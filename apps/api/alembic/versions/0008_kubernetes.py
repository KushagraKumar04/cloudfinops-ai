"""kubernetes cost analysis

Revision ID: 0008_kubernetes
Revises: 0007_users
Create Date: 2026-10-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_kubernetes"
down_revision: Union[str, None] = "0007_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "kubernetes_clusters",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("cloud_account_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("region", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("node_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_cpu_cores", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0"),
        sa.Column("total_memory_gb", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),
        sa.Column("monthly_cost", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="USD"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_kubernetes_clusters_tenant_id_tenants", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cloud_account_id"], ["cloud_accounts.id"], name="fk_kubernetes_clusters_cloud_account_id_cloud_accounts", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_kubernetes_clusters"),
        sa.UniqueConstraint("tenant_id", "cloud_account_id", "name", name="uq_k8s_cluster_tenant_account_name"),
    )
    op.create_index("ix_kubernetes_clusters_tenant_id", "kubernetes_clusters", ["tenant_id"])
    op.create_index("ix_kubernetes_clusters_cloud_account_id", "kubernetes_clusters", ["cloud_account_id"])
    op.create_index("ix_kubernetes_clusters_provider", "kubernetes_clusters", ["provider"])
    op.create_index("ix_kubernetes_clusters_name", "kubernetes_clusters", ["name"])
    op.create_index("ix_kubernetes_clusters_region", "kubernetes_clusters", ["region"])
    op.create_index("ix_kubernetes_clusters_status", "kubernetes_clusters", ["status"])

    op.create_table(
        "kubernetes_namespaces",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("cluster_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("cpu_request_cores", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0"),
        sa.Column("cpu_limit_cores", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0"),
        sa.Column("cpu_usage_avg_cores", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0"),
        sa.Column("memory_request_gb", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),
        sa.Column("memory_limit_gb", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),
        sa.Column("memory_usage_avg_gb", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),
        sa.Column("monthly_cost", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="USD"),
        sa.Column("labels", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_kubernetes_namespaces_tenant_id_tenants", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cluster_id"], ["kubernetes_clusters.id"], name="fk_kubernetes_namespaces_cluster_id_kubernetes_clusters", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_kubernetes_namespaces"),
        sa.UniqueConstraint("cluster_id", "name", name="uq_k8s_namespace_cluster_name"),
    )
    op.create_index("ix_kubernetes_namespaces_tenant_id", "kubernetes_namespaces", ["tenant_id"])
    op.create_index("ix_kubernetes_namespaces_cluster_id", "kubernetes_namespaces", ["cluster_id"])
    op.create_index("ix_kubernetes_namespaces_name", "kubernetes_namespaces", ["name"])

    op.create_table(
        "kubernetes_workloads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("cluster_id", sa.Uuid(), nullable=False),
        sa.Column("namespace_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("replicas", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("cpu_request_cores", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0"),
        sa.Column("cpu_limit_cores", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0"),
        sa.Column("cpu_usage_avg_cores", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0"),
        sa.Column("memory_request_gb", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),
        sa.Column("memory_limit_gb", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),
        sa.Column("memory_usage_avg_gb", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),
        sa.Column("monthly_cost", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0"),
        sa.Column("potential_savings", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0"),
        sa.Column("over_provisioned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="USD"),
        sa.Column("labels", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_kubernetes_workloads_tenant_id_tenants", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cluster_id"], ["kubernetes_clusters.id"], name="fk_kubernetes_workloads_cluster_id_kubernetes_clusters", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["namespace_id"], ["kubernetes_namespaces.id"], name="fk_kubernetes_workloads_namespace_id_kubernetes_namespaces", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_kubernetes_workloads"),
        sa.UniqueConstraint("namespace_id", "kind", "name", name="uq_k8s_workload_ns_kind_name"),
    )
    op.create_index("ix_kubernetes_workloads_tenant_id", "kubernetes_workloads", ["tenant_id"])
    op.create_index("ix_kubernetes_workloads_cluster_id", "kubernetes_workloads", ["cluster_id"])
    op.create_index("ix_kubernetes_workloads_namespace_id", "kubernetes_workloads", ["namespace_id"])
    op.create_index("ix_kubernetes_workloads_name", "kubernetes_workloads", ["name"])
    op.create_index("ix_kubernetes_workloads_kind", "kubernetes_workloads", ["kind"])

    op.create_table(
        "kubernetes_cost_allocations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("cluster_id", sa.Uuid(), nullable=False),
        sa.Column("namespace_id", sa.Uuid(), nullable=True),
        sa.Column("workload_id", sa.Uuid(), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("cost", sa.Numeric(precision=18, scale=4), nullable=False, server_default="0"),
        sa.Column("cpu_cost", sa.Numeric(precision=18, scale=4), nullable=False, server_default="0"),
        sa.Column("memory_cost", sa.Numeric(precision=18, scale=4), nullable=False, server_default="0"),
        sa.Column("storage_cost", sa.Numeric(precision=18, scale=4), nullable=False, server_default="0"),
        sa.Column("network_cost", sa.Numeric(precision=18, scale=4), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="USD"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_k8s_cost_alloc_tenant", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cluster_id"], ["kubernetes_clusters.id"], name="fk_k8s_cost_alloc_cluster", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["namespace_id"], ["kubernetes_namespaces.id"], name="fk_k8s_cost_alloc_namespace", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workload_id"], ["kubernetes_workloads.id"], name="fk_k8s_cost_alloc_workload", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_kubernetes_cost_allocations"),
        sa.UniqueConstraint("cluster_id", "namespace_id", "workload_id", "date", name="uq_k8s_cost_cluster_ns_workload_date"),
    )
    op.create_index("ix_kubernetes_cost_allocations_tenant_id", "kubernetes_cost_allocations", ["tenant_id"])
    op.create_index("ix_kubernetes_cost_allocations_cluster_id", "kubernetes_cost_allocations", ["cluster_id"])
    op.create_index("ix_kubernetes_cost_allocations_namespace_id", "kubernetes_cost_allocations", ["namespace_id"])
    op.create_index("ix_kubernetes_cost_allocations_workload_id", "kubernetes_cost_allocations", ["workload_id"])
    op.create_index("ix_kubernetes_cost_allocations_date", "kubernetes_cost_allocations", ["date"])


def downgrade() -> None:
    op.drop_index("ix_kubernetes_cost_allocations_date", table_name="kubernetes_cost_allocations")
    op.drop_index("ix_kubernetes_cost_allocations_workload_id", table_name="kubernetes_cost_allocations")
    op.drop_index("ix_kubernetes_cost_allocations_namespace_id", table_name="kubernetes_cost_allocations")
    op.drop_index("ix_kubernetes_cost_allocations_cluster_id", table_name="kubernetes_cost_allocations")
    op.drop_index("ix_kubernetes_cost_allocations_tenant_id", table_name="kubernetes_cost_allocations")
    op.drop_table("kubernetes_cost_allocations")

    op.drop_index("ix_kubernetes_workloads_kind", table_name="kubernetes_workloads")
    op.drop_index("ix_kubernetes_workloads_name", table_name="kubernetes_workloads")
    op.drop_index("ix_kubernetes_workloads_namespace_id", table_name="kubernetes_workloads")
    op.drop_index("ix_kubernetes_workloads_cluster_id", table_name="kubernetes_workloads")
    op.drop_index("ix_kubernetes_workloads_tenant_id", table_name="kubernetes_workloads")
    op.drop_table("kubernetes_workloads")

    op.drop_index("ix_kubernetes_namespaces_name", table_name="kubernetes_namespaces")
    op.drop_index("ix_kubernetes_namespaces_cluster_id", table_name="kubernetes_namespaces")
    op.drop_index("ix_kubernetes_namespaces_tenant_id", table_name="kubernetes_namespaces")
    op.drop_table("kubernetes_namespaces")

    op.drop_index("ix_kubernetes_clusters_status", table_name="kubernetes_clusters")
    op.drop_index("ix_kubernetes_clusters_region", table_name="kubernetes_clusters")
    op.drop_index("ix_kubernetes_clusters_name", table_name="kubernetes_clusters")
    op.drop_index("ix_kubernetes_clusters_provider", table_name="kubernetes_clusters")
    op.drop_index("ix_kubernetes_clusters_cloud_account_id", table_name="kubernetes_clusters")
    op.drop_index("ix_kubernetes_clusters_tenant_id", table_name="kubernetes_clusters")
    op.drop_table("kubernetes_clusters")