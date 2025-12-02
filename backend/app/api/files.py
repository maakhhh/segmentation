from zipfile import ZipFile

from fastapi import APIRouter, UploadFile, File, HTTPException, Request, Form
from typing import List, Dict
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


@router.post("/upload_series_zip")
async def upload_series_zip(
    request: Request,
    series_name: str = Form(...),
    zip_file: UploadFile = File(...)
):
    """
    Загрузка серии DICOM в виде ZIP архива.
    """
    user_id = get_user_id(request)
    if not zip_file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Разрешены только ZIP архивы")

    content = await zip_file.read()
    uploaded_files = []

    with ZipFile(BytesIO(content)) as zip_obj:
        for file_info in zip_obj.infolist():
            filename = file_info.filename
            ext = os.path.splitext(filename)[1].lower()
            if ext != ".dcm":
                continue  # игнорируем не-DICOM

            file_bytes = zip_obj.read(file_info)
            key = storage.upload_file(user_id, f"{series_name}/{os.path.basename(filename)}", file_bytes)
            uploaded_files.append(key)

    if not uploaded_files:
        raise HTTPException(status_code=400, detail="Архив не содержит DICOM файлов")

    return {"message": "Серия успешно загружена", "files": uploaded_files}


@router.get("/series-list")
async def list_series(request: Request):
    """
    Получение списка серий пользователя.
    Формат хранения: user_id/series_name/file.dcm
    """
    user_id = get_user_id(request)
    try:
        prefix = f"{user_id }/"
        objects = storage.client.list_objects(
            storage.bucket,
            prefix=prefix,
            recursive=True
        )

        series: Dict[str, List[str]] = {}

        for obj in objects:
            # Пример пути:
            # user123/abdomen_ct_01/IMG0001.dcm

            full_path = obj.object_name.replace(prefix, "")  # abdomen_ct_01/IMG0001.dcm

            if "/" not in full_path:
                # файл уровня user_id — пропускаем
                continue

            series_name, filename = full_path.split("/", 1)

            if series_name not in series:
                series[series_name] = []

            series[series_name].append(filename)

        # Преобразуем в массив объектов
        result = [
            {
                "series_name": s,
                "files": sorted(series[s])
            }
            for s in sorted(series)
        ]

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении списка серий: {e}")