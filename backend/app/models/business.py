import uuid
from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import GUID, TimestampMixin


class Business(Base, TimestampMixin):
    __tablename__ = "businesses"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True)
    tier = Column(String(20), default="simple", nullable=False)  # simple, growth, enterprise
    currency_code = Column(String(10), default="INR", nullable=False)
    currency_symbol = Column(String(5), default="₹", nullable=False)
    default_language = Column(String(10), default="ta", nullable=False)  # ta, tanglish, en
    emergency_recovery_key_hash = Column(String(255), nullable=True)
    settings = Column(JSON, default=dict, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Stage 2: Adaptive Onboarding & Business Profile
    onboarding_completed = Column(Boolean, default=False, nullable=False)
    onboarding_step = Column(Integer, default=1, nullable=False)
    onboarding_answers = Column(JSON, default=dict, nullable=False)
    recommended_tier = Column(String(20), nullable=True)
    recommendation_reasons = Column(JSON, default=list, nullable=False)
    enabled_modules = Column(JSON, default=list, nullable=False)
    workforce_count = Column(Integer, default=1, nullable=False)
    app_users_count = Column(Integer, default=1, nullable=False)
    branch_count = Column(Integer, default=1, nullable=False)
    warehouse_count = Column(Integer, default=1, nullable=False)
    operations = Column(JSON, default=list, nullable=False)
    accessibility_settings = Column(JSON, default=dict, nullable=False)

    # Relationships
    users = relationship("User", back_populates="business", cascade="all, delete-orphan")
    branches = relationship("Branch", back_populates="business", cascade="all, delete-orphan")
    warehouses = relationship("Warehouse", back_populates="business", cascade="all, delete-orphan")


class Branch(Base, TimestampMixin):
    __tablename__ = "branches"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    business_id = Column(GUID, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), default="Main Branch", nullable=False)
    code = Column(String(50), default="BR-01", nullable=False)
    address = Column(Text, nullable=True)
    phone = Column(String(20), nullable=True)
    is_main = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    business = relationship("Business", back_populates="branches")
    warehouses = relationship("Warehouse", back_populates="branch", cascade="all, delete-orphan")


class Warehouse(Base, TimestampMixin):
    __tablename__ = "warehouses"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    business_id = Column(GUID, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id = Column(GUID, ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), default="Main Counter", nullable=False)
    is_default = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    business = relationship("Business", back_populates="warehouses")
    branch = relationship("Branch", back_populates="warehouses")
