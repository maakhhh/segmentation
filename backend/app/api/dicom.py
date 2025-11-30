from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
import os
import pydicom
from backend.app.services.dicom_processor import DICOMProcessor

router = APIRouter(prefix="/dicom", tags=["dicom"])

UPLOAD_DIR = "uploads"


@router.get("/info/{filename}")
async def get_dicom_info(filename: str):
    """Информация о DICOM файле"""
    try:
        file_path = os.path.join(UPLOAD_DIR, filename)

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Файл не найден")

        if not filename.lower().endswith('.dcm'):
            raise HTTPException(status_code=400, detail="Файл не является DICOM")

        result = DICOMProcessor.read_dicom_file(file_path)

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])

        return {
            "filename": filename,
            "info": result["metadata"],
            "image_info": result["image_info"],
            "has_preview": bool(result.get("preview_base64"))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки DICOM файла: {str(e)}")


@router.get("/preview/{filename}")
async def get_dicom_preview(filename: str):
    """Превью DICOM файла как PNG"""
    try:
        file_path = os.path.join(UPLOAD_DIR, filename)

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Файл не найден")

        if not filename.lower().endswith('.dcm'):
            raise HTTPException(status_code=400, detail="Файл не является DICOM")

        result = DICOMProcessor.read_dicom_file(file_path)

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])

        pixel_array = pydicom.dcmread(file_path).pixel_array
        normalized_image = DICOMProcessor.normalize_dicom_image(pixel_array)
        png_data = DICOMProcessor.convert_to_png(normalized_image)

        return Response(content=png_data, media_type="image/png")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка создания превью: {str(e)}")