from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class OperatorCreate(BaseModel):
    name: str
    max_load: int = 10
    active: bool = True


class OperatorUpdate(BaseModel):
    name: Optional[str] = None
    max_load: Optional[int] = None
    active: Optional[bool] = None


class OperatorOut(BaseModel):
    id: int
    name: str
    active: bool
    max_load: int

    model_config = ConfigDict(from_attributes=True)


class SourceCreate(BaseModel):
    name: str
    code: Optional[str] = None


class SourceOut(BaseModel):
    id: int
    name: str
    code: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class SourceOperatorWeightIn(BaseModel):
    operator_id: int
    weight: int


class SourceOperatorWeightOut(BaseModel):
    operator_id: int
    operator_name: str
    weight: int


class SourceDetailOut(SourceOut):
    operators: List[SourceOperatorWeightOut]


class LeadOut(BaseModel):
    id: int
    external_id: str
    name: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class ContactCreate(BaseModel):
    lead_external_id: str
    lead_name: Optional[str] = None
    source_id: int
    message: Optional[str] = None


class ContactShort(BaseModel):
    id: int
    created_at: datetime
    is_active: bool
    message: Optional[str]
    source: SourceOut
    operator: Optional[OperatorOut]

    model_config = ConfigDict(from_attributes=True)


class LeadWithContactsOut(LeadOut):
    contacts: List[ContactShort]


class ContactOut(BaseModel):
    id: int
    created_at: datetime
    is_active: bool
    message: Optional[str]
    lead: LeadOut
    source: SourceOut
    operator: Optional[OperatorOut]

    model_config = ConfigDict(from_attributes=True)


class OperatorSourceCount(BaseModel):
    source_id: int
    source_name: str
    contacts_count: int


class OperatorStatsItem(BaseModel):
    operator_id: int
    operator_name: str
    total_contacts: int
    sources: List[OperatorSourceCount]
