"""
Менеджер состояния приложения (синглтон)
"""
from model.model_utils import LiverSegmentationModel
from backend.app.services.segmentation_service import SegmentationService

class AppState:
    """Класс для управления состоянием приложения (синглтон)"""


    def initialize_model(self, model_path: str):
        """Инициализация модели"""
        try:
            print(f"🔍 Ищу модель по пути: {model_path}")

            self.model = LiverSegmentationModel(model_path)
            self.segmentation_service = SegmentationService(self.model)
            self.model_available = True

            print("✅ Модель и сервис сегментации успешно инициализированы")
            return True

        except Exception as e:
            print(f"❌ Ошибка инициализации модели: {e}")
            import traceback
            traceback.print_exc()
            self.model_available = False
            return False

    def get_segmentation_service(self):
        """Получить сервис сегментации"""
        return self.segmentation_service

    def is_model_available(self):
        """Проверить доступность модели"""
        return self.model_available and self.segmentation_service is not None



app_state = AppState()