from fastapi import APIRouter, UploadFile, File, HTTPException
import os
from typing import List
from backend.app.models.schemas import FileUploadResponse, FileInfo
from backend.app.services.dicom_processor import DICOMProcessor

router = APIRouter(prefix="/files", tags=["files"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED_EXTENSIONS = {'.dcm', '.png', '.jpg', '.jpeg'}


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """Загрузка файла для сегментации"""
    try:
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Неподдерживаемый формат файла. Разрешенные: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        # Проверка размера
        max_size = 50 * 1024 * 1024
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)

        if file_size > max_size:
            raise HTTPException(status_code=400, detail="Файл слишком большой. Максимальный размер: 50MB")

        file_path = os.path.join(UPLOAD_DIR, file.filename)

        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # DICOM обработка
        processing_result = {}
        if file_extension == '.dcm':
            processing_result = DICOMProcessor.read_dicom_file(file_path)

        return FileUploadResponse(
            message="Файл успешно загружен",
            filename=file.filename,
            file_size=file_size,
            file_type=file_extension,
            saved_path=file_path
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@router.get("/list", response_model=List[FileInfo])
async def list_uploaded_files():
    """Список загруженных файлов"""
    files = []
    if os.path.exists(UPLOAD_DIR):
        for filename in os.listdir(UPLOAD_DIR):
            file_path = os.path.join(UPLOAD_DIR, filename)
            if os.path.isfile(file_path):
                files.append(FileInfo(
                    name=filename,
                    size=os.path.getsize(file_path),
                    upload_time=os.path.getctime(file_path)
                ))
    return files