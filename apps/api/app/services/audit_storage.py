import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.config import get_settings


class StorageError(Exception):
    pass


@dataclass
class StoredObject:
    backend: str
    object_key: str
    size_bytes: int


class AuditStorage(Protocol):
    backend: str

    def put(self, object_key: str, payload: bytes) -> StoredObject: ...

    def signed_url(self, object_key: str, ttl_seconds: int) -> str: ...

    def delete(self, object_key: str) -> None: ...


class LocalStorage:
    backend = "local"

    def __init__(self, root: str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path_for(self, object_key: str) -> Path:
        safe = Path(object_key.lstrip("/"))
        target = (self.root / safe).resolve()
        if self.root.resolve() not in target.parents and target != self.root.resolve():
            raise StorageError("Path traversal detected")
        return target

    def put(self, object_key: str, payload: bytes) -> StoredObject:
        path = self._path_for(object_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return StoredObject(backend=self.backend, object_key=object_key, size_bytes=len(payload))

    def signed_url(self, object_key: str, ttl_seconds: int) -> str:
        settings = get_settings()
        return f"{settings.app_base_url}/api/v1/audit/exports/download?key={object_key}"

    def delete(self, object_key: str) -> None:
        path = self._path_for(object_key)
        if path.exists():
            path.unlink()

    def read(self, object_key: str) -> bytes:
        path = self._path_for(object_key)
        if not path.exists():
            raise StorageError("Object not found")
        return path.read_bytes()


class S3Storage:
    backend = "s3"

    def __init__(self) -> None:
        import boto3

        settings = get_settings()
        if not settings.audit_export_s3_bucket:
            raise StorageError("AUDIT_EXPORT_S3_BUCKET is not configured")
        kwargs: dict = {}
        if settings.audit_export_s3_region:
            kwargs["region_name"] = settings.audit_export_s3_region
        if settings.audit_export_s3_endpoint_url:
            kwargs["endpoint_url"] = settings.audit_export_s3_endpoint_url
        if settings.audit_export_s3_access_key_id and settings.audit_export_s3_secret_access_key:
            kwargs["aws_access_key_id"] = settings.audit_export_s3_access_key_id
            kwargs["aws_secret_access_key"] = settings.audit_export_s3_secret_access_key
        self._client = boto3.client("s3", **kwargs)
        self._bucket = settings.audit_export_s3_bucket
        self._prefix = settings.audit_export_s3_prefix.strip("/")

    def _key(self, object_key: str) -> str:
        if self._prefix:
            return f"{self._prefix}/{object_key.lstrip('/')}"
        return object_key.lstrip("/")

    def put(self, object_key: str, payload: bytes) -> StoredObject:
        key = self._key(object_key)
        try:
            self._client.put_object(Bucket=self._bucket, Key=key, Body=payload)
        except Exception as exc:
            raise StorageError(f"S3 put failed: {exc}") from exc
        return StoredObject(backend=self.backend, object_key=object_key, size_bytes=len(payload))

    def signed_url(self, object_key: str, ttl_seconds: int) -> str:
        key = self._key(object_key)
        try:
            return self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=ttl_seconds,
            )
        except Exception as exc:
            raise StorageError(f"S3 presign failed: {exc}") from exc

    def delete(self, object_key: str) -> None:
        key = self._key(object_key)
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
        except Exception as exc:
            raise StorageError(f"S3 delete failed: {exc}") from exc


class AzureBlobStorage:
    backend = "azure"

    def __init__(self) -> None:
        from azure.storage.blob import BlobServiceClient

        settings = get_settings()
        if not settings.audit_export_azure_container:
            raise StorageError("AUDIT_EXPORT_AZURE_CONTAINER is not configured")
        if settings.audit_export_azure_connection_string:
            self._service = BlobServiceClient.from_connection_string(
                settings.audit_export_azure_connection_string
            )
        elif settings.audit_export_azure_account_url:
            from azure.identity import DefaultAzureCredential

            self._service = BlobServiceClient(
                account_url=settings.audit_export_azure_account_url,
                credential=DefaultAzureCredential(),
            )
        else:
            raise StorageError("Azure Blob requires a connection string or account URL")
        self._container = settings.audit_export_azure_container

    def put(self, object_key: str, payload: bytes) -> StoredObject:
        try:
            blob = self._service.get_blob_client(container=self._container, blob=object_key)
            blob.upload_blob(payload, overwrite=True)
        except Exception as exc:
            raise StorageError(f"Azure put failed: {exc}") from exc
        return StoredObject(backend=self.backend, object_key=object_key, size_bytes=len(payload))

    def signed_url(self, object_key: str, ttl_seconds: int) -> str:
        from datetime import UTC, datetime, timedelta

        from azure.storage.blob import BlobSasPermissions, generate_blob_sas

        settings = get_settings()
        if not settings.audit_export_azure_connection_string:
            raise StorageError("Signed URLs require a connection string")
        parts = dict(
            kv.split("=", 1)
            for kv in settings.audit_export_azure_connection_string.split(";")
            if "=" in kv
        )
        account_name = parts.get("AccountName", "")
        account_key = parts.get("AccountKey", "")
        if not account_name or not account_key:
            raise StorageError("Connection string missing AccountName or AccountKey")

        sas = generate_blob_sas(
            account_name=account_name,
            container_name=self._container,
            blob_name=object_key,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(UTC) + timedelta(seconds=ttl_seconds),
        )
        return f"https://{account_name}.blob.core.windows.net/{self._container}/{object_key}?{sas}"

    def delete(self, object_key: str) -> None:
        try:
            blob = self._service.get_blob_client(container=self._container, blob=object_key)
            blob.delete_blob(delete_snapshots="include")
        except Exception as exc:
            raise StorageError(f"Azure delete failed: {exc}") from exc


_storage: AuditStorage | None = None


def get_storage() -> AuditStorage:
    global _storage
    if _storage is not None:
        return _storage

    settings = get_settings()
    backend = settings.audit_export_backend.strip().lower()
    if backend == "s3":
        _storage = S3Storage()
    elif backend == "azure":
        _storage = AzureBlobStorage()
    else:
        root = settings.audit_export_local_root
        if not os.path.isabs(root):
            root = os.path.join(os.getcwd(), root)
        _storage = LocalStorage(root)
    return _storage


def reset_storage() -> None:
    global _storage
    _storage = None


def build_object_key(tenant_id: uuid.UUID, export_id: uuid.UUID, fmt: str) -> str:
    return f"{tenant_id}/{export_id}.{fmt}"