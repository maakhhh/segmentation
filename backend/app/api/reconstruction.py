from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from typing import Dict, Any
import tempfile
import os
import json
from pathlib import Path
import numpy as np
import logging

from backend.app.services.reconstruction_service import reconstruction_service
from backend.app.services.segmentation_service import SegmentationService
from backend.app.services.dicom_processor import DICOMProcessor
from backend.app.core.state import app_state
from backend.app.services.storage_service import StorageService
from backend.app.models.schemas import SegmentationResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reconstruction", tags=["reconstruction"])
storage = StorageService()


def get_user_id(request: Request) -> str:
    """Временный идентификатор пользователя через заголовок"""
    return request.headers.get("X-User", "default-user")


@router.post("/3d/{filename}", response_model=Dict[str, Any])
async def create_3d_model(request: Request, filename: str):
    """
    Создание 3D модели из одного DICOM среза (создание тестового объема)
    """
    user_id = get_user_id(request)

    try:
        logger.info(f"Создание 3D модели из одного среза: {filename}")

        # 1. Проверяем модель
        if not app_state.is_model_available():
            raise HTTPException(status_code=500, detail="Модель не инициализирована")

        # 2. Получаем файл
        file_data = storage.download_file_bytes(user_id, filename)
        if not file_data:
            raise HTTPException(status_code=404, detail="Файл не найден")

        if not filename.lower().endswith(".dcm"):
            raise HTTPException(status_code=400, detail="Требуется DICOM файл")

        # 3. Читаем DICOM
        from io import BytesIO
        dicom_result = DICOMProcessor.read_dicom_bytes(BytesIO(file_data))
        if not dicom_result["success"]:
            raise HTTPException(status_code=400, detail=dicom_result["error"])

        # 4. Сегментируем срез
        segmentation_service = app_state.get_segmentation_service()
        segmentation_result = segmentation_service.segment_slice(dicom_result["pixel_array"])

        if not segmentation_result["success"]:
            raise HTTPException(status_code=400, detail=segmentation_result["error"])

        # 5. Получаем маску
        # Внимание: segment_slice возвращает словарь, маску нужно извлечь
        # Создаем тестовую маску на основе сегментации
        mask_shape = segmentation_result.get("mask_shape", [512, 512])
        liver_pixels = segmentation_result.get("metrics", {}).get("liver_pixels", 100000)
        liver_ratio = segmentation_result.get("metrics", {}).get("liver_area_ratio", 0.3)

        # Создаем простую эллиптическую маску для тестирования
        y, x = np.ogrid[:mask_shape[0], :mask_shape[1]]
        center_y, center_x = mask_shape[0] // 2, mask_shape[1] // 2

        # Размеры эллипса пропорциональны площади печени
        radius_ratio = np.sqrt(liver_ratio)
        radius_y = int(mask_shape[0] * radius_ratio * 0.5)
        radius_x = int(mask_shape[1] * radius_ratio * 0.5)

        mask = ((x - center_x) ** 2 / radius_x ** 2 + (y - center_y) ** 2 / radius_y ** 2) <= 1
        mask = mask.astype(np.uint8) * 255

        logger.info(f"Создана тестовая маска: shape={mask.shape}, площадь={liver_ratio * 100:.1f}%")

        # 6. Создаем тестовый 3D объем из маски
        # Для одного среза создаем простой объем: 20 срезов, уменьшаем интенсивность к краям
        num_slices = 20
        test_volume = reconstruction_service.create_test_volume_from_slice(mask, num_slices)

        # 7. 3D реконструкция
        slice_thickness = dicom_result.get("metadata", {}).get("slice_thickness", 3.0)
        spacing = (0.7, 0.7, slice_thickness)  # Стандартные значения для КТ

        recon_result = reconstruction_service.reconstruct_from_masks(test_volume, spacing)

        if not recon_result.get("success", False):
            error_msg = recon_result.get("error", "Неизвестная ошибка")
            logger.error(f"Ошибка 3D реконструкции: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)

        # 8. Читаем STL файл как base64 для фронтенда
        stl_path = recon_result.get("export_paths", {}).get("stl")
        stl_base64 = None
        if stl_path and os.path.exists(stl_path):
            with open(stl_path, "rb") as f:
                import base64
                stl_base64 = base64.b64encode(f.read()).decode('utf-8')

        # 9. Подготовка ответа
        response_data = {
            "filename": filename,
            "success": True,
            "reconstruction": {
                "mesh_info": recon_result.get("mesh_info", {}),
                "metrics": recon_result.get("metrics", {}),
                "stl_base64": stl_base64
            },
            "segmentation_info": {
                "mask_shape": segmentation_result.get("mask_shape"),
                "metrics": segmentation_result.get("metrics", {})
            },
            "note": "3D модель создана из одного среза с экстраполяцией"
        }

        logger.info(f"3D реконструкция из одного среза завершена для {filename}")
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Ошибка 3D реконструкции: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/export/{filename}")
async def export_3d_model(request: Request, filename: str, format: str = "stl"):
    """
    Экспорт 3D модели в STL или PLY
    """
    user_id = get_user_id(request)

    file_extension = f".{format.lower()}"
    valid_formats = ["stl", "ply"]

    if format not in valid_formats:
        raise HTTPException(status_code=400, detail=f"Неподдерживаемый формат. Допустимы: {', '.join(valid_formats)}")

    try:
        logger.info(f"Экспорт 3D модели {filename} в формате {format}")

        import pyvista as pv

        # Создаем простую тестовую модель печени (сфера)
        sphere = pv.Sphere(radius=50)

        # Сохраняем во временный файл
        with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as tmp:
            tmp_path = tmp.name
            sphere.save(tmp_path, binary=True)

        logger.info(f"Файл создан: {tmp_path}, размер: {os.path.getsize(tmp_path)} байт")

        return FileResponse(
            path=tmp_path,
            media_type="application/octet-stream",
            filename=f"liver_model_{filename}{file_extension}"
        )
    except Exception as e:
        logger.error(f"Ошибка экспорта: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка экспорта: {str(e)}")


@router.get("/metrics/{filename}")
async def get_3d_metrics(request: Request, filename: str):
    """
    Получение метрик 3D модели
    """
    user_id = get_user_id(request)

    try:
        logger.info(f"Запрос метрик для файла: {filename}")

        # Для демонстрации возвращаем тестовые данные
        return {
            "filename": filename,
            "metrics": {
                "volume_ml": 1450.5,
                "surface_area_cm2": 850.3,
                "center_of_mass": [125.4, 98.7, 67.2],
                "bounding_box": {
                    "x": [0, 250],
                    "y": [0, 200],
                    "z": [0, 150]
                }
            }
        }
    except Exception as e:
        logger.error(f"Ошибка получения метрик: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения метрик: {str(e)}")


@router.post("/batch")
async def batch_reconstruction(request: Request):
    """
    Пакетная обработка нескольких файлов
    """
    # TODO: Реализовать пакетную обработку
    return {"message": "Пакетная обработка в разработке"}


@router.get("/preview/{filename}")
async def get_3d_preview(request: Request, filename: str):
    """
    Получение превью 3D модели
    """
    # TODO: Реализовать создание и возврат превью изображения
    return {"message": "Превью 3D модели в разработке"}