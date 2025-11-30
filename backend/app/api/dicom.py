from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from io import BytesIO
from backend.app.services.storage_service import StorageService
from backend.app.services.dicom_processor import DICOMProcessor

router = APIRouter(prefix="/dicom", tags=["dicom"])

storage = StorageService()


def get_user_id(request: Request) -> str:
    """Временный идентификатор пользователя через заголовок"""
    return request.headers.get("X-User", "default-user")


@router.get("/info/{filename}")
async def get_dicom_info(request: Request, filename: str):
    """Информация о DICOM файле"""
    user_id = get_user_id(request)

    try:
        # Получаем файл из S3 в память
        file_data = storage.download_file_bytes(user_id, filename)
        if not file_data:
            raise HTTPException(status_code=404, detail="Файл не найден")

        if not filename.lower().endswith(".dcm"):
            raise HTTPException(status_code=400, detail="Файл не является DICOM")

        result = DICOMProcessor.read_dicom_bytes(BytesIO(file_data))
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])

        return {
            "filename": filename,
            "info": result["metadata"],
            "image_info": result["image_info"],
            "has_preview": bool(result.get("preview_base64"))
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки DICOM файла: {str(e)}")


@router.get("/preview/{filename}")
async def get_dicom_preview(request: Request, filename: str):
    """Превью DICOM файла как PNG"""
    user_id = get_user_id(request)

    try:
        file_data = storage.download_file_bytes(user_id, filename)
        if not file_data:
            raise HTTPException(status_code=404, detail="Файл не найден")

        if not filename.lower().endswith(".dcm"):
            raise HTTPException(status_code=400, detail="Файл не является DICOM")

        dicom_obj = DICOMProcessor.read_dicom_bytes(BytesIO(file_data))
        pixel_array = dicom_obj["pixel_array"]

        normalized_image = DICOMProcessor.normalize_dicom_image(pixel_array)
        png_data = DICOMProcessor.convert_to_png(normalized_image)

        return Response(content=png_data, media_type="image/png")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка создания превью: {str(e)}")
