"""
MinIO / S3-compatible image storage helper.
Saves try-on results and uploads to MinIO (local dev) → Cloudflare R2 (prod).

MinIO is already in docker-compose.yml (port 9000, console 9001).
"""

import io
import logging
import os
from pathlib import Path
from typing import Optional
import uuid

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client

    try:
        import boto3
        from botocore.client import Config

        endpoint = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
        access   = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        secret   = os.getenv("MINIO_SECRET_KEY", "minioadmin")
        region   = os.getenv("MINIO_REGION", "us-east-1")

        _client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access,
            aws_secret_access_key=secret,
            region_name=region,
            config=Config(signature_version="s3v4"),
        )
        logger.info(f"✅ MinIO client connected → {endpoint}")
    except ImportError:
        logger.warning("boto3 not installed — storage disabled")
    except Exception as e:
        logger.warning(f"MinIO connection failed: {e} — storage disabled")

    return _client


def _ensure_bucket(bucket: str):
    client = _get_client()
    if client is None:
        return
    try:
        client.head_bucket(Bucket=bucket)
    except Exception:
        try:
            client.create_bucket(Bucket=bucket)
            logger.info(f"✅ Created MinIO bucket: {bucket}")
        except Exception as e:
            logger.warning(f"Could not create bucket {bucket}: {e}")


def save_result(
    image_bytes: bytes,
    content_type: str = "image/jpeg",
    bucket: str = "tryon-results",
    prefix: str = "results/",
) -> Optional[str]:
    """
    Upload image to MinIO and return the public URL.
    Returns None if MinIO is unavailable (non-blocking).
    """
    client = _get_client()
    if client is None:
        return None

    _ensure_bucket(bucket)

    ext      = "jpg" if "jpeg" in content_type else "png"
    key      = f"{prefix}{uuid.uuid4().hex}.{ext}"

    try:
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=io.BytesIO(image_bytes),
            ContentType=content_type,
            ContentLength=len(image_bytes),
        )
        endpoint = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
        url = f"{endpoint}/{bucket}/{key}"
        logger.info(f"✅ Saved to MinIO: {url}")
        return url
    except Exception as e:
        logger.warning(f"MinIO upload failed: {e}")
        return None


def save_garment(image_bytes: bytes, garment_id: str) -> Optional[str]:
    """Upload a garment image to the garment-catalog bucket."""
    return save_result(
        image_bytes,
        bucket="garment-catalog",
        prefix=f"garments/{garment_id}/",
    )
