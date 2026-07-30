"""SQLAlchemy ORM Models for the Catalog Module.

Defines database mapping for VehicleModel, VariantModel, ColorModel, and OptionModel.
"""

from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class VehicleModel(Base):
    """SQLAlchemy ORM Model representing vehicle product line."""

    __tablename__ = "vehicles"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100), nullable=False)
    slug = Column(String(120), unique=True, nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=True)
    base_price = Column(Numeric(15, 2), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    variants = relationship("VariantModel", back_populates="vehicle", cascade="all, delete-orphan", lazy="selectin")
    colors = relationship("ColorModel", back_populates="vehicle", cascade="all, delete-orphan", lazy="selectin")
    options = relationship("OptionModel", back_populates="vehicle", cascade="all, delete-orphan")


class VariantModel(Base):
    """SQLAlchemy ORM Model representing a specific vehicle trim/variant."""

    __tablename__ = "vehicle_variants"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    vehicle_id = Column(PG_UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    sku = Column(String(50), unique=True, nullable=False, index=True)
    price = Column(Numeric(15, 2), nullable=False)
    specs = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    vehicle = relationship("VehicleModel", back_populates="variants")


class ColorModel(Base):
    """SQLAlchemy ORM Model representing vehicle exterior/interior color choices."""

    __tablename__ = "vehicle_colors"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    vehicle_id = Column(PG_UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(50), nullable=False)
    color_code = Column(String(20), nullable=False)
    price_extra = Column(Numeric(15, 2), default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    vehicle = relationship("VehicleModel", back_populates="colors")


class OptionModel(Base):
    """SQLAlchemy ORM Model representing vehicle optional add-on equipment."""

    __tablename__ = "vehicle_options"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    vehicle_id = Column(PG_UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    price = Column(Numeric(15, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    vehicle = relationship("VehicleModel", back_populates="options")
