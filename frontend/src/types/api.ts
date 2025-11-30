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