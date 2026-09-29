from pydantic import Field

from app.schemas.base import CamelModel


class AwsConnectIn(CamelModel):
    name: str = Field(min_length=1, max_length=120)
    account_identifier: str = Field(min_length=12, max_length=12, pattern=r"^\d{12}$")
    role_arn: str = Field(min_length=20, max_length=255)
    environment: str = Field(default="production", max_length=32)
    regions: list[str] = Field(default_factory=lambda: ["us-east-1"])
    external_id: str | None = None


class AwsConnectOut(CamelModel):
    id: str
    external_id: str
    role_arn: str
    cloudformation_url: str
    trust_policy: dict
    note: str


class AzureConnectIn(CamelModel):
    name: str = Field(min_length=1, max_length=120)
    subscription_id: str = Field(min_length=1, max_length=120)
    tenant_id: str = Field(min_length=1, max_length=180)
    client_id: str = Field(min_length=1, max_length=128)
    client_secret: str = Field(min_length=1, max_length=512)
    environment: str = Field(default="production", max_length=32)


class AzureConnectOut(CamelModel):
    id: str
    subscription_id: str
    az_cli_command: str
    note: str


class VerifyOut(CamelModel):
    ok: bool
    message: str
    account_id: str | None = None