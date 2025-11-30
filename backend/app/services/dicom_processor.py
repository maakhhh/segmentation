import pydicom
import numpy as np
from typing import Dict, Any
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
