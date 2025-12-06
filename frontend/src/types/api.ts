export interface FileInfo {
  name: string;
  size: number;
  upload_time: number;
}

export interface DicomInfo {
  filename: string;
  info: {
    modality: string;
    study_description: string;
    series_description: string;
    rows: number;
    columns: number;
    slice_thickness: number;
  };
  image_info: {
    shape: number[];
    data_type: string;
    min_value: number;
    max_value: number;
    mean_value: number;
  };
}

export interface SegmentationResult {
  filename: string;
  segmentation: {
    success: boolean;
    mask_shape: number[];
    metrics: {
      liver_area_ratio: number;
      liver_pixels: number;
      total_pixels: number;
    };
    mask_area_pixels: number;
    visualization: string; // Добавляем визуализацию
  };
  dicom_info: DicomInfo['info'];
}

export interface HealthStatus {
  status: string;
  service: string;
  model_available: boolean;
}

// Добавляем типы для 3D реконструкции
export interface ReconstructionMetrics {
  volume_ml: number;
  volume_mm3: number;
  surface_area_cm2: number;
  surface_area_mm2: number;
  center_of_mass: number[];
  spacing_x: number;
  spacing_y: number;
  spacing_z: number;
  bounding_box: {
    x: number[];
    y: number[];
    z: number[];
  };
}

export interface MeshInfo {
  num_vertices: number;
  num_faces: number;
  bounds: number[];
}

export interface ReconstructionResult {
  filename: string;
  success: boolean;
  reconstruction: {
    mesh_info: MeshInfo;
    metrics: ReconstructionMetrics;
    stl_base64?: string;  // Base64 encoded STL file
  };
  segmentation_info?: {
    mask_shape: number[];
    metrics: any;
  };
}

export interface HealthStatus {
  status: string;
  service: string;
  model_available: boolean;
}

// Добавляем типы для ZIP загрузки
export interface ZipUploadResult {
  filename: string;
  success: boolean;
  series_info: {
    num_slices: number;
    volume_shape: number[];
    spacing: number[];
    num_dicom_files: number;
  };
  segmentation: {
    masks_shape: number[];
    metrics: any;
  };
  reconstruction: {
    mesh_info: MeshInfo;
    metrics: ReconstructionMetrics;
    stl_base64?: string;
  };
}