import numpy as np
from typing import Dict, Any, List
import logging
import cv2
from PIL import Image
import io
import base64

logger = logging.getLogger(__name__)


class SegmentationService:
    """Сервис для сегментации печени"""

    def __init__(self, model):
        self.model = model
        print("✅ SegmentationService создан")

    def segment_slice(self, image_slice: np.ndarray) -> Dict[str, Any]:
        """
        Сегментация одного среза
        """
        try:
            print(f"🎯 Сегментирую срез: {image_slice.shape}")
            mask = self.model.predict_slice(image_slice)
            print(f"✅ Получена маска: {mask.shape}")

            # Создаем визуализацию
            visualization = self._create_visualization(image_slice, mask)

            metrics = self._calculate_metrics(mask)
            return {
                "success": True,
                "mask_shape": [int(dim) for dim in mask.shape],
                "metrics": metrics,
                "mask_area_pixels": int(np.sum(mask)),
                "visualization": visualization  # Добавляем визуализацию
            }
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    #################
    def segment_volume(self, volume: np.ndarray) -> Dict[str, Any]:
        """
        Сегментация всего объема (всех срезов)
        """
        try:
            print(f"🎯 Сегментирую объем: {volume.shape}")
            masks = []

            # Сегментируем каждый срез
            for i in range(volume.shape[0]):
                slice_2d = volume[i]
                mask = self.model.predict_slice(slice_2d)
                masks.append(mask)

            masks_array = np.array(masks)

            return {
                "success": True,
                "masks_3d": masks_array,
                "shape": masks_array.shape,
                "total_slices": len(masks)
            }

        except Exception as e:
            logger.error(f"Ошибка сегментации объема: {e}")
            return {"success": False, "error": str(e)}
    ######################
    def _create_visualization(self, original_image: np.ndarray, mask: np.ndarray) -> str:
        """
        Создание визуализации с наложенной маской
        """
        try:
            # Нормализуем исходное изображение для визуализации
            if original_image.dtype != np.uint8:
                normalized_original = self._normalize_image(original_image)
            else:
                normalized_original = original_image

            # Создаем цветное изображение (RGB)
            if len(normalized_original.shape) == 2:
                colored_original = cv2.cvtColor(normalized_original, cv2.COLOR_GRAY2RGB)
            else:
                colored_original = normalized_original

            # Создаем цветную маску (красный цвет с прозрачностью)
            colored_mask = np.zeros_like(colored_original)
            colored_mask[mask == 1] = [255, 0, 0]  # Красный цвет для печени

            # Накладываем маску на оригинальное изображение
            alpha = 0.3  # Прозрачность маски
            visualization = cv2.addWeighted(colored_original, 1.0, colored_mask, alpha, 0)

            # Конвертируем в base64
            success, buffer = cv2.imencode('.png', visualization)
            if not success:
                raise Exception("Не удалось закодировать изображение")

            image_base64 = base64.b64encode(buffer).decode('utf-8')
            return image_base64

        except Exception as e:
            logger.error(f"Ошибка создания визуализации: {e}")
            return ""

    def _normalize_image(self, image: np.ndarray) -> np.ndarray:
        """
        Нормализация изображения к диапазону 0-255
        """
        image_normalized = cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX)
        return image_normalized.astype(np.uint8)

    def _calculate_metrics(self, mask: np.ndarray) -> Dict[str, float]:
        """Вычисление метрик для маски"""
        total_pixels = mask.size
        liver_pixels = np.sum(mask)

        return {
            "liver_area_ratio": float(liver_pixels / total_pixels) if total_pixels > 0 else 0.0,
            "liver_pixels": int(liver_pixels),
            "total_pixels": int(total_pixels)
        }

    def segment_volume(self, volume_3d: np.ndarray) -> Dict[str, Any]:
        """
        Сегментация 3D объема печени

        Args:
            volume_3d: 3D массив КТ-срезов (z, y, x)

        Returns:
            Словарь с 3D маской сегментации
        """
        try:
            logger.info(f"Начинаю 3D сегментацию: shape={volume_3d.shape}")

            num_slices = volume_3d.shape[0]
            masks = []

            for i in range(num_slices):
                slice_2d = volume_3d[i]

                # Сегментируем срез
                mask = self.model.predict_slice(slice_2d)
                masks.append(mask)

                # Логируем прогресс
                if i % 10 == 0 or i == num_slices - 1:
                    logger.info(f"Обработан срез {i + 1}/{num_slices}")

            # Собираем 3D маску
            masks_3d = np.array(masks, dtype=np.uint8)

            # Рассчитываем метрики
            total_pixels = masks_3d.size
            liver_pixels = np.sum(masks_3d > 0)
            liver_ratio = liver_pixels / total_pixels if total_pixels > 0 else 0

            logger.info(f"3D сегментация завершена: {masks_3d.shape}")
            logger.info(f"Пикселей печени: {liver_pixels} ({liver_ratio * 100:.1f}%)")

            return {
                'success': True,
                'masks_3d': masks_3d,
                'metrics': {
                    'total_slices': num_slices,
                    'liver_pixels_total': int(liver_pixels),
                    'liver_volume_ratio': float(liver_ratio),
                    'volume_shape': list(masks_3d.shape)
                }
            }

        except Exception as e:
            logger.error(f"Ошибка 3D сегментации: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def segment_slice_batch(self, slices: List[np.ndarray]) -> Dict[str, Any]:
        """
        Пакетная сегментация нескольких срезов
        """
        try:
            masks = []
            for i, slice_img in enumerate(slices):
                mask = self.model.predict_slice(slice_img)
                masks.append(mask)

            return {
                'success': True,
                'masks': masks,
                'num_slices': len(masks)
            }
        except Exception as e:
            logger.error(f"Ошибка пакетной сегментации: {str(e)}")
            return {'success': False, 'error': str(e)}