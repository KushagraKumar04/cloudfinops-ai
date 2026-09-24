from app.adapters.aws import AWSAdapter
from app.adapters.azure import AzureAdapter
from app.adapters.base import CloudProviderAdapter

__all__ = ["CloudProviderAdapter", "AWSAdapter", "AzureAdapter", "get_adapter"]


def get_adapter(provider: str) -> CloudProviderAdapter:
    normalized = provider.strip().lower()
    if normalized == "aws":
        return AWSAdapter()
    if normalized == "azure":
        return AzureAdapter()
    raise ValueError(f"Unsupported provider: {provider}")