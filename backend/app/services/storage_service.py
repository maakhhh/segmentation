from io import BytesIO

from minio import Minio
from minio.error import S3Error
import os
from datetime import timedelta, datetime


class StorageService:
    def __init__(self):
        self.client = Minio(
            os.getenv("MINIO_ENDPOINT"),
            access_key=os.getenv("MINIO_ACCESS_KEY"),
            secret_key=os.getenv("MINIO_SECRET_KEY"),
            secure=False,
        )
        self.bucket = os.getenv("MINIO_BUCKET")

        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    def upload_file(self, user_id: str, filename: str, data: bytes):
        key = f"{user_id}/{filename}"

        self.client.put_object(
            bucket_name=self.bucket,
            object_name=key,
            data=BytesIO(data),
            length=len(data),
        )
        return key

    def list_files(self, user_id: str, prefix=""):
        prefix = f"{user_id}/{prefix}"
        objects = self.client.list_objects(self.bucket, prefix=prefix)
        return [obj.object_name.replace(prefix, "") for obj in objects if not obj.is_dir]

    def get_file(self, user_id: str, filename: str):
        key = f"{user_id}/{filename}"
        return self.client.get_object(self.bucket, key)

    def download_file_bytes(self, user_id: str, filename: str) -> bytes:
        """
        Скачивает объект из MinIO и возвращает его содержимое как bytes.
        """
        key = f"{user_id}/{filename}"
        response = self.client.get_object(bucket_name=self.bucket, object_name=key)
        try:
            data = response.read()
        finally:
            response.close()
            response.release_conn()
        return data

    def delete_old_files(self, ttl_hours=24):
        """Удаляет файлы старше TTL"""
        now = datetime.utcnow()
        for obj in self.client.list_objects(self.bucket, recursive=True):
            if obj.last_modified < now - timedelta(hours=ttl_hours):
                self.client.remove_object(self.bucket, obj.object_name)
