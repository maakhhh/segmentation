from fastapi import APIRouter, HTTPException, Request
from io import BytesIO
from backend.app.models.schemas import SegmentationResponse
from backend.app.services.dicom_processor import DICOMProcessor
from backend.app.core.state import app_state
from backend.app.services.storage_service import StorageService

router = APIRouter(prefix="/segmentation", tags=["segmentation"])

storage = StorageService()


def get_user_id(request: Request) -> str:
    """Временный идентификатор пользователя через заголовок"""
    return request.headers.get("X-User", "default-user")


@router.post("/slice/{filename}", response_model=SegmentationResponse)
async def segment_file(request: Request, filename: str):
    """Сегментация загруженного DICOM файла"""
    user_id = get_user_id(request)

    try:
        # Проверяем доступность модели
        if not app_state.is_model_available():
            raise HTTPException(status_code=500, detail="Модель не инициализирована")

        # Получаем файл из S3
        file_data = storage.download_file_bytes(user_id, filename)
        if not file_data:
            raise HTTPException(status_code=404, detail="Файл не найден")

        if not filename.lower().endswith(".dcm"):
            raise HTTPException(status_code=400, detail="Сегментация доступна только для DICOM файлов")

        # Читаем DICOM из байтов
        dicom_result = DICOMProcessor.read_dicom_bytes(BytesIO(file_data))
        if not dicom_result["success"]:
            raise HTTPException(status_code=400, detail=dicom_result["error"])

        # Сервис сегментации
        segmentation_service = app_state.get_segmentation_service()

        # Сегментация
        pixel_array = dicom_result["pixel_array"]
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
