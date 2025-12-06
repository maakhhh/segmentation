import {
  FileInfo,
  DicomInfo,
  SegmentationResult,
  HealthStatus,
  ReconstructionResult
} from '../types/api';
import { getUserId } from './user';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
const USER_ID = getUserId();

const handleResponse = async (response: Response) => {
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }
  return response.json();
};

export const apiService = {
  // Health check
  getHealth: async (): Promise<HealthStatus> => {
    const response = await fetch(`${API_BASE}/health`);
    return handleResponse(response);
  },

  // File operations
  uploadFile: async (file: File): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE}/files/upload`, {
      method: 'POST',
      headers: {
        "X-User": USER_ID
      },
      body: formData,
    });

    return handleResponse(response);
  },

  listFiles: async (): Promise<FileInfo[]> => {
    const response = await fetch(`${API_BASE}/files/list`, {
      headers: {
        "X-User": USER_ID
      },
    });
    return handleResponse(response);
  },

  // DICOM operations
  getDicomInfo: async (filename: string): Promise<DicomInfo> => {
    const response = await fetch(`${API_BASE}/dicom/info/${filename}`, {
      headers: {
        "X-User": USER_ID
      },
    });
    return handleResponse(response);
  },

  getDicomPreview: async (filename: string): Promise<Blob> => {
    const response = await fetch(`${API_BASE}/dicom/preview/${filename}`, {
      headers: {
        "X-User": USER_ID
      },
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return response.blob();
  },

  // 2D Segmentation
  segmentFile: async (filename: string): Promise<SegmentationResult> => {
    const response = await fetch(`${API_BASE}/segmentation/slice/${filename}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User': USER_ID
      },
    });
    return handleResponse(response);
  },

  // 3D Reconstruction operations
  reconstruct3D: async (filename: string): Promise<ReconstructionResult> => {
    const response = await fetch(`${API_BASE}/reconstruction/3d/${filename}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User': USER_ID
      },
    });
    return handleResponse(response);
  },

  export3DModel: async (filename: string, format: string = 'stl'): Promise<Blob> => {
    const response = await fetch(`${API_BASE}/reconstruction/export/${filename}?format=${format}`, {
      headers: {
        "X-User": USER_ID
      },
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return response.blob();
  },

  get3DMetrics: async (filename: string): Promise<any> => {
    const response = await fetch(`${API_BASE}/reconstruction/metrics/${filename}`, {
      headers: {
        "X-User": USER_ID
      },
    });
    return handleResponse(response);
  },

  // Utility function to download file
  downloadFile: (blob: Blob, filename: string) => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  },

  // ZIP upload
  uploadZipSeries: async (file: File): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE}/zip/upload-series`, {
      method: 'POST',
      headers: {
        'X-User': USER_ID
      },
      body: formData,
    });

    return handleResponse(response);
  },

  // Для прогресса загрузки
  uploadZipWithProgress: async (file: File, onProgress?: (progress: number) => void) => {
    // Реализация с использованием XMLHttpRequest или axios для отслеживания прогресса
  }
};
