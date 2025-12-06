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

    class ReconstructionMetrics(BaseModel):
        volume_ml: float
        volume_mm3: float
        surface_area_cm2: float
        surface_area_mm2: float
        center_of_mass: List[float]
        spacing_x: float
        spacing_y: float
        spacing_z: float
        bounding_box: Dict[str, List[float]]

    class MeshInfo(BaseModel):
        num_vertices: int
        num_faces: int
        bounds: List[float]

    class ReconstructionResponse(BaseModel):
        filename: str
        success: bool
        reconstruction: Dict[str, Any]
        segmentation_info: Optional[Dict[str, Any]] = None