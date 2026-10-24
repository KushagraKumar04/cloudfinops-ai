import uuid
from datetime import date, datetime
from typing import Any

from pydantic import Field, field_validator

from app.schemas.base import CamelModel


class ClusterOut(CamelModel):
    id: uuid.UUID
    cloud_account_id: uuid.UUID
    account_name: str = ""
    provider: str
    name: str
    version: str = ""
    region: str
    status: str
    node_count: int = 0
    total_cpu_cores: float = 0
    total_memory_gb: float = 0
    monthly_cost: float = 0
    currency: str = "USD"
    created_at: datetime
    updated_at: datetime
    namespace_count: int = 0
    workload_count: int = 0
    over_provisioned_count: int = 0
    potential_savings: float = 0

    @field_validator(
        "total_cpu_cores",
        "total_memory_gb",
        "monthly_cost",
        "potential_savings",
        mode="before",
    )
    @classmethod
    def coerce_decimal(cls, v):
        if v is None:
            return 0
        return float(v)


class NamespaceOut(CamelModel):
    id: uuid.UUID
    cluster_id: uuid.UUID
    name: str
    cpu_request_cores: float = 0
    cpu_limit_cores: float = 0
    cpu_usage_avg_cores: float = 0
    memory_request_gb: float = 0
    memory_limit_gb: float = 0
    memory_usage_avg_gb: float = 0
    monthly_cost: float = 0
    currency: str = "USD"
    labels: dict[str, str] = Field(default_factory=dict)

    @field_validator(
        "cpu_request_cores",
        "cpu_limit_cores",
        "cpu_usage_avg_cores",
        "memory_request_gb",
        "memory_limit_gb",
        "memory_usage_avg_gb",
        "monthly_cost",
        mode="before",
    )
    @classmethod
    def coerce_decimal(cls, v):
        if v is None:
            return 0
        return float(v)


class WorkloadOut(CamelModel):
    id: uuid.UUID
    cluster_id: uuid.UUID
    namespace_id: uuid.UUID
    namespace_name: str = ""
    name: str
    kind: str
    replicas: int = 1
    cpu_request_cores: float = 0
    cpu_limit_cores: float = 0
    cpu_usage_avg_cores: float = 0
    memory_request_gb: float = 0
    memory_limit_gb: float = 0
    memory_usage_avg_gb: float = 0
    monthly_cost: float = 0
    potential_savings: float = 0
    over_provisioned: bool = False
    currency: str = "USD"
    labels: dict[str, str] = Field(default_factory=dict)

    @field_validator(
        "cpu_request_cores",
        "cpu_limit_cores",
        "cpu_usage_avg_cores",
        "memory_request_gb",
        "memory_limit_gb",
        "memory_usage_avg_gb",
        "monthly_cost",
        "potential_savings",
        mode="before",
    )
    @classmethod
    def coerce_decimal(cls, v):
        if v is None:
            return 0
        return float(v)


class CostAllocationOut(CamelModel):
    date: date
    cost: float = 0
    cpu_cost: float = 0
    memory_cost: float = 0
    storage_cost: float = 0
    network_cost: float = 0

    @field_validator(
        "cost", "cpu_cost", "memory_cost", "storage_cost", "network_cost", mode="before"
    )
    @classmethod
    def coerce_decimal(cls, v):
        if v is None:
            return 0
        return float(v)


class ClusterDetail(CamelModel):
    cluster: ClusterOut
    namespaces: list[NamespaceOut] = Field(default_factory=list)
    workloads: list[WorkloadOut] = Field(default_factory=list)


class ClusterListOut(CamelModel):
    items: list[ClusterOut]
    total: int
    aggregates: dict[str, Any] = Field(default_factory=dict)


class CostTrendPoint(CamelModel):
    date: date
    cost: float
    cpu_cost: float = 0
    memory_cost: float = 0
    storage_cost: float = 0
    network_cost: float = 0

    @field_validator(
        "cost", "cpu_cost", "memory_cost", "storage_cost", "network_cost", mode="before"
    )
    @classmethod
    def coerce_decimal(cls, v):
        if v is None:
            return 0
        return float(v)