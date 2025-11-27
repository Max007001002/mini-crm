from typing import List

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from . import models, schemas, services
from .database import Base, SessionLocal, engine

# Инициализация базы
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Mini CRM Leads Distribution")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Операторы


@app.post("/operators", response_model=schemas.OperatorOut, status_code=status.HTTP_201_CREATED)
def create_operator(
    operator_in: schemas.OperatorCreate, db: Session = Depends(get_db)
):
    existing = db.query(models.Operator).filter_by(name=operator_in.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Оператор с таким именем уже существует",
        )
    operator = models.Operator(**operator_in.model_dump())
    db.add(operator)
    db.commit()
    db.refresh(operator)
    return operator


@app.get("/operators", response_model=List[schemas.OperatorOut])
def list_operators(db: Session = Depends(get_db)):
    operators = db.query(models.Operator).order_by(models.Operator.id).all()
    return operators


@app.patch("/operators/{operator_id}", response_model=schemas.OperatorOut)
def update_operator(
    operator_id: int, operator_in: schemas.OperatorUpdate, db: Session = Depends(get_db)
):
    operator = db.get(models.Operator, operator_id)
    if not operator:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Оператор не найден")

    data = operator_in.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(operator, field, value)

    db.add(operator)
    db.commit()
    db.refresh(operator)
    return operator


# Источники и конфигурация весов


@app.post("/sources", response_model=schemas.SourceOut, status_code=status.HTTP_201_CREATED)
def create_source(source_in: schemas.SourceCreate, db: Session = Depends(get_db)):
    existing = (
        db.query(models.Source)
        .filter(
            (models.Source.name == source_in.name)
            | (models.Source.code == source_in.code)
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Источник с таким именем или кодом уже существует",
        )
    source = models.Source(**source_in.model_dump())
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@app.get("/sources", response_model=List[schemas.SourceOut])
def list_sources(db: Session = Depends(get_db)):
    sources = db.query(models.Source).order_by(models.Source.id).all()
    return sources


@app.get("/sources/{source_id}", response_model=schemas.SourceDetailOut)
def get_source_detail(source_id: int, db: Session = Depends(get_db)):
    source = db.get(models.Source, source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Источник не найден")

    operators = []
    for cfg in source.operator_configs:
        operators.append(
            schemas.SourceOperatorWeightOut(
                operator_id=cfg.operator_id,
                operator_name=cfg.operator.name,
                weight=cfg.weight,
            )
        )

    return schemas.SourceDetailOut(
        id=source.id,
        name=source.name,
        code=source.code,
        operators=operators,
    )


@app.put("/sources/{source_id}/operators", response_model=schemas.SourceDetailOut)
def set_source_operators(
    source_id: int,
    items: List[schemas.SourceOperatorWeightIn],
    db: Session = Depends(get_db),
):
    source = db.get(models.Source, source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Источник не найден")

    operator_ids = [item.operator_id for item in items]
    if operator_ids:
        operators = (
            db.query(models.Operator)
            .filter(models.Operator.id.in_(operator_ids))
            .all()
        )
        found_ids = {op.id for op in operators}
        missing = set(operator_ids) - found_ids
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Не найдены операторы: {sorted(missing)}",
            )

    # Сбрасываем старую конфигурацию
    db.query(models.SourceOperatorConfig).filter_by(source_id=source_id).delete()

    # Записываем новую
    for item in items:
        cfg = models.SourceOperatorConfig(
            source_id=source_id,
            operator_id=item.operator_id,
            weight=item.weight,
        )
        db.add(cfg)

    db.commit()
    db.refresh(source)

    operators_out = [
        schemas.SourceOperatorWeightOut(
            operator_id=cfg.operator_id,
            operator_name=cfg.operator.name,
            weight=cfg.weight,
        )
        for cfg in source.operator_configs
    ]

    return schemas.SourceDetailOut(
        id=source.id,
        name=source.name,
        code=source.code,
        operators=operators_out,
    )


# Регистрация обращения


@app.post("/contacts", response_model=schemas.ContactOut, status_code=status.HTTP_201_CREATED)
def create_contact(
    contact_in: schemas.ContactCreate,
    db: Session = Depends(get_db),
):
    source = db.get(models.Source, contact_in.source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Источник не найден")

    lead = services.get_or_create_lead(
        db, external_id=contact_in.lead_external_id, name=contact_in.lead_name
    )

    operator = services.pick_operator_for_source(db, source.id)

    contact = models.Contact(
        lead_id=lead.id,
        source_id=source.id,
        operator_id=operator.id if operator else None,
        message=contact_in.message,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)

    return contact


# Просмотр состояния


@app.get("/leads", response_model=List[schemas.LeadWithContactsOut])
def list_leads(db: Session = Depends(get_db)):
    leads = db.query(models.Lead).order_by(models.Lead.id).all()
    result: List[schemas.LeadWithContactsOut] = []

    for lead in leads:
        contacts_short = [
            schemas.ContactShort(
                id=c.id,
                created_at=c.created_at,
                is_active=c.is_active,
                message=c.message,
                source=c.source,
                operator=c.operator,
            )
            for c in lead.contacts
        ]
        result.append(
            schemas.LeadWithContactsOut(
                id=lead.id,
                external_id=lead.external_id,
                name=lead.name,
                contacts=contacts_short,
            )
        )
    return result


@app.get("/stats/operators", response_model=List[schemas.OperatorStatsItem])
def operators_stats(db: Session = Depends(get_db)):
    from sqlalchemy import func

    rows = (
        db.query(
            models.Operator.id,
            models.Operator.name,
            models.Source.id,
            models.Source.name,
            func.count(models.Contact.id),
        )
        .join(models.Contact, models.Contact.operator_id == models.Operator.id)
        .join(models.Source, models.Source.id == models.Contact.source_id)
        .group_by(models.Operator.id, models.Source.id)
        .all()
    )

    stats_map = {}
    for op_id, op_name, src_id, src_name, cnt in rows:
        item = stats_map.setdefault(
            op_id,
            {
                "operator_id": op_id,
                "operator_name": op_name,
                "total_contacts": 0,
                "sources": [],
            },
        )
        item["total_contacts"] += cnt
        item["sources"].append(
            schemas.OperatorSourceCount(
                source_id=src_id, source_name=src_name, contacts_count=cnt
            )
        )

    result = [
        schemas.OperatorStatsItem(
            operator_id=data["operator_id"],
            operator_name=data["operator_name"],
            total_contacts=data["total_contacts"],
            sources=data["sources"],
        )
        for data in stats_map.values()
    ]
    return result
