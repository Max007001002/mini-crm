from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Operator(Base):
    __tablename__ = "operators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_load: Mapped[int] = mapped_column(Integer, default=10, nullable=False)

    source_configs: Mapped[List["SourceOperatorConfig"]] = relationship(
        back_populates="operator", cascade="all, delete-orphan"
    )
    contacts: Mapped[List["Contact"]] = relationship(
        back_populates="operator", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"Operator(id={self.id}, name={self.name!r})"


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    external_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    contacts: Mapped[List["Contact"]] = relationship(
        back_populates="lead", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"Lead(id={self.id}, external_id={self.external_id!r})"


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True)

    operator_configs: Mapped[List["SourceOperatorConfig"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )
    contacts: Mapped[List["Contact"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"Source(id={self.id}, name={self.name!r})"


class SourceOperatorConfig(Base):
    __tablename__ = "source_operator_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    operator_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("operators.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    weight: Mapped[int] = mapped_column(Integer, nullable=False)

    source: Mapped["Source"] = relationship(back_populates="operator_configs")
    operator: Mapped["Operator"] = relationship(back_populates="source_configs")

    __table_args__ = (
        UniqueConstraint("source_id", "operator_id", name="uix_source_operator"),
    )

    def __repr__(self) -> str:
        return (
            f"SourceOperatorConfig(source_id={self.source_id}, "
            f"operator_id={self.operator_id}, weight={self.weight})"
        )


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    lead_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    operator_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("operators.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    lead: Mapped["Lead"] = relationship(back_populates="contacts")
    source: Mapped["Source"] = relationship(back_populates="contacts")
    operator: Mapped[Optional["Operator"]] = relationship(back_populates="contacts")

    def __repr__(self) -> str:
        return f"Contact(id={self.id}, lead_id={self.lead_id}, source_id={self.source_id})"
