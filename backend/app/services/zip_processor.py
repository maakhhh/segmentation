import zipfile
import tempfile
import os
import pydicom
import numpy as np
from typing import Dict, Any, List, Tuple
import logging
from pathlib import Path
import re

logger = logging.getLogger(__name__)


class ZIPProcessor:
    """Обработчик ZIP архивов с сериями DICOM"""

    @staticmethod
    def extract_zip(zip_bytes: bytes) -> Tuple[str, List[str]]:
        """
        Извлечение ZIP архива во временную директорию
        """
        try:
            # Создаем временную директорию
            temp_dir = tempfile.mkdtemp(prefix="dicom_series_")
            logger.info(f"Создана временная директория: {temp_dir}")

            # Сохраняем ZIP во временный файл
            zip_path = os.path.join(temp_dir, "archive.zip")
            with open(zip_path, "wb") as f:
                f.write(zip_bytes)

            # Извлекаем ZIP
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            # Удаляем ZIP файл
            os.remove(zip_path)

            # Находим все DICOM файлы
            dicom_files = []
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_lower = file.lower()
                    if file_lower.endswith('.dcm') or '.dcm' in file_lower or file_lower.endswith('.ima'):
                        full_path = os.path.join(root, file)
                        dicom_files.append(full_path)

            logger.info(f"Найдено DICOM файлов: {len(dicom_files)}")

            return temp_dir, dicom_files

        except Exception as e:
            logger.error(f"Ошибка извлечения ZIP: {str(e)}")
            raise

    @staticmethod
    def read_dicom_series(dicom_files: List[str]) -> Dict[str, Any]:
        """
        Чтение серии DICOM файлов и создание 3D объема
        """
        try:
            slices_data = []

            # Читаем каждый DICOM файл
            for file_path in dicom_files:
                try:
                    dicom = pydicom.dcmread(file_path, force=True)

                    # Пропускаем если нет пиксельных данных
                    if not hasattr(dicom, 'pixel_array'):
                        continue

                    # Получаем пиксельные данные
                    pixel_array = dicom.pixel_array

                    # Получаем позицию среза
                    slice_location = getattr(dicom, 'SliceLocation', 0)
                    instance_number = getattr(dicom, 'InstanceNumber', 0)

                    # Получаем orientation и position
                    image_orientation = getattr(dicom, 'ImageOrientationPatient', [1, 0, 0, 0, 1, 0])
                    image_position = getattr(dicom, 'ImagePositionPatient', [0, 0, 0])

                    slices_data.append({
                        'pixel_array': pixel_array,
                        'slice_location': float(slice_location),
                        'instance_number': int(instance_number),
                        'image_position': image_position,
                        'rows': dicom.Rows,
                        'columns': dicom.Columns,
                        'pixel_spacing': list(map(float, getattr(dicom, 'PixelSpacing', [1.0, 1.0]))),
                        'slice_thickness': float(getattr(dicom, 'SliceThickness', 3.0)),
                        'file_path': file_path
                    })

                except Exception as e:
                    logger.warning(f"Ошибка чтения DICOM файла {file_path}: {str(e)}")
                    continue

            if not slices_data:
                raise ValueError("Не найдено валидных DICOM файлов")

            # Сортируем по позиции среза
            slices_data.sort(key=lambda x: x['slice_location'])

            # Проверяем размеры
            first_slice = slices_data[0]
            target_shape = (first_slice['rows'], first_slice['columns'])

            # Создаем 3D объем
            num_slices = len(slices_data)
            volume = np.zeros((num_slices, target_shape[0], target_shape[1]), dtype=np.float32)

            for i, slice_data in enumerate(slices_data):
                # Нормализуем срез
                slice_array = slice_data['pixel_array'].astype(np.float32)

                # Масштабируем если нужно
                if slice_array.shape != target_shape:
                    from skimage.transform import resize
                    slice_array = resize(slice_array, target_shape, preserve_range=True)

                # Нормализуем к 0-1
                slice_min = np.min(slice_array)
                slice_max = np.max(slice_array)
                if slice_max > slice_min:
                    volume[i] = (slice_array - slice_min) / (slice_max - slice_min)
                else:
                    volume[i] = slice_array

            # Получаем spacing
            pixel_spacing = first_slice['pixel_spacing']
            slice_thickness = first_slice['slice_thickness']

            # Вычисляем spacing между срезами
            if len(slices_data) > 1:
                # Берем разницу в slice_location между соседними срезами
                slice_locations = [s['slice_location'] for s in slices_data]
                slice_spacings = np.abs(np.diff(slice_locations))
                avg_slice_spacing = np.mean(slice_spacings) if len(slice_spacings) > 0 else slice_thickness
            else:
                avg_slice_spacing = slice_thickness

            spacing = (float(pixel_spacing[0]), float(pixel_spacing[1]), float(avg_slice_spacing))

            logger.info(f"Создан 3D объем: {volume.shape}, spacing: {spacing}")
            logger.info(f"Диапазон интенсивностей: {volume.min():.3f} - {volume.max():.3f}")

            return {
                'success': True,
                'volume': volume,
                'spacing': spacing,
                'num_slices': num_slices,
                'volume_shape': volume.shape,
                'slice_info': [{
                    'slice_location': s['slice_location'],
                    'instance_number': s['instance_number']
                } for s in slices_data]
            }

        except Exception as e:
            logger.error(f"Ошибка чтения серии DICOM: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}