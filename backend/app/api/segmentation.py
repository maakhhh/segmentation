import numpy as np
from fastapi import APIRouter, HTTPException, Request, Form
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


@router.post("/series")
async def segment_series(request: Request, series_name: str = Form(...)):
    user_id = get_user_id(request)

    # Получаем список всех файлов серии из хранилища
    series_files = storage.list_files(user_id, prefix=f'{series_name}/')
    # Фильтруем только файлы нужной серии

    if not series_files:
        raise HTTPException(status_code=404, detail="Серия не найдена")

    print(f"📁 Найдено файлов в серии {series_name}: {len(series_files)}")

    # Загружаем байты всех DICOM
    files_bytes = []
    for filename in series_files:
        try:
            file_bytes = storage.download_file_bytes(user_id, f'{series_name}/{filename}')
            files_bytes.append(file_bytes)
            print(f"📥 Загружен: {filename}")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки {filename}: {e}")
            continue

    if not files_bytes:
        raise HTTPException(status_code=400, detail="Не удалось загрузить файлы серии")

    # Читаем и сортируем серию
    series_data = DICOMProcessor.read_dicom_series_bytes(files_bytes)
    if not series_data["success"]:
        raise HTTPException(status_code=400, detail="Ошибка чтения DICOM серии")

    print(f"📊 Серия прочитана: {len(files_bytes)} файлов, объем: {series_data['volume_shape']}")

    # Сегментация по каждому срезу
    segmentation_service = app_state.get_segmentation_service()
    results = []

    for i, slice_img in enumerate(series_data["volume"]):
        print(f"\n🔬 Сегментирую срез {i + 1}/{len(series_data['volume'])}...")

        # Сегментируем срез
        mask_result = segmentation_service.segment_slice(slice_img)

        # Проверяем результат
        if not mask_result.get("success", False):
            print(f"❌ Срез {i + 1}: ошибка сегментации")
            results.append({
                "success": False,
                "error": mask_result.get("error", "Неизвестная ошибка"),
                "mask_shape": [],
                "metrics": {"liver_area_ratio": 0, "liver_pixels": 0, "total_pixels": 0},
                "mask_area_pixels": 0,
                "visualization": None
            })
            continue

        print(f"✅ Срез {i + 1}: успешно, визуализация: {'есть' if mask_result.get('visualization') else 'нет'}")

        # Добавляем результат
        results.append({
            "success": True,
            "mask_shape": mask_result.get("mask_shape", []),
            "metrics": mask_result.get("metrics", {
                "liver_area_ratio": 0,
                "liver_pixels": 0,
                "total_pixels": slice_img.size
            }),
            "mask_area_pixels": mask_result.get("mask_area_pixels", 0),
            "visualization": mask_result.get("visualization")  # ← ВОТ ОНА!
        })

    successful_slices = sum(1 for r in results if r.get("success", False))
    slices_with_vis = sum(1 for r in results if r.get("visualization"))

    print(f"\n🎯 Итог: {successful_slices}/{len(results)} успешно, {slices_with_vis}/{len(results)} с визуализацией")

    return {
        "message": "Сегментация завершена",
        "volume_shape": series_data["volume_shape"],
        "segmentation": results,
        "total_slices": len(results),
        "successful_slices": successful_slices,
        "slices_with_visualization": slices_with_vis
    }
