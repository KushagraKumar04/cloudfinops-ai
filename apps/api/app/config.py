from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "info"
    database_url: str = "postgresql+psycopg://cloudfinops:cloudfinops@localhost:5432/cloudfinops"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    default_tenant_slug: str = "demo"
    encryption_key: str = ""
    aws_management_account_id: str = "000000000000"
    aws_external_id_prefix: str = "cloudfinops"
    app_base_url: str = "http://localhost:8000"
    mock_adapters: bool = False

    llm_enabled: bool = True
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_api_version: str = "2024-08-01-preview"
    llm_provider_override: str = ""
    llm_model_override: str = ""
    llm_timeout_seconds: int = 60
    llm_max_tool_iterations: int = 3

    auth_disabled: bool = False
    jwt_secret: str = "dev-insecure-change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24 * 7

    demo_mode: bool = True
    frontend_base_url: str = "http://localhost:5173"

    oauth_enabled: bool = False
    oauth_redirect_base_url: str = "http://localhost:8000"
    github_client_id: str = ""
    github_client_secret: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""

    worker_enabled: bool = True
    worker_queue_name: str = "cloudfinops"
    worker_job_timeout_seconds: int = 900
    worker_result_ttl_seconds: int = 3600

    aws_max_concurrency: int = 4
    aws_metrics_days: int = 30
    aws_cost_lookback_days: int = 90
    aws_discovery_services: str = "EC2,RDS,S3,EBS,EIP,EKS"
    aws_metric_coverage_threshold: float = 0.85

    audit_export_backend: str = "local"
    audit_export_local_root: str = "exports"
    audit_export_retention_days: int = 30
    audit_export_max_records: int = 100000

    audit_export_s3_bucket: str = ""
    audit_export_s3_prefix: str = "audit"
    audit_export_s3_region: str = ""
    audit_export_s3_endpoint_url: str = ""
    audit_export_s3_access_key_id: str = ""
    audit_export_s3_secret_access_key: str = ""
    audit_export_signed_url_ttl_seconds: int = 900

    audit_export_azure_container: str = ""
    audit_export_azure_connection_string: str = ""
    audit_export_azure_account_url: str = ""

    smtp_enabled: bool = False
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "notifications@cloudfinops.local"
    smtp_starttls: bool = False

    webhook_timeout_seconds: int = 10
    webhook_max_retries: int = 2

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()