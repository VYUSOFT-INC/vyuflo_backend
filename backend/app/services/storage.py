"""
File storage service — local disk in dev, Amazon S3 in production.
Switches on settings.STORAGE_BACKEND ("local" or "s3").
"""
import os
import aioboto3
from app.core.config import settings

_session = aioboto3.Session(
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_REGION,
)


async def upload_file(content: bytes, key: str, content_type: str) -> None:
    """Save bytes under `key` (S3 object key / relative path)."""
    if settings.STORAGE_BACKEND == "s3":
        async with _session.client("s3") as s3:
            await s3.put_object(
                Bucket=settings.S3_BUCKET,
                Key=key,
                Body=content,
                ContentType=content_type,
                ServerSideEncryption="AES256",  # encryption at rest
            )
    else:  # local dev — served by your existing static mount
        path = f"./{key}"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(content)


async def get_presigned_url(key: str, expires: int = 900) -> str:
    """Temporary signed URL (15 min). Bucket stays private."""
    if settings.STORAGE_BACKEND == "s3":
        async with _session.client("s3") as s3:
            return await s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": settings.S3_BUCKET, "Key": key},
                ExpiresIn=expires,
            )
    else:
        return f"/{key}"  # local: hits your static files


async def delete_file(key: str) -> None:
    """Delete an object by key."""
    if settings.STORAGE_BACKEND == "s3":
        async with _session.client("s3") as s3:
            await s3.delete_object(Bucket=settings.S3_BUCKET, Key=key)
    else:
        path = f"./{key}"
        if os.path.exists(path):
            os.remove(path)