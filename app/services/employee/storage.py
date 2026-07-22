# """
# File storage service — local disk in dev, Amazon S3 in production.
# Switches on settings.STORAGE_BACKEND ("local" or "s3").
# """
# import os
# import aioboto3 
# from app.core.config import settings

# _session = aioboto3.Session(
#     aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
#     aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
#     region_name=settings.AWS_REGION,
# )


# async def upload_file(content: bytes, key: str, content_type: str) -> None:
#     """Save bytes under `key` (S3 object key / relative path)."""
#     if settings.STORAGE_BACKEND == "s3":
#         async with _session.client("s3") as s3:
#             await s3.put_object(
#                 Bucket=settings.S3_BUCKET,
#                 Key=key,
#                 Body=content,
#                 ContentType=content_type,
#                 ServerSideEncryption="AES256",  # encryption at rest
#             )
#     else:  # local dev — served by your existing static mount
#         path = f"./{key}"
#         os.makedirs(os.path.dirname(path), exist_ok=True)
#         with open(path, "wb") as f:
#             f.write(content)


# async def get_presigned_url(key: str, expires: int = 900) -> str:
#     """Temporary signed URL (15 min). Bucket stays private."""
#     if settings.STORAGE_BACKEND == "s3":
#         async with _session.client("s3") as s3:
#             return await s3.generate_presigned_url(
#                 "get_object",
#                 Params={"Bucket": settings.S3_BUCKET, "Key": key},
#                 ExpiresIn=expires,
#             )
#     else:
#         return f"/{key}"  # local: hits your static files


# async def delete_file(key: str) -> None:
#     """Delete an object by key."""
#     if settings.STORAGE_BACKEND == "s3":
#         async with _session.client("s3") as s3:
#             await s3.delete_object(Bucket=settings.S3_BUCKET, Key=key)
#     else:
#         path = f"./{key}"
#         if os.path.exists(path):
#             os.remove(path)



"""
File storage service — local disk in dev, Amazon S3 / DigitalOcean Spaces in production.
Switches on settings.STORAGE_BACKEND ("local" or "s3").
"""
import os
import aioboto3
from botocore.config import Config
from app.core.config import settings

_session = aioboto3.Session(
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_REGION,
)


# def _client():
#     """Single place that builds the S3/Spaces client — endpoint + path-style addressing."""
#     return _session.client(
#         "s3",
#         endpoint_url=settings.S3_ENDPOINT_URL,
#         config=Config(s3={"addressing_style": "path"}),  # needed because bucket name has a dot
#     )

def _client():
    if not settings.S3_ENDPOINT_URL:
        raise RuntimeError("S3_ENDPOINT_URL is required when STORAGE_BACKEND=s3")
    return _session.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        config=Config(s3={"addressing_style": "path"}),
    )

async def upload_file(content: bytes, key: str, content_type: str) -> None:
    """Save bytes under `key` (S3 object key / relative path)."""
    if settings.STORAGE_BACKEND == "s3":
        async with _client() as s3:
            await s3.put_object(
                Bucket=settings.S3_BUCKET,
                Key=key,
                Body=content,
                ContentType=content_type,
                # NOTE: no ServerSideEncryption param — Spaces rejects AES256 on put_object
            )
    else:  # local dev — served by your existing static mount
        path = f"./{key}"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(content)


async def get_presigned_url(key: str, expires: int = 900) -> str:
    """Temporary signed URL (15 min). Bucket stays private."""
    if settings.STORAGE_BACKEND == "s3":
        async with _client() as s3:
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
        async with _client() as s3:
            await s3.delete_object(Bucket=settings.S3_BUCKET, Key=key)
    else:
        path = f"./{key}"
        if os.path.exists(path):
            os.remove(path)

# # test_spaces.py — run directly: python test_spaces.py
# import boto3
# from botocore.config import Config

# session = boto3.session.Session()

# client = boto3.client(
#     "s3",
#     region_name="sfo3",
#     endpoint_url="https://sfo3.digitaloceanspaces.com",  # NOT https://vyuflo.storage.sfo3.digitaloceanspaces.com
#     aws_access_key_id="DO801HKEWPLTHFH7UPQX",
#     aws_secret_access_key="pYamJAfogS8lkJ9onbo5zMK27WlJQwxVkIYRNNd3kyI",
#     config=boto3.session.Config(s3={"addressing_style": "path"})  # force path-style
# )

# # 1. Can we even list buckets with this key?
# print(client.list_objects_v2(Bucket="vyuflo.storage", MaxKeys=1))

# # 2. Can we put an object?
# client.put_object(Bucket="vyuflo.storage", Key="test/hello.txt", Body=b"hello")
# print("upload OK")