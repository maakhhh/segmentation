from fastapi import APIRouter, UploadFile, File, HTTPException, Request, BackgroundTasks
from typing import Dict, Any, List
import os
import tempfile
import shutil
from backend.app.services.zip_processor import ZIPProcessor
from backend.app.services.segmentation_service import SegmentationService
from backend.app.services.reconstruction_service import reconstruction_service
from backend.app.services.simple_reconstruction import simple_reconstruction_service  # Импортируем упрощенный сервис
from backend.app.core.state import app_state
from backend.app.services.storage_service import StorageService
import numpy as np
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/zip", tags=["zip"])

storage = StorageService()


def get_user_id(request: Request) -> str:
    """Идентификатор пользователя"""
    return request.headers.get("X-User", "default-user")


@router.post("/upload-series", response_model=Dict[str, Any])
async def upload_zip_series(
        request: Request,
        file: UploadFile = File(...),
        background_tasks: BackgroundTasks = None
):
    """
    Загрузка ZIP архива с серией DICOM файлов для 3D реконструкции
    """
    user_id = get_user_id(request)
    temp_dir = None

    try:
        # Проверяем расширение
        if not file.filename.lower().endswith('.zip'):
            raise HTTPException(status_code=400, detail="Требуется ZIP архив")

        # Читаем файл
        content = await file.read()
        logger.info(f"Получен ZIP архив: {file.filename}, размер: {len(content)} байт")

        # Извлекаем ZIP
        temp_dir, dicom_files = ZIPProcessor.extract_zip(content)

        if not dicom_files:
            raise HTTPException(status_code=400, detail="В архиве не найдены DICOM файлов")

        # Читаем серию DICOM
        series_result = ZIPProcessor.read_dicom_series(dicom_files)

        if not series_result.get('success'):
            raise HTTPException(status_code=400, detail=series_result.get('error', 'Ошибка чтения серии'))

        volume = series_result['volume']
        spacing = series_result['spacing']

        logger.info(f"Прочитан объем: {volume.shape}, срезов: {len(dicom_files)}, spacing: {spacing}")

        # Сегментация 3D объема
        if not app_state.is_model_available():
            raise HTTPException(status_code=500, detail="Модель не инициализирована")

        segmentation_service = app_state.get_segmentation_service()
        segmentation_result = segmentation_service.segment_volume(volume)

        if not segmentation_result['success']:
            raise HTTPException(status_code=400, detail=segmentation_result.get('error', 'Ошибка сегментации'))

        masks_3d = segmentation_result['masks_3d']

        # 3D реконструкция из реальных масок
        recon_result = reconstruction_service.reconstruct_from_masks(masks_3d, spacing)

        if not recon_result.get('success'):
            error_msg = recon_result.get('error', 'Ошибка 3D реконструкции')
            logger.error(f"Ошибка реконструкции: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)

        # Читаем STL как base64
        stl_path = recon_result.get('export_paths', {}).get('stl')
        stl_base64 = None
        if stl_path and os.path.exists(stl_path):
            with open(stl_path, "rb") as f:
                import base64
                stl_base64 = base64.b64encode(f.read()).decode('utf-8')
            logger.info(f"STL файл прочитан, размер: {os.path.getsize(stl_path)} байт")
        else:
            logger.warning("STL файл не найден или не создан")

        # Формируем ответ
        response = {
            'filename': file.filename,
            'success': True,
            'series_info': {
                'num_slices': len(dicom_files),
                'volume_shape': volume.shape,
                'spacing': list(spacing),
                'num_dicom_files': len(dicom_files)
            },
            'segmentation': {
                'masks_shape': masks_3d.shape,
                'metrics': segmentation_result.get('metrics', {})
            },
            'reconstruction': {
                'mesh_info': recon_result.get('mesh_info', {}),
                'metrics': recon_result.get('metrics', {}),
                'stl_base64': stl_base64
            }
        }

        logger.info(f"3D реконструкция завершена успешно")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка обработки ZIP архива: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка обработки ZIP архива: {str(e)}")

    finally:
        # Очищаем временные файлы
        if temp_dir and os.path.exists(temp_dir):
            try:
                import shutil
                shutil.rmtree(temp_dir)
                logger.info(f"Очищена временная директория: {temp_dir}")
            except Exception as e:
                logger.warning(f"Не удалось очистить временную директорию: {str(e)}")


@router.post("/process-volume")
async def process_volume_data(request: Request, volume_data: Dict[str, Any]):
    """
    Прямая обработка 3D объема (для тестирования)
    """
    try:
        # Получаем данные объема из запроса
        volume_array = np.array(volume_data.get('volume', []))
        spacing = volume_data.get('spacing', [0.7, 0.7, 3.0])

        if volume_array.size == 0:
            raise HTTPException(status_code=400, detail="Не предоставлены данные объема")

        # Используем упрощенную реконструкцию
        recon_result = simple_reconstruction_service.reconstruct_from_volume_demo(
            volume_array.shape,
            tuple(spacing)
        )

        return recon_result

    except Exception as e:
        logger.error(f"Ошибка обработки объема: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка обработки объема: {str(e)}")