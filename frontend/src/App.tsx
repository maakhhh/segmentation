import React, { useState, useEffect } from 'react';
import FileUpload from './components/FileUpload';
import FileList from './components/FileList';
import DicomViewer from './components/DicomViewer';
import SegmentationResult from './components/SegmentationResult';
import { apiService } from './services/api';
import { HealthStatus } from './types/api';
import './App.css';

const App: React.FC = () => {
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [selectedFile, setSelectedFile] = useState<string>('');
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [segmentationData, setSegmentationData] = useState<any>(null);

  useEffect(() => {
    checkHealth();
  }, []);

  const checkHealth = async () => {
    try {
      const status = await apiService.getHealth();
      setHealthStatus(status);
    } catch (error) {
      console.error('Health check failed:', error);
    }
  };

  const handleUploadSuccess = () => {
    setRefreshTrigger(prev => prev + 1);
  };

  const handleFileSelect = (filename: string) => {
    setSelectedFile(filename);
    setSegmentationData(null);
  };

  const handleSegment = async () => {
    if (!selectedFile) return;
    
    try {
      const result = await apiService.segmentFile(selectedFile);
      setSegmentationData(result);
    } catch (error) {
      console.error('Segmentation failed:', error);
      alert('Ошибка сегментации: ' + error);
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>🍃 Сервис сегментации печени</h1>
        {healthStatus && (
          <div className="health-status">
            Статус: {healthStatus.status} | 
            Модель: {healthStatus.model_available ? '✅ Доступна' : '❌ Недоступна'}
          </div>
        )}
      </header>

      <div className="app-content">
        <div className="sidebar">
          <FileUpload onUploadSuccess={handleUploadSuccess} />
          <FileList 
            refreshTrigger={refreshTrigger} 
            onFileSelect={handleFileSelect} 
          />
        </div>

        <div className="main-content">
          {selectedFile && (
            <div className="file-actions">
              <h3>Выбран файл: {selectedFile}</h3>
              <button onClick={handleSegment} className="segment-button">
                🎯 Выполнить сегментацию
              </button>
            </div>
          )}

          {selectedFile && (
            <DicomViewer filename={selectedFile} />
          )}

          {segmentationData && (
            <SegmentationResult data={segmentationData} />
          )}
        </div>
      </div>
    </div>
  );
};

export default App;