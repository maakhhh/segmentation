import pydicom
import numpy as np
from typing import Dict, Any
import logging
from PIL import Image
import io
import base64
from typing import List

logger = logging.getLogger(__name__)


class DICOMProcessor:
    """Класс для обработки DICOM файлов"""

    @staticmethod
    def sort_dicom_series(file_paths: List[str]) -> List[str]:
        """
        Сортировка DICOM файлов по позиции среза
        """
        try:
            slices_info = []

            for file_path in file_paths:
                dicom = pydicom.dcmread(file_path)
                # Пытаемся получить позицию среза разными способами
                slice_position = getattr(dicom, 'SliceLocation',
                                         getattr(dicom, 'ImagePositionPatient', [0, 0, 0])[2])
                slices_info.append((file_path, float(slice_position)))

            # Сортируем по позиции
            sorted_slices = sorted(slices_info, key=lambda x: x[1])
            return [path for path, _ in sorted_slices]

        except Exception as e:
            logger.error(f"Ошибка сортировки серии: {str(e)}")
            # Возвращаем в оригинальном порядке если не удалось отсортировать
            return file_paths

    @staticmethod
    def read_dicom_series(file_paths: List[str]) -> Dict[str, Any]:
        """
        Чтение серии DICOM файлов как объемного данных
        """
        try:
            slices = []
            series_metadata = {
                "number_of_slices": len(file_paths),
                "slice_thickness": None,
                "pixel_spacing": None,
                "series_description": ""
            }

            for i, file_path in enumerate(file_paths):
                dicom = pydicom.dcmread(file_path)
                pixel_array = dicom.pixel_array

                # Собираем метаданные из первого файла
                if i == 0:
                    series_metadata.update({
                        "slice_thickness": float(getattr(dicom, 'SliceThickness', 1.0)),
                        "pixel_spacing": [float(x) for x in getattr(dicom, 'PixelSpacing', [1.0, 1.0])],
                        "series_description": str(getattr(dicom, 'SeriesDescription', '')),
                        "rows": int(dicom.Rows),
                        "columns": int(dicom.Columns)
                    })

                slices.append(pixel_array)

            # Создаем 3D объем
            volume = np.stack(slices, axis=0)

            return {
                "success": True,
                "volume": volume,
                "series_info": series_metadata,
                "volume_shape": volume.shape
            }

        except Exception as e:
            logger.error(f"Ошибка чтения DICOM серии: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def read_dicom_file(file_path: str) -> Dict[str, Any]:
        """
        Чтение одного DICOM файла
        """
        try:
            dicom = pydicom.dcmread(file_path)

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

            # Нормализуем для превью
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
                "preview_base64": preview_base64
            }

        except Exception as e:
            logger.error(f"Ошибка чтения DICOM файла {file_path}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def normalize_dicom_image(pixel_array: np.ndarray) -> np.ndarray:
        """
        Нормализация DICOM изображения для визуализации
        """
        try:
            # Конвертируем в float
            image = pixel_array.astype(np.float32)

            # Нормализуем к диапазону 0-255
            image_min = np.min(image)
            image_max = np.max(image)

            if image_max > image_min:
                image = (image - image_min) / (image_max - image_min) * 255.0
            else:
                image = np.zeros_like(image)

            return image.astype(np.uint8)
        except Exception as e:
            logger.error(f"Ошибка нормализации изображения: {str(e)}")
            return np.zeros(pixel_array.shape, dtype=np.uint8)

    @staticmethod
    def image_to_base64(image_array: np.ndarray) -> str:
        """
        Конвертация numpy array в base64 строку
        """
        try:
            # Создаем изображение
            image = Image.fromarray(image_array)

            # Конвертируем в bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)

            # Конвертируем в base64
            base64_str = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
            return base64_str  # Возвращаем без data URL prefix

        except Exception as e:
            logger.error(f"Ошибка конвертации в base64: {str(e)}")
            return ""

    @staticmethod
    def convert_to_png(image_array: np.ndarray) -> bytes:
        """
        Конвертация numpy array в PNG bytes
        """
        try:
            # Создаем изображение
            image = Image.fromarray(image_array.astype(np.uint8))

            # Конвертируем в bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)

            return img_byte_arr.getvalue()

        except Exception as e:
            logger.error(f"Ошибка конвертации в PNG: {str(e)}")
            raise