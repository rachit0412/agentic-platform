"""
Cloud Storage Connector — Pull files from S3, Azure Blob, Google Cloud Storage.

Lists objects in a bucket/container, filters by extension, downloads content
and stages into filestore for indexing.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx", ".csv", ".json", ".html", ".xml", ".rst", ".log"}


def pull_cloud_storage(config: dict) -> list[dict]:
    """
    List and download files from cloud storage.
    Returns list of {"name": str, "content": str|bytes, "metadata": dict}
    """
    provider = config["provider"]
    bucket = config["bucket"]
    prefix = config.get("prefix", "")
    ext_filter = config.get("file_extensions", "")
    allowed_exts = {e.strip() for e in ext_filter.split(",") if e.strip()} if ext_filter else SUPPORTED_EXTENSIONS

    if provider == "s3":
        return _pull_s3(bucket, prefix, allowed_exts, config)
    elif provider == "azure_blob":
        return _pull_azure_blob(bucket, prefix, allowed_exts, config)
    elif provider == "gcs":
        return _pull_gcs(bucket, prefix, allowed_exts, config)
    else:
        raise ValueError(f"Unsupported provider: {provider}")


def test_connection(config: dict) -> dict:
    """Test cloud storage connectivity."""
    provider = config["provider"]
    try:
        if provider == "s3":
            import boto3
            session = boto3.Session(
                aws_access_key_id=config.get("access_key"),
                aws_secret_access_key=config.get("secret_key"),
            )
            s3 = session.client("s3")
            s3.head_bucket(Bucket=config["bucket"])
        elif provider == "azure_blob":
            from azure.storage.blob import BlobServiceClient
            client = BlobServiceClient.from_connection_string(config["connection_string"])
            container = client.get_container_client(config["bucket"])
            container.get_container_properties()
        elif provider == "gcs":
            from google.cloud import storage
            client = storage.Client()
            bucket = client.get_bucket(config["bucket"])
        return {"ok": True, "message": f"Connected to {provider}://{config['bucket']}"}
    except ImportError as e:
        return {"ok": False, "message": f"Missing dependency: {e}"}
    except Exception as e:
        return {"ok": False, "message": str(e)}


def _pull_s3(bucket: str, prefix: str, allowed_exts: set, config: dict) -> list[dict]:
    """Pull from AWS S3."""
    try:
        import boto3
    except ImportError:
        raise ImportError("boto3 not installed. Run: pip install boto3")

    session = boto3.Session(
        aws_access_key_id=config.get("access_key"),
        aws_secret_access_key=config.get("secret_key"),
    )
    s3 = session.client("s3")

    documents = []
    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

    for page in pages:
        for obj in page.get("Contents", []):
            key = obj["Key"]
            ext = os.path.splitext(key)[1].lower()
            if ext not in allowed_exts:
                continue
            if obj["Size"] > 50 * 1024 * 1024:  # Skip files > 50MB
                continue

            response = s3.get_object(Bucket=bucket, Key=key)
            body = response["Body"].read()
            content = body.decode("utf-8", errors="replace")

            documents.append({
                "name": os.path.basename(key),
                "content": content,
                "metadata": {"source": f"s3://{bucket}/{key}", "size": obj["Size"]},
            })

    logger.info(f"S3 connector pulled {len(documents)} files from s3://{bucket}/{prefix}")
    return documents


def _pull_azure_blob(container_name: str, prefix: str, allowed_exts: set, config: dict) -> list[dict]:
    """Pull from Azure Blob Storage."""
    try:
        from azure.storage.blob import BlobServiceClient
    except ImportError:
        raise ImportError("azure-storage-blob not installed. Run: pip install azure-storage-blob")

    client = BlobServiceClient.from_connection_string(config["connection_string"])
    container = client.get_container_client(container_name)

    documents = []
    blobs = container.list_blobs(name_starts_with=prefix)

    for blob in blobs:
        ext = os.path.splitext(blob.name)[1].lower()
        if ext not in allowed_exts:
            continue
        if blob.size > 50 * 1024 * 1024:
            continue

        blob_client = container.get_blob_client(blob.name)
        data = blob_client.download_blob().readall()
        content = data.decode("utf-8", errors="replace")

        documents.append({
            "name": os.path.basename(blob.name),
            "content": content,
            "metadata": {"source": f"azure://{container_name}/{blob.name}", "size": blob.size},
        })

    logger.info(f"Azure Blob connector pulled {len(documents)} files from {container_name}/{prefix}")
    return documents


def _pull_gcs(bucket_name: str, prefix: str, allowed_exts: set, config: dict) -> list[dict]:
    """Pull from Google Cloud Storage."""
    try:
        from google.cloud import storage
    except ImportError:
        raise ImportError("google-cloud-storage not installed. Run: pip install google-cloud-storage")

    client = storage.Client()
    bucket = client.bucket(bucket_name)

    documents = []
    blobs = bucket.list_blobs(prefix=prefix)

    for blob in blobs:
        ext = os.path.splitext(blob.name)[1].lower()
        if ext not in allowed_exts:
            continue
        if blob.size > 50 * 1024 * 1024:
            continue

        data = blob.download_as_bytes()
        content = data.decode("utf-8", errors="replace")

        documents.append({
            "name": os.path.basename(blob.name),
            "content": content,
            "metadata": {"source": f"gcs://{bucket_name}/{blob.name}", "size": blob.size},
        })

    logger.info(f"GCS connector pulled {len(documents)} files from gs://{bucket_name}/{prefix}")
    return documents
