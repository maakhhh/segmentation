from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from typing import List
from backend.app.models.schemas import FileUploadResponse, FileInfo
from backend.app.services.storage_service import StorageService
from backend.app.services.dicom_processor import DICOMProcessor
from io import BytesIO
import os

router = APIRouter(prefix="/files", tags=["files"])

ALLOWED_EXTENSIONS = {'.dcm', '.png', '.jpg', '.jpeg'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

storage = StorageService()


def get_user_id(request: Request) -> str:
    """
    Временный идентификатор пользователя через заголовок.
    Можно заменить на токены или uuid.
    """
    return request.headers.get("X-User", "default-user")


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(request: Request, file: UploadFile = File(...)):
    """
    Загрузка файла пользователем в S3-совместимое хранилище.
    Поддержка DICOM и одиночных изображений.
    """
    user_id = get_user_id(request)
    file_extension = os.path.splitext(file.filename)[1].lower()

    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Неподдерживаемый формат файла. Разрешенные: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Проверка размера файла
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Файл слишком большой. Максимальный размер: {MAX_FILE_SIZE / (1024*1024)} MB"
        )

    try:
        # Загружаем файл в S3 / MinIO
        key = storage.upload_file(user_id, file.filename, content)

        return FileUploadResponse(
            message="Файл успешно загружен",
            filename=file.filename,
            file_size=len(content),
            file_type=file_extension,
            saved_path=key
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при загрузке файла: {str(e)}")


@router.get("/list", response_model=List[FileInfo])
async def list_uploaded_files(request: Request):
    """
    Список файлов пользователя.
    """
    user_id = get_user_id(request)
    try:
        files = []
        object_list = storage.list_files(user_id)
        for key in object_list:
            # Получаем метаданные файла
            obj = storage.client.stat_object(storage.bucket, f"{user_id}/{key}")
            files.append(FileInfo(
                name=key,
                size=obj.size,
                upload_time=obj.last_modified.timestamp()
            ))
        return files
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении списка файлов: {str(e)}")