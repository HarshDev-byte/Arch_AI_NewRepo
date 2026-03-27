"""
database.py — Async SQLAlchemy engine + ORM models for ArchAI.

Supports:
  - PostgreSQL via asyncpg (production / Supabase)
  - SQLite fallback for local dev without Docker
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, AsyncGenerator

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Double,
    ForeignKey,
    Integer,
    Text,
    func,
)
from sqlalchemy import UniqueConstraint
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from config import settings

# ─────────────────────────────────────────────────────────────────────────────
# Engine & session factory
# ─────────────────────────────────────────────────────────────────────────────

def _make_async_url(url: str) -> str:
    """Convert sync postgres:// URLs to async postgresql+asyncpg:// scheme."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    # SQLite fallback for local dev without Docker
    if url.startswith("sqlite"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    return url


def _json() -> Any:
    """Return JSONB on Postgres, JSON on SQLite (dialect-agnostic helper)."""
    db_url = settings.database_url
    if "postgresql" in db_url or "postgres" in db_url:
        return JSONB
    return JSON


async_engine = create_async_engine(
    _make_async_url(settings.database_url),
    echo=settings.environment == "development",
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ─────────────────────────────────────────────────────────────────────────────
# Declarative base
# ─────────────────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ─────────────────────────────────────────────────────────────────────────────
# Helper — portable UUID primary key
# Postgres uses native UUID type; SQLite stores as TEXT.
# ─────────────────────────────────────────────────────────────────────────────

def _uuid_col(primary_key: bool = False) -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True),
        primary_key=primary_key,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid() if not primary_key else None,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # relationships
    projects: Mapped[list["Project"]] = relationship("Project", back_populates="user")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="pending"
    )  # pending | processing | complete | error

    # Location
    latitude: Mapped[float | None] = mapped_column(Double, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Double, nullable=True)

    # Plot & brief
    plot_area_sqm: Mapped[float | None] = mapped_column(Double, nullable=True)
    plot_width_m: Mapped[float | None] = mapped_column(Double, nullable=True)
    plot_depth_m: Mapped[float | None] = mapped_column(Double, nullable=True)
    fsi_allowed: Mapped[float | None] = mapped_column(Double, nullable=True, default=2.0)
    budget_inr: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    floors: Mapped[int] = mapped_column(Integer, default=2)
    style_preferences: Mapped[list[Any]] = mapped_column(_json(), default=list)

    # Design DNA
    design_seed: Mapped[str | None] = mapped_column(Text, nullable=True)
    design_dna: Mapped[dict[str, Any] | None] = mapped_column(_json(), nullable=True)

    # Sharing
    share_token: Mapped[str | None] = mapped_column(Text, nullable=True, unique=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # relationships
    user: Mapped["User | None"] = relationship("User", back_populates="projects")
    agent_runs: Mapped[list["AgentRun"]] = relationship(
        "AgentRun", back_populates="project", cascade="all, delete-orphan"
    )
    design_variants: Mapped[list["DesignVariant"]] = relationship(
        "DesignVariant", back_populates="project", cascade="all, delete-orphan"
    )
    cost_estimate: Mapped["CostEstimate | None"] = relationship(
        "CostEstimate", back_populates="project", uselist=False, cascade="all, delete-orphan"
    )
    geo_analysis: Mapped["GeoAnalysis | None"] = relationship(
        "GeoAnalysis", back_populates="project", uselist=False, cascade="all, delete-orphan"
    )
    compliance_check: Mapped["ComplianceCheck | None"] = relationship(
        "ComplianceCheck", back_populates="project", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Project id={self.id} name={self.name!r} status={self.status}>"


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    agent_name: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # geo|cost|layout|design|threed|vr|compliance|sustainability
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="pending"
    )  # pending|running|complete|error

    input_data: Mapped[dict[str, Any] | None] = mapped_column(_json(), nullable=True)
    output_data: Mapped[dict[str, Any] | None] = mapped_column(_json(), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # relationships
    project: Mapped["Project"] = relationship("Project", back_populates="agent_runs")

    def __repr__(self) -> str:
        return f"<AgentRun agent={self.agent_name} status={self.status} project={self.project_id}>"


class DesignVariant(Base):
    __tablename__ = "design_variants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    variant_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dna: Mapped[dict[str, Any] | None] = mapped_column(_json(), nullable=True)
    score: Mapped[float | None] = mapped_column(Double, nullable=True)
    is_selected: Mapped[bool] = mapped_column(Boolean, default=False)

    floor_plan_svg: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_url: Mapped[str | None] = mapped_column(Text, nullable=True)    # .glb in Supabase Storage
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # relationships
    project: Mapped["Project"] = relationship("Project", back_populates="design_variants")

    def __repr__(self) -> str:
        return f"<DesignVariant #{self.variant_number} score={self.score} project={self.project_id}>"


class CostEstimate(Base):
    __tablename__ = "cost_estimates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    breakdown: Mapped[dict[str, Any] | None] = mapped_column(_json(), nullable=True)
    total_cost_inr: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    cost_per_sqft: Mapped[float | None] = mapped_column(Double, nullable=True)
    roi_estimate: Mapped[dict[str, Any] | None] = mapped_column(_json(), nullable=True)
    land_value_estimate: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # relationships
    project: Mapped["Project"] = relationship("Project", back_populates="cost_estimate")

    def __repr__(self) -> str:
        return f"<CostEstimate total=₹{self.total_cost_inr} project={self.project_id}>"


class GeoAnalysis(Base):
    __tablename__ = "geo_analysis"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    plot_data: Mapped[dict[str, Any] | None] = mapped_column(_json(), nullable=True)
    zoning_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    fsi_allowed: Mapped[float | None] = mapped_column(Double, nullable=True)
    road_access: Mapped[dict[str, Any] | None] = mapped_column(_json(), nullable=True)
    nearby_amenities: Mapped[dict[str, Any] | None] = mapped_column(_json(), nullable=True)
    elevation_profile: Mapped[dict[str, Any] | None] = mapped_column(_json(), nullable=True)
    solar_irradiance: Mapped[float | None] = mapped_column(Double, nullable=True)
    wind_data: Mapped[dict[str, Any] | None] = mapped_column(_json(), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # relationships
    project: Mapped["Project"] = relationship("Project", back_populates="geo_analysis")

    def __repr__(self) -> str:
        return f"<GeoAnalysis zone={self.zoning_type} fsi={self.fsi_allowed} project={self.project_id}>"


class ComplianceCheck(Base):
    __tablename__ = "compliance_checks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    fsi_used: Mapped[float | None] = mapped_column(Double, nullable=True)
    fsi_allowed: Mapped[float | None] = mapped_column(Double, nullable=True)
    setback_compliance: Mapped[dict[str, Any] | None] = mapped_column(_json(), nullable=True)
    height_compliance: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    parking_required: Mapped[int | None] = mapped_column(Integer, nullable=True)
    green_area_required: Mapped[float | None] = mapped_column(Double, nullable=True)
    issues: Mapped[list[Any]] = mapped_column(_json(), default=list)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # relationships
    project: Mapped["Project"] = relationship("Project", back_populates="compliance_check")

    def __repr__(self) -> str:
        return f"<ComplianceCheck passed={self.passed} project={self.project_id}>"


class APIKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    key_preview: Mapped[str] = mapped_column(Text, nullable=False)
    key_enc: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_tested: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    test_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"<APIKey provider={self.provider} label={self.label} user={self.user_id}>"


class AgentKeyAssignment(Base):
    __tablename__ = "agent_key_assignments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    agent_name: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint('user_id', 'agent_name', name='uq_agent_user_name'),)

    api_key: Mapped[APIKey | None] = relationship("APIKey")

    def __repr__(self) -> str:
        return f"<AgentKeyAssignment agent={self.agent_name} provider={self.provider} user={self.user_id}>"


# ─────────────────────────────────────────────────────────────────────────────
# Dependency & lifecycle helpers
# ─────────────────────────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables (idempotent — safe to call on every startup)."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables initialised.")
