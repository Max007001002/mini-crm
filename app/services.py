from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from . import models


def get_or_create_lead(
    db: Session, external_id: str, name: Optional[str] = None
) -> models.Lead:
    # По внешнему id ищем лида, при необходимости создаём
    lead = db.query(models.Lead).filter_by(external_id=external_id).first()
    if lead:
        if name and not lead.name:
            lead.name = name
            db.add(lead)
            db.flush()
        return lead

    lead = models.Lead(external_id=external_id, name=name)
    db.add(lead)
    db.flush()
    return lead


def _get_available_configs_for_source(
    db: Session, source_id: int
) -> List[models.SourceOperatorConfig]:
    configs = (
        db.query(models.SourceOperatorConfig)
        .join(models.SourceOperatorConfig.operator)
        .filter(
            models.SourceOperatorConfig.source_id == source_id,
            models.Operator.active.is_(True),
        )
        .all()
    )
    if not configs:
        return []

    operator_ids = [cfg.operator_id for cfg in configs]
    if not operator_ids:
        return []

    load_rows = (
        db.query(models.Contact.operator_id, func.count(models.Contact.id))
        .filter(
            models.Contact.operator_id.in_(operator_ids),
            models.Contact.is_active.is_(True),
        )
        .group_by(models.Contact.operator_id)
        .all()
    )
    loads = {op_id: count for op_id, count in load_rows}

    available: List[models.SourceOperatorConfig] = []
    for cfg in configs:
        op = cfg.operator
        current = loads.get(op.id, 0)
        if current < op.max_load:
            available.append(cfg)

    return available


def _choose_operator_weighted(
    configs: List[models.SourceOperatorConfig],
) -> Optional[models.Operator]:
    # Простой случайный выбор по весам
    positive = [cfg for cfg in configs if cfg.weight > 0]
    if not positive:
        return None

    total_weight = sum(cfg.weight for cfg in positive)
    if total_weight <= 0:
        return None

    import random

    r = random.randint(1, total_weight)
    acc = 0
    for cfg in positive:
        acc += cfg.weight
        if r <= acc:
            return cfg.operator
    return None


def pick_operator_for_source(db: Session, source_id: int) -> Optional[models.Operator]:
    # Возвращаем оператора с учётом весов и лимитов
    configs = _get_available_configs_for_source(db, source_id)
    if not configs:
        return None

    remaining = list(configs)

    while remaining:
        op = _choose_operator_weighted(remaining)
        if op is None:
            return None

        current_load = (
            db.query(func.count(models.Contact.id))
            .filter(
                models.Contact.operator_id == op.id,
                models.Contact.is_active.is_(True),
            )
            .scalar()
        ) or 0

        if op.active and current_load < op.max_load:
            return op

        remaining = [cfg for cfg in remaining if cfg.operator_id != op.id]

    return None
