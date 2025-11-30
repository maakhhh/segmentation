from fastapi import APIRouter, HTTPException
import os
import pydicom

# Абсолютные импорты
from backend.app.models.schemas import SegmentationResponse
from backend.app.services.dicom_processor import DICOMProcessor
from backend.app.core.state import app_state

router = APIRouter(prefix="/segmentation", tags=["segmentation"])

UPLOAD_DIR = "uploads"


@router.post("/slice/{filename}", response_model=SegmentationResponse)
async def segment_file(filename: str):
    """Сегментация загруженного DICOM файла"""
    try:
        # Проверяем доступность модели через app_state
        if not app_state.is_model_available():
            raise HTTPException(status_code=500, detail="Модель не инициализирована")

        file_path = os.path.join(UPLOAD_DIR, filename)

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Файл не найден")

        if not filename.lower().endswith('.dcm'):
            raise HTTPException(status_code=400, detail="Сегментация доступна только для DICOM файлов")

        # Читаем DICOM файл
        dicom_result = DICOMProcessor.read_dicom_file(file_path)
        if not dicom_result["success"]:
            raise HTTPException(status_code=400, detail=dicom_result["error"])

        # Получаем сервис сегментации
        segmentation_service = app_state.get_segmentation_service()

        # Сегментируем
        pixel_array = pydicom.dcmread(file_path).pixel_array
        segmentation_result = segmentation_service.segment_slice(pixel_array)

        if not segmentation_result["success"]:
            raise HTTPException(status_code=400, detail=segmentation_result["error"])

        return SegmentationResponse(
            filename=filename,
            segmentation=segmentation_result,
            dicom_info=dicom_result["metadata"]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сегментации: {str(e)}")