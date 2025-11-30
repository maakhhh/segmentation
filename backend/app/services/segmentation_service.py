import numpy as np
from typing import Dict, Any
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