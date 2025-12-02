import pydicom
import numpy as np
from typing import Dict, Any, List
import logging
from PIL import Image
import io
import base64

logger = logging.getLogger(__name__)


class DICOMProcessor:
    """Класс для обработки DICOM файлов"""

    @staticmethod
    def read_dicom_bytes(file_bytes: io.BytesIO) -> Dict[str, Any]:
        """
        Чтение одного DICOM файла из BytesIO
        """
        try:
            dicom = pydicom.dcmread(file_bytes)

            # Базовые метаданные
            metadata = {
                "modality": str(getattr(dicom, 'Modality', 'Unknown')),
                "study_description": str(getattr(dicom, 'StudyDescription', '')),
                "series_description": str(getattr(dicom, 'SeriesDescription', '')),
                "rows": int(getattr(dicom, 'Rows', 0)),
                "columns": int(getattr(dicom, 'Columns', 0)),
                "slice_thickness": float(getattr(dicom, 'SliceThickness', 1.0)),
            }

            # Pixel data
            pixel_array = dicom.pixel_array

            normalized_image = DICOMProcessor.normalize_dicom_image(pixel_array)
            preview_base64 = DICOMProcessor.image_to_base64(normalized_image)

            return {
                "success": True,
                "metadata": metadata,
                "image_info": {
                    "shape": [int(dim) for dim in pixel_array.shape],
                    "data_type": str(pixel_array.dtype),
                    "min_value": float(np.min(pixel_array)),
                    "max_value": float(np.max(pixel_array)),
                    "mean_value": float(np.mean(pixel_array)),
                },
                "preview_base64": preview_base64,
                "pixel_array": pixel_array  # для превью и сегментации
            }

        except Exception as e:
            logger.error(f"Ошибка чтения DICOM: {str(e)}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def normalize_dicom_image(pixel_array: np.ndarray) -> np.ndarray:
        """Нормализация DICOM изображения для визуализации"""
        image = pixel_array.astype(np.float32)
        min_val = np.min(image)
        max_val = np.max(image)
        if max_val > min_val:
            image = (image - min_val) / (max_val - min_val) * 255.0
        else:
            image = np.zeros_like(image)
        return image.astype(np.uint8)

    @staticmethod
    def image_to_base64(image_array: np.ndarray) -> str:
        """Конвертация numpy array в base64 строку"""
        try:
            image = Image.fromarray(image_array)
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
        except Exception as e:
            logger.error(f"Ошибка конвертации в base64: {str(e)}")
            return ""

    @staticmethod
    def convert_to_png(image_array: np.ndarray) -> bytes:
        """Конвертация numpy array в PNG bytes"""
        image = Image.fromarray(image_array)
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        return buffer.getvalue()

    @staticmethod
    def read_dicom_series_bytes(files_bytes: List[bytes]) -> Dict:
        """
        Чтение серии DICOM файлов из байтов.
        Возвращает отсортированный 3D-объем и метаданные.
        """

        slices = []
        series_metadata = {}

        # Читаем каждый DICOM из байтов
        for i, file_bytes in enumerate(files_bytes):
            try:
                dicom_obj = pydicom.dcmread(io.BytesIO(file_bytes), force=True)

                # Проверяем, что это действительно DICOM
                if not hasattr(dicom_obj, 'pixel_array'):
                    continue

                # Получаем пиксельные данные
                pixel_array = dicom_obj.pixel_array.astype(np.float32)

                # Применяем Rescale Slope/Intercept если есть
                if hasattr(dicom_obj, 'RescaleSlope') and hasattr(dicom_obj, 'RescaleIntercept'):
                    pixel_array = pixel_array * float(dicom_obj.RescaleSlope) + float(dicom_obj.RescaleIntercept)
                    print(f"  Применен Rescale: Slope={dicom_obj.RescaleSlope}, Intercept={dicom_obj.RescaleIntercept}")

                # Применяем оконное преобразование если есть
                window_center = getattr(dicom_obj, 'WindowCenter', None)
                window_width = getattr(dicom_obj, 'WindowWidth', None)

                if window_center is not None and window_width is not None:
                    # Конвертируем в список если нужно
                    if hasattr(window_center, '__len__'):
                        window_center = float(window_center[0])
                    else:
                        window_center = float(window_center)

                    if hasattr(window_width, '__len__'):
                        window_width = float(window_width[0])
                    else:
                        window_width = float(window_width)

                    # Применяем оконное преобразование
                    window_min = window_center - window_width / 2
                    window_max = window_center + window_width / 2

                    pixel_array = np.clip(pixel_array, window_min, window_max)
                    pixel_array = (pixel_array - window_min) / (window_max - window_min)
                    pixel_array = np.clip(pixel_array, 0, 1) * 255
                    pixel_array = pixel_array.astype(np.uint8)

                    print(f"  Применено окно: Center={window_center}, Width={window_width}")
                else:
                    # Иначе нормализуем к 0-255
                    pixel_min = pixel_array.min()
                    pixel_max = pixel_array.max()

                    if pixel_max - pixel_min > 0:
                        pixel_array = (pixel_array - pixel_min) / (pixel_max - pixel_min) * 255
                    else:
                        pixel_array = pixel_array * 255

                    pixel_array = pixel_array.astype(np.uint8)
                    print(f"  Нормализовано: [{pixel_min}, {pixel_max}] -> [0, 255]")

                # Метаданные первого файла
                if i == 0:
                    series_metadata = {
                        "slice_thickness": float(getattr(dicom_obj, "SliceThickness", 1.0)),
                        "pixel_spacing": [float(x) for x in getattr(dicom_obj, "PixelSpacing", [1.0, 1.0])],
                        "series_description": getattr(dicom_obj, "SeriesDescription", ""),
                        "rows": int(dicom_obj.Rows),
                        "columns": int(dicom_obj.Columns),
                        "modality": getattr(dicom_obj, "Modality", ""),
                        "window_center": float(window_center) if window_center else None,
                        "window_width": float(window_width) if window_width else None,
                        "rescale_slope": float(getattr(dicom_obj, 'RescaleSlope', 1.0)),
                        "rescale_intercept": float(getattr(dicom_obj, 'RescaleIntercept', 0.0)),
                    }

                # Определяем позицию среза
                slice_position = None
                if hasattr(dicom_obj, 'ImagePositionPatient'):
                    slice_position = float(dicom_obj.ImagePositionPatient[2])
                elif hasattr(dicom_obj, 'SliceLocation'):
                    slice_position = float(dicom_obj.SliceLocation)
                else:
                    slice_position = float(getattr(dicom_obj, 'InstanceNumber', i))

                slices.append((pixel_array, slice_position, i))

            except Exception as e:
                print(f"Ошибка чтения DICOM файла {i}: {e}")
                continue

        if not slices:
            return {"success": False, "error": "Нет DICOM файлов с изображениями"}

        # Сортировка по позиции среза
        try:
            slices_sorted = sorted(slices, key=lambda x: x[1])
            volume = np.stack([s[0] for s in slices_sorted], axis=0)

            print(f"✅ Создан объем: {volume.shape}, dtype: {volume.dtype}, диапазон: [{volume.min()}, {volume.max()}]")

        except Exception as e:
            return {"success": False, "error": f"Ошибка при создании объема: {str(e)}"}

        return {
            "success": True,
            "volume": volume,
            "series_info": series_metadata,
            "volume_shape": volume.shape,
            "num_slices": len(slices),
        }


