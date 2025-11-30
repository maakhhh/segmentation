import tensorflow as tf
import numpy as np
import cv2
from typing import Tuple
import logging
import os

logger = logging.getLogger(__name__)


# Функции метрик
def dice_coef(y_true, y_pred, smooth=1e-6):
    y_true_f = tf.cast(tf.reshape(y_true, [-1]), tf.float32)
    y_pred_f = tf.cast(tf.reshape(y_pred, [-1]), tf.float32)
    y_pred_f = tf.clip_by_value(y_pred_f, 0.0, 1.0)

    intersection = tf.reduce_sum(y_true_f * y_pred_f)
    sums = tf.reduce_sum(y_true_f) + tf.reduce_sum(y_pred_f)
    dice = (2.0 * intersection + smooth) / (sums + smooth)
    return dice


def dice_loss(y_true, y_pred):
    return 1.0 - dice_coef(y_true, y_pred)


class LiverSegmentationModel:
    """Класс для работы с моделью сегментации печени"""

    def __init__(self, model_path: str):
        try:
            print(f"🔄 Загружаю модель из: {model_path}")

            self.model = tf.keras.models.load_model(
                model_path,
                custom_objects={
                    'dice_coef': dice_coef,
                    'dice_loss': dice_loss
                },
                compile=False
            )

            print(f"✅ Модель успешно загружена")
            print(f"   Входная форма: {self.model.input_shape}")
            print(f"   Выходная форма: {self.model.output_shape}")

        except Exception as e:
            print(f"❌ Ошибка загрузки модели: {e}")
            raise

    def preprocess_slice(self, image_slice: np.ndarray) -> np.ndarray:
        """
        Предобработка одного среза для модели
        """
        print(f"🔧 Предобработка среза: {image_slice.shape} -> 512x512")

        # Приводим к размеру 512x512 как при обучении
        if image_slice.shape != (512, 512):
            image_slice = cv2.resize(image_slice, (512, 512), interpolation=cv2.INTER_LINEAR)

        # Нормализация как при обучении (samplewise)
        image_slice = image_slice.astype(np.float32)
        mean = np.mean(image_slice)
        std = np.std(image_slice)

        if std > 0:
            image_slice = (image_slice - mean) / std
        else:
            image_slice = image_slice - mean

        # Добавляем размерности для батча и канала
        image_slice = np.expand_dims(image_slice, axis=0)  # batch dimension
        image_slice = np.expand_dims(image_slice, axis=-1)  # channel dimension

        return image_slice

    def postprocess_mask(self, prediction: np.ndarray, original_shape: Tuple) -> np.ndarray:
        """
        Постобработка маски предсказания
        """
        # Убираем размерности батча и канала
        mask = prediction[0, :, :, 0]

        # Приводим к оригинальному размеру
        if original_shape != (512, 512):
            mask = cv2.resize(mask, original_shape, interpolation=cv2.INTER_LINEAR)

        # Бинаризация
        binary_mask = (mask > 0.5).astype(np.uint8)

        return binary_mask

    def predict_slice(self, image_slice: np.ndarray) -> np.ndarray:
        """
        Предсказание для одного среза
        """
        original_shape = image_slice.shape
        print(f"🎯 Предсказание для среза: {original_shape}")

        # Предобработка
        processed_slice = self.preprocess_slice(image_slice)
        print(f"   После предобработки: {processed_slice.shape}")

        # Предсказание
        prediction = self.model.predict(processed_slice, verbose=0)
        print(f"   Получен prediction: {prediction.shape}")

        # Постобработка
        mask = self.postprocess_mask(prediction, original_shape)
        print(f"   Финальная маска: {mask.shape}")

        return mask
