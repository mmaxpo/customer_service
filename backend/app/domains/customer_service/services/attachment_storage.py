from __future__ import annotations

import asyncio
import os
from pathlib import Path

from fastapi import HTTPException

from app.core.config import settings


class AttachmentStorage:
    @property
    def backend(self) -> str:
        return settings.ATTACHMENT_STORAGE_BACKEND

    async def put(self, *, key: str, content: bytes, content_type: str) -> None:
        if self.backend == "s3":
            await asyncio.to_thread(
                self._s3().put_object,
                Bucket=self._bucket(),
                Key=key,
                Body=content,
                ContentType=content_type,
                ServerSideEncryption="AES256",
            )
            return
        path = self.local_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_bytes(content)
        os.chmod(temporary, 0o600)
        temporary.replace(path)

    async def signed_download_url(self, *, key: str, filename: str) -> str | None:
        if self.backend != "s3":
            return None
        return await asyncio.to_thread(
            self._s3().generate_presigned_url,
            "get_object",
            Params={
                "Bucket": self._bucket(),
                "Key": key,
                "ResponseContentDisposition": f'attachment; filename="{filename}"',
            },
            ExpiresIn=settings.ATTACHMENT_SIGNED_URL_SECONDS,
        )

    async def delete(self, *, key: str) -> None:
        if self.backend == "s3":
            await asyncio.to_thread(
                self._s3().delete_object, Bucket=self._bucket(), Key=key
            )
            return
        self.local_path(key).unlink(missing_ok=True)

    def local_path(self, key: str) -> Path:
        root = Path(settings.ATTACHMENT_STORAGE_ROOT).resolve()
        path = (root / key).resolve()
        if root not in path.parents:
            raise HTTPException(status_code=400, detail="Invalid attachment path")
        return path

    def _bucket(self) -> str:
        if not settings.S3_BUCKET:
            raise RuntimeError("S3_BUCKET is required for S3 attachment storage")
        return settings.S3_BUCKET

    @staticmethod
    def _s3():
        import boto3

        return boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            region_name=settings.S3_REGION,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        )
