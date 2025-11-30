from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class HealthResponse(BaseModel):
    status: str
    service: str
    model_available: bool


class FileUploadResponse(BaseModel):
    message: str
    filename: str
    file_size: int
    file_type: str
    saved_path: str


class SegmentationResponse(BaseModel):
    filename: str
    segmentation: Dict[str, Any]
    dicom_info: Dict[str, Any]


class FileInfo(BaseModel):
    name: str
    size: int
    upload_time: float