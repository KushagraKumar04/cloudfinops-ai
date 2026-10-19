import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    from datetime import UTC

    return datetime.now(UTC)


class KubernetesCluster(Base):
    __tablename__ = "kubernetes_clusters"
    __table_args__ = (
        UniqueConstraint("tenant_id", "cloud_account_id", "name", name="uq_k8s_cluster_tenant_account_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    cloud_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cloud_accounts.id", ondelete="CASCADE"), index=True
    )

    provider: Mapped[str] = mapped_column(String(16), index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    version: Mapped[str] = mapped_column(String(32), default="")
    region: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(24), default="active", index=True)

    node_count: Mapped[int] = mapped_column(Integer, default=0)
    total_cpu_cores: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    total_memory_gb: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    monthly_cost: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    currency: Mapped[str] = mapped_column(String(8), default="USD")

    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    namespaces: Mapped[list["KubernetesNamespace"]] = relationship(
        back_populates="cluster", cascade="all, delete-orphan"
    )
    workloads: Mapped[list["KubernetesWorkload"]] = relationship(
        back_populates="cluster", cascade="all, delete-orphan"
    )
    cost_allocations: Mapped[list["KubernetesCostAllocation"]] = relationship(
        back_populates="cluster", cascade="all, delete-orphan"
    )


class KubernetesNamespace(Base):
    __tablename__ = "kubernetes_namespaces"
    __table_args__ = (
        UniqueConstraint("cluster_id", "name", name="uq_k8s_namespace_cluster_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    cluster_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("kubernetes_clusters.id", ondelete="CASCADE"), index=True
    )

    name: Mapped[str] = mapped_column(String(120), index=True)
    cpu_request_cores: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    cpu_limit_cores: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    cpu_usage_avg_cores: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    memory_request_gb: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    memory_limit_gb: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    memory_usage_avg_gb: Mapped[float] = mapped_column(Numeric(12, 2), default=0)

    monthly_cost: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    labels: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    cluster: Mapped["KubernetesCluster"] = relationship(back_populates="namespaces")
    workloads: Mapped[list["KubernetesWorkload"]] = relationship(
        back_populates="namespace", cascade="all, delete-orphan"
    )


class KubernetesWorkload(Base):
    __tablename__ = "kubernetes_workloads"
    __table_args__ = (
        UniqueConstraint("namespace_id", "kind", "name", name="uq_k8s_workload_ns_kind_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    cluster_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("kubernetes_clusters.id", ondelete="CASCADE"), index=True
    )
    namespace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("kubernetes_namespaces.id", ondelete="CASCADE"), index=True
    )

    name: Mapped[str] = mapped_column(String(200), index=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    replicas: Mapped[int] = mapped_column(Integer, default=1)

    cpu_request_cores: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    cpu_limit_cores: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    cpu_usage_avg_cores: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    memory_request_gb: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    memory_limit_gb: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    memory_usage_avg_gb: Mapped[float] = mapped_column(Numeric(12, 2), default=0)

    monthly_cost: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    potential_savings: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    over_provisioned: Mapped[bool] = mapped_column(Boolean, default=False)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    labels: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    cluster: Mapped["KubernetesCluster"] = relationship(back_populates="workloads")
    namespace: Mapped["KubernetesNamespace"] = relationship(back_populates="workloads")


class KubernetesCostAllocation(Base):
    __tablename__ = "kubernetes_cost_allocations"
    __table_args__ = (
        UniqueConstraint(
            "cluster_id", "namespace_id", "workload_id", "date",
            name="uq_k8s_cost_cluster_ns_workload_date",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE", name="fk_k8s_cost_alloc_tenant"),
        index=True,
    )
    cluster_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("kubernetes_clusters.id", ondelete="CASCADE", name="fk_k8s_cost_alloc_cluster"),
        index=True,
    )
    namespace_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("kubernetes_namespaces.id", ondelete="SET NULL", name="fk_k8s_cost_alloc_namespace"),
        index=True,
        nullable=True,
    )
    workload_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("kubernetes_workloads.id", ondelete="SET NULL", name="fk_k8s_cost_alloc_workload"),
        index=True,
        nullable=True,
    )

    date: Mapped[date] = mapped_column(Date, index=True)
    cost: Mapped[float] = mapped_column(Numeric(18, 4), default=0)
    cpu_cost: Mapped[float] = mapped_column(Numeric(18, 4), default=0)
    memory_cost: Mapped[float] = mapped_column(Numeric(18, 4), default=0)
    storage_cost: Mapped[float] = mapped_column(Numeric(18, 4), default=0)
    network_cost: Mapped[float] = mapped_column(Numeric(18, 4), default=0)
    currency: Mapped[str] = mapped_column(String(8), default="USD")

    cluster: Mapped["KubernetesCluster"] = relationship(back_populates="cost_allocations")