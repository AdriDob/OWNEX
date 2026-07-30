"""Cloud Backup System — Backup to S3, GCS, and other cloud providers.

Provides:
- CloudBackupProvider: abstract base for cloud backup providers
- S3BackupProvider: AWS S3 backup implementation
- GCSBackupProvider: Google Cloud Storage backup implementation
- CloudBackupManager: coordinator for cloud backup operations
- Automated scheduling with cron jobs
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.cloud_backup")


class CloudProvider(Enum):
    """Supported cloud providers."""

    AWS_S3 = "aws_s3"
    GOOGLE_CLOUD_STORAGE = "google_cloud_storage"
    AZURE_BLOB = "azure_blob"
    MINIO = "minio"


@dataclass
class CloudBackupConfig:
    """Configuration for cloud backup."""

    provider: CloudProvider
    bucket_name: str
    region: str | None = None
    access_key: str = ""
    secret_key: str = ""
    endpoint_url: str = ""  # For MinIO or other S3-compatible services
    prefix: str = "ownex-backups"  # Prefix for backup objects
    compression: bool = True
    encryption: bool = True
    retention_days: int = 30


class CloudBackupProvider(ABC):
    """Abstract base class for cloud backup providers."""

    def __init__(self, config: CloudBackupConfig):
        self.config = config
        self._client = None

    @abstractmethod
    def connect(self) -> bool:
        """Connect to the cloud provider."""
        pass

    @abstractmethod
    def upload_backup(self, backup_path: str, backup_name: str) -> dict[str, Any]:
        """Upload a backup to cloud storage."""
        pass

    @abstractmethod
    def download_backup(self, backup_name: str, destination: str) -> dict[str, Any]:
        """Download a backup from cloud storage."""
        pass

    @abstractmethod
    def list_backups(self) -> list[dict[str, Any]]:
        """List all backups in cloud storage."""
        pass

    @abstractmethod
    def delete_backup(self, backup_name: str) -> dict[str, Any]:
        """Delete a backup from cloud storage."""
        pass

    @abstractmethod
    def get_backup_url(self, backup_name: str, expires_in: int = 3600) -> str:
        """Generate a presigned URL for backup download."""
        pass


class S3BackupProvider(CloudBackupProvider):
    """AWS S3 backup provider."""

    def __init__(self, config: CloudBackupConfig):
        super().__init__(config)
        self._s3_client = None

    def connect(self) -> bool:
        """Connect to AWS S3."""
        try:
            import boto3
            from botocore.exceptions import ClientError

            s3_config = {
                "aws_access_key_id": self.config.access_key,
                "aws_secret_access_key": self.config.secret_key,
            }

            if self.config.region:
                s3_config["region_name"] = self.config.region

            if self.config.endpoint_url:
                s3_config["endpoint_url"] = self.config.endpoint_url

            self._s3_client = boto3.client("s3", **s3_config)

            # Test connection
            self._s3_client.head_bucket(Bucket=self.config.bucket_name)

            logger.info(f"[CLOUD BACKUP] Connected to S3 bucket: {self.config.bucket_name}")
            return True

        except ImportError:
            logger.error("[CLOUD BACKUP] boto3 not installed")
            return False
        except ClientError as e:
            logger.error(f"[CLOUD BACKUP] Failed to connect to S3: {e}")
            return False

    def upload_backup(self, backup_path: str, backup_name: str) -> dict[str, Any]:
        """Upload a backup to S3."""
        if not self._s3_client:
            self.connect()

        try:
            import shutil

            backup_path = Path(backup_path)

            # Compress if enabled
            if self.config.compression:
                import zipfile

                zip_path = backup_path.with_suffix(".zip")
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                    for item in backup_path.rglob("*"):
                        if item.is_file():
                            zipf.write(item, item.relative_to(backup_path))
                upload_path = zip_path
            else:
                upload_path = backup_path

            # Generate object key
            object_key = f"{self.config.prefix}/{backup_name}"
            if self.config.compression:
                object_key += ".zip"

            # Upload
            extra_args = {}
            if self.config.encryption:
                extra_args["ServerSideEncryption"] = "AES256"

            self._s3_client.upload_file(
                str(upload_path),
                self.config.bucket_name,
                object_key,
                ExtraArgs=extra_args if extra_args else None,
            )

            # Cleanup zip file if created
            if self.config.compression and upload_path != backup_path:
                upload_path.unlink()

            logger.info(f"[CLOUD BACKUP] Uploaded backup to S3: {object_key}")

            return {
                "success": True,
                "provider": "s3",
                "bucket": self.config.bucket_name,
                "object_key": object_key,
                "size": backup_path.stat().st_size,
            }

        except Exception as e:
            logger.error(f"[CLOUD BACKUP] Failed to upload to S3: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def download_backup(self, backup_name: str, destination: str) -> dict[str, Any]:
        """Download a backup from S3."""
        if not self._s3_client:
            self.connect()

        try:
            object_key = f"{self.config.prefix}/{backup_name}"
            if self.config.compression:
                object_key += ".zip"

            dest_path = Path(destination)
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            self._s3_client.download_file(
                self.config.bucket_name,
                object_key,
                str(dest_path),
            )

            # Decompress if needed
            if self.config.compression and dest_path.suffix == ".zip":
                import zipfile

                extract_path = dest_path.parent / dest_path.stem
                with zipfile.ZipFile(dest_path, "r") as zipf:
                    zipf.extractall(extract_path)
                dest_path.unlink()
                dest_path = extract_path

            logger.info(f"[CLOUD BACKUP] Downloaded backup from S3: {object_key}")

            return {
                "success": True,
                "provider": "s3",
                "object_key": object_key,
                "destination": str(dest_path),
            }

        except Exception as e:
            logger.error(f"[CLOUD BACKUP] Failed to download from S3: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def list_backups(self) -> list[dict[str, Any]]:
        """List all backups in S3."""
        if not self._s3_client:
            self.connect()

        try:
            response = self._s3_client.list_objects_v2(
                Bucket=self.config.bucket_name,
                Prefix=self.config.prefix,
            )

            backups = []
            for obj in response.get("Contents", []):
                object_key = obj["Key"]
                backup_name = object_key.replace(f"{self.config.prefix}/", "").replace(".zip", "")
                backups.append({
                    "name": backup_name,
                    "object_key": object_key,
                    "size": obj["Size"],
                    "last_modified": obj["LastModified"].isoformat(),
                    "provider": "s3",
                })

            return backups

        except Exception as e:
            logger.error(f"[CLOUD BACKUP] Failed to list S3 backups: {e}")
            return []

    def delete_backup(self, backup_name: str) -> dict[str, Any]:
        """Delete a backup from S3."""
        if not self._s3_client:
            self.connect()

        try:
            object_key = f"{self.config.prefix}/{backup_name}"
            if self.config.compression:
                object_key += ".zip"

            self._s3_client.delete_object(
                Bucket=self.config.bucket_name,
                Key=object_key,
            )

            logger.info(f"[CLOUD BACKUP] Deleted backup from S3: {object_key}")

            return {
                "success": True,
                "provider": "s3",
                "object_key": object_key,
            }

        except Exception as e:
            logger.error(f"[CLOUD BACKUP] Failed to delete from S3: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def get_backup_url(self, backup_name: str, expires_in: int = 3600) -> str:
        """Generate a presigned URL for backup download."""
        if not self._s3_client:
            self.connect()

        try:
            object_key = f"{self.config.prefix}/{backup_name}"
            if self.config.compression:
                object_key += ".zip"

            url = self._s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.config.bucket_name,
                    "Key": object_key,
                },
                ExpiresIn=expires_in,
            )

            return url

        except Exception as e:
            logger.error(f"[CLOUD BACKUP] Failed to generate presigned URL: {e}")
            return ""


class GCSBackupProvider(CloudBackupProvider):
    """Google Cloud Storage backup provider."""

    def __init__(self, config: CloudBackupConfig):
        super().__init__(config)
        self._gcs_client = None

    def connect(self) -> bool:
        """Connect to Google Cloud Storage."""
        try:
            from google.cloud import storage

            self._gcs_client = storage.Client()
            bucket = self._gcs_client.bucket(self.config.bucket_name)

            # Test connection
            bucket.blob("test").delete()

            logger.info(f"[CLOUD BACKUP] Connected to GCS bucket: {self.config.bucket_name}")
            return True

        except ImportError:
            logger.error("[CLOUD BACKUP] google-cloud-storage not installed")
            return False
        except Exception as e:
            logger.error(f"[CLOUD BACKUP] Failed to connect to GCS: {e}")
            return False

    def upload_backup(self, backup_path: str, backup_name: str) -> dict[str, Any]:
        """Upload a backup to GCS."""
        if not self._gcs_client:
            self.connect()

        try:
            import shutil

            backup_path = Path(backup_path)

            # Compress if enabled
            if self.config.compression:
                import zipfile

                zip_path = backup_path.with_suffix(".zip")
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                    for item in backup_path.rglob("*"):
                        if item.is_file():
                            zipf.write(item, item.relative_to(backup_path))
                upload_path = zip_path
            else:
                upload_path = backup_path

            # Generate object key
            object_key = f"{self.config.prefix}/{backup_name}"
            if self.config.compression:
                object_key += ".zip"

            # Upload
            bucket = self._gcs_client.bucket(self.config.bucket_name)
            blob = bucket.blob(object_key)

            if self.config.encryption:
                blob.upload_from_filename(str(upload_path), encryption_key=self.config.secret_key)
            else:
                blob.upload_from_filename(str(upload_path))

            # Cleanup zip file if created
            if self.config.compression and upload_path != backup_path:
                upload_path.unlink()

            logger.info(f"[CLOUD BACKUP] Uploaded backup to GCS: {object_key}")

            return {
                "success": True,
                "provider": "gcs",
                "bucket": self.config.bucket_name,
                "object_key": object_key,
                "size": backup_path.stat().st_size,
            }

        except Exception as e:
            logger.error(f"[CLOUD BACKUP] Failed to upload to GCS: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def download_backup(self, backup_name: str, destination: str) -> dict[str, Any]:
        """Download a backup from GCS."""
        if not self._gcs_client:
            self.connect()

        try:
            object_key = f"{self.config.prefix}/{backup_name}"
            if self.config.compression:
                object_key += ".zip"

            dest_path = Path(destination)
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            bucket = self._gcs_client.bucket(self.config.bucket_name)
            blob = bucket.blob(object_key)

            if self.config.encryption:
                blob.download_to_filename(str(dest_path), encryption_key=self.config.secret_key)
            else:
                blob.download_to_filename(str(dest_path))

            # Decompress if needed
            if self.config.compression and dest_path.suffix == ".zip":
                import zipfile

                extract_path = dest_path.parent / dest_path.stem
                with zipfile.ZipFile(dest_path, "r") as zipf:
                    zipf.extractall(extract_path)
                dest_path.unlink()
                dest_path = extract_path

            logger.info(f"[CLOUD BACKUP] Downloaded backup from GCS: {object_key}")

            return {
                "success": True,
                "provider": "gcs",
                "object_key": object_key,
                "destination": str(dest_path),
            }

        except Exception as e:
            logger.error(f"[CLOUD BACKUP] Failed to download from GCS: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def list_backups(self) -> list[dict[str, Any]]:
        """List all backups in GCS."""
        if not self._gcs_client:
            self.connect()

        try:
            bucket = self._gcs_client.bucket(self.config.bucket_name)
            blobs = bucket.list_blobs(prefix=self.config.prefix)

            backups = []
            for blob in blobs:
                object_key = blob.name
                backup_name = object_key.replace(f"{self.config.prefix}/", "").replace(".zip", "")
                backups.append({
                    "name": backup_name,
                    "object_key": object_key,
                    "size": blob.size,
                    "last_modified": blob.time_created.isoformat(),
                    "provider": "gcs",
                })

            return backups

        except Exception as e:
            logger.error(f"[CLOUD BACKUP] Failed to list GCS backups: {e}")
            return []

    def delete_backup(self, backup_name: str) -> dict[str, Any]:
        """Delete a backup from GCS."""
        if not self._gcs_client:
            self.connect()

        try:
            object_key = f"{self.config.prefix}/{backup_name}"
            if self.config.compression:
                object_key += ".zip"

            bucket = self._gcs_client.bucket(self.config.bucket_name)
            blob = bucket.blob(object_key)
            blob.delete()

            logger.info(f"[CLOUD BACKUP] Deleted backup from GCS: {object_key}")

            return {
                "success": True,
                "provider": "gcs",
                "object_key": object_key,
            }

        except Exception as e:
            logger.error(f"[CLOUD BACKUP] Failed to delete from GCS: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def get_backup_url(self, backup_name: str, expires_in: int = 3600) -> str:
        """Generate a signed URL for backup download."""
        if not self._gcs_client:
            self.connect()

        try:
            object_key = f"{self.config.prefix}/{backup_name}"
            if self.config.compression:
                object_key += ".zip"

            bucket = self._gcs_client.bucket(self.config.bucket_name)
            blob = bucket.blob(object_key)

            url = blob.generate_signed_url(expiration=expires_in)

            return url

        except Exception as e:
            logger.error(f"[CLOUD BACKUP] Failed to generate signed URL: {e}")
            return ""


class CloudBackupManager:
    """Manager for cloud backup operations."""

    def __init__(self, config: CloudBackupConfig):
        self.config = config
        self._provider = self._create_provider()

    def _create_provider(self) -> CloudBackupProvider:
        """Create the appropriate provider based on config."""
        if self.config.provider == CloudProvider.AWS_S3:
            return S3BackupProvider(self.config)
        elif self.config.provider == CloudProvider.GOOGLE_CLOUD_STORAGE:
            return GCSBackupProvider(self.config)
        else:
            raise ValueError(f"Unsupported provider: {self.config.provider}")

    def upload_to_cloud(self, backup_path: str, backup_name: str) -> dict[str, Any]:
        """Upload a local backup to cloud storage."""
        logger.info(f"[CLOUD BACKUP] Uploading backup to cloud: {backup_name}")
        return self._provider.upload_backup(backup_path, backup_name)

    def download_from_cloud(self, backup_name: str, destination: str) -> dict[str, Any]:
        """Download a backup from cloud storage."""
        logger.info(f"[CLOUD BACKUP] Downloading backup from cloud: {backup_name}")
        return self._provider.download_backup(backup_name, destination)

    def list_cloud_backups(self) -> list[dict[str, Any]]:
        """List all backups in cloud storage."""
        logger.info("[CLOUD BACKUP] Listing cloud backups")
        return self._provider.list_backups()

    def delete_from_cloud(self, backup_name: str) -> dict[str, Any]:
        """Delete a backup from cloud storage."""
        logger.info(f"[CLOUD BACKUP] Deleting backup from cloud: {backup_name}")
        return self._provider.delete_backup(backup_name)

    def get_backup_download_url(self, backup_name: str, expires_in: int = 3600) -> str:
        """Generate a download URL for a backup."""
        return self._provider.get_backup_url(backup_name, expires_in)

    def sync_to_cloud(self, local_backup_path: str) -> dict[str, Any]:
        """Sync a local backup to cloud (upload + verify)."""
        # Upload
        backup_name = Path(local_backup_path).name
        upload_result = self.upload_to_cloud(local_backup_path, backup_name)

        if not upload_result.get("success"):
            return upload_result

        # Verify by listing
        cloud_backups = self.list_cloud_backups()
        backup_exists = any(b["name"] == backup_name for b in cloud_backups)

        if backup_exists:
            logger.info(f"[CLOUD BACKUP] Sync successful: {backup_name}")
            return {
                "success": True,
                "backup_name": backup_name,
                "cloud_provider": self.config.provider.value,
            }
        else:
            return {
                "success": False,
                "error": "Backup not found in cloud after upload",
            }

    def cleanup_old_backups(self) -> dict[str, Any]:
        """Clean up old backups based on retention policy."""
        if self.config.retention_days <= 0:
            return {"success": True, "deleted": 0}

        from datetime import timedelta

        cutoff_date = datetime.now(UTC) - timedelta(days=self.config.retention_days)
        cloud_backups = self.list_cloud_backups()

        deleted_count = 0
        for backup in cloud_backups:
            backup_date = datetime.fromisoformat(backup["last_modified"])
            if backup_date < cutoff_date:
                result = self.delete_from_cloud(backup["name"])
                if result.get("success"):
                    deleted_count += 1

        logger.info(f"[CLOUD BACKUP] Cleaned up {deleted_count} old backups")

        return {
            "success": True,
            "deleted": deleted_count,
            "retention_days": self.config.retention_days,
        }


# Singleton instance
_cloud_backup_manager: CloudBackupManager | None = None


def get_cloud_backup_manager(config: CloudBackupConfig | None = None) -> CloudBackupManager:
    """Get singleton cloud backup manager instance."""
    global _cloud_backup_manager
    if _cloud_backup_manager is None and config is not None:
        _cloud_backup_manager = CloudBackupManager(config)
    return _cloud_backup_manager


def reset_cloud_backup_manager() -> None:
    """Reset cloud backup manager instance (for testing)."""
    global _cloud_backup_manager
    _cloud_backup_manager = None
