import { FileInfo, DicomInfo, SegmentationResult, HealthStatus } from '../types/api';

const API_BASE = 'http://localhost:8000';

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
      body: formData,
    });
    
    return handleResponse(response);
  },

  listFiles: async (): Promise<FileInfo[]> => {
    const response = await fetch(`${API_BASE}/files/list`);
    return handleResponse(response);
  },

  // DICOM operations
  getDicomInfo: async (filename: string): Promise<DicomInfo> => {
    const response = await fetch(`${API_BASE}/dicom/info/${filename}`);
    return handleResponse(response);
  },

  getDicomPreview: async (filename: string): Promise<Blob> => {
    const response = await fetch(`${API_BASE}/dicom/preview/${filename}`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return response.blob();
  },

  // Segmentation
  segmentFile: async (filename: string): Promise<SegmentationResult> => {
    const response = await fetch(`${API_BASE}/segmentation/slice/${filename}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    return handleResponse(response);
  },
};