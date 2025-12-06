from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from backend.app.core.state import app_state
from backend.app.core.config import settings
from backend.app.api.files import router as files_router
from backend.app.api.dicom import router as dicom_router
from backend.app.api.segmentation import router as segmentation_router
from backend.app.api.reconstruction import router as reconstruction_router
from backend.app.api.zip_upload import router as zip_router  # Добавляем

app = FastAPI(
    title=settings.app_name,
    description="Сервис для сегментации печени на КТ-снимках с 3D реконструкцией",
    version=settings.version
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(files_router)
app.include_router(dicom_router)
app.include_router(segmentation_router)
app.include_router(reconstruction_router)
app.include_router(zip_router)  # Регистрируем ZIP роутер


@app.on_event("startup")
async def startup_event():
    """Инициализация модели при запуске сервера"""
    try:
        model_path = os.path.join(os.path.dirname(__file__), "..", "..", "model", "unet.keras")
        model_path = os.path.abspath(model_path)

        success = app_state.initialize_model(model_path)
        if not success:
            print("Модель не загружена, но сервер продолжает работу")

    except Exception as e:
        print(f"Критическая ошибка при запуске: {e}")
        import traceback
        traceback.print_exc()


@app.on_event("shutdown")
async def shutdown_event():
    """Очистка ресурсов при завершении работы"""
    try:
        from backend.app.services.reconstruction_service import reconstruction_service
        reconstruction_service.cleanup_temp_files()
    except:
        pass


@app.get("/")
async def root():
    return {
        "message": "Добро пожаловать в сервис сегментации печени!",
        "status": "Сервер работает",
        "version": settings.version,
        "model_available": app_state.is_model_available(),
        "endpoints": {
            "2d_segmentation": "/segmentation/slice/{filename}",
            "3d_reconstruction": "/reconstruction/3d/{filename}",
            "3d_export": "/reconstruction/export/{filename}",
            "3d_metrics": "/reconstruction/metrics/{filename}",
            "zip_upload": "/zip/upload-series"  # Добавляем
        }
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "liver_segmentation",
        "model_available": app_state.is_model_available()
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload
    )