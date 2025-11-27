from typing import Dict

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import app, get_db


SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


def test_weighted_distribution_and_limits():
    r1 = client.post(
        "/operators",
        json={"name": "op1", "max_load": 1000, "active": True},
    )
    assert r1.status_code == 201
    op1 = r1.json()

    r2 = client.post(
        "/operators",
        json={"name": "op2", "max_load": 1000, "active": True},
    )
    assert r2.status_code == 201
    op2 = r2.json()

    # источник
    rs = client.post("/sources", json={"name": "botA", "code": "A"})
    assert rs.status_code == 201
    source = rs.json()
    source_id = source["id"]

    # веса 10/30
    r_cfg = client.put(
        f"/sources/{source_id}/operators",
        json=[
            {"operator_id": op1["id"], "weight": 10},
            {"operator_id": op2["id"], "weight": 30},
        ],
    )
    assert r_cfg.status_code == 200

    total = 200
    counts: Dict[int, int] = {op1["id"]: 0, op2["id"]: 0}

    for i in range(total):
        rc = client.post(
            "/contacts",
            json={
                "lead_external_id": f"lead-{i}",
                "lead_name": f"Lead {i}",
                "source_id": source_id,
                "message": "ping",
            },
        )
        assert rc.status_code == 201
        op = rc.json()["operator"]
        assert op is not None
        counts[op["id"]] += 1

    # ожидаем, что оператор с весом 30 получил больше обращений
    assert counts[op2["id"]] > counts[op1["id"]]


def test_max_load_respected():
    # отдельный источник и операторы c маленьким лимитом
    r1 = client.post(
        "/operators",
        json={"name": "limit-op1", "max_load": 1, "active": True},
    )
    assert r1.status_code == 201
    op1 = r1.json()

    r2 = client.post(
        "/operators",
        json={"name": "limit-op2", "max_load": 1, "active": True},
    )
    assert r2.status_code == 201
    op2 = r2.json()

    rs = client.post("/sources", json={"name": "botB", "code": "B"})
    assert rs.status_code == 201
    source = rs.json()
    source_id = source["id"]

    r_cfg = client.put(
        f"/sources/{source_id}/operators",
        json=[
            {"operator_id": op1["id"], "weight": 1},
            {"operator_id": op2["id"], "weight": 1},
        ],
    )
    assert r_cfg.status_code == 200

    counts: Dict[int, int] = {op1["id"]: 0, op2["id"]: 0}
    unassigned = 0

    for i in range(10):
        rc = client.post(
            "/contacts",
            json={
                "lead_external_id": f"limit-lead-{i}",
                "lead_name": f"Lead {i}",
                "source_id": source_id,
                "message": "ping",
            },
        )
        assert rc.status_code == 201
        payload = rc.json()
        op = payload["operator"]
        if op is None:
            unassigned += 1
        else:
            counts[op["id"]] += 1

    # ни один оператор не должен получить больше обращений, чем его лимит
    assert counts[op1["id"]] <= 1
    assert counts[op2["id"]] <= 1
    # часть обращений должна остаться без оператора из-за лимитов
    assert unassigned > 0
