import React, { useState, useEffect } from 'react';
import FileUpload from './components/FileUpload';
import ZipUpload from './components/ZipUpload';
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
  const [activeTab, setActiveTab] = useState<'single' | 'series'>('single');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  console.log('App render:', {
    activeTab,
    selectedFile,
    hasSegmentationData: !!segmentationData,
    segmentationDataType: segmentationData?.type || 'none'
  });

  useEffect(() => {
    checkHealth();
  }, []);

  const checkHealth = async () => {
    try {
      const status = await apiService.getHealth();
      setHealthStatus(status);
    } catch (error) {
      console.error('Health check failed:', error);
      setError('Ошибка подключения к серверу');
    }
  };

  const handleUploadSuccess = () => {
    setRefreshTrigger(prev => prev + 1);
  };

  const handleZipUploadSuccess = (result: any) => {
    console.log('ZIP upload success result:', result);

    // Формируем данные в формате, который ожидает SegmentationResult
    const formattedData = {
      filename: result.filename,
      segmentation: {
        success: true,
        mask_shape: result.segmentation?.masks_shape || [512, 512],
        metrics: result.segmentation?.metrics || {
          liver_area_ratio: 0.3,
          liver_pixels: 100000,
          total_pixels: 262144
        },
        mask_area_pixels: 100000,
        visualization: null // Нет 2D визуализации для ZIP
      },
      dicom_info: {
        modality: 'CT',
        study_description: result.series_info?.study_description || 'ZIP Archive',
        series_description: result.series_info?.series_description || 'DICOM Series',
        rows: 512,
        columns: 512,
        slice_thickness: result.series_info?.spacing?.[2] || 3.0
      },
      reconstruction: result.reconstruction,
      series_info: result.series_info,
      type: 'zip' // Добавляем тип для идентификации
    };

    console.log('Formatted data for SegmentationResult:', formattedData);
    setSegmentationData(formattedData);
    setSelectedFile(result.filename);
    setRefreshTrigger(prev => prev + 1);
  };

  const handleFileSelect = (filename: string) => {
    console.log('File selected:', filename);
    setSelectedFile(filename);
    setSegmentationData(null);
    setError(null);
  };

  const handleSegment = async () => {
    if (!selectedFile) return;

    setLoading(true);
    setError(null);

    try {
      const result = await apiService.segmentFile(selectedFile);
      console.log('Segmentation result:', result);

      // Добавляем тип для идентификации
      const resultWithType = { ...result, type: 'single' };
      setSegmentationData(resultWithType);
    } catch (error) {
      console.error('Segmentation failed:', error);
      const errorMsg = error instanceof Error ? error.message : 'Неизвестная ошибка';
      setError('Ошибка сегментации: ' + errorMsg);
      alert('Ошибка сегментации: ' + errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = (tab: 'single' | 'series') => {
    console.log('Changing tab to:', tab);
    setActiveTab(tab);
    setSelectedFile('');
    setSegmentationData(null);
    setError(null);
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>🍃 Сервис 3D сегментации печени</h1>
        {healthStatus && (
          <div className="health-status">
            Статус: {healthStatus.status} |
            Модель: {healthStatus.model_available ? '✅ Доступна' : '❌ Недоступна'}
          </div>
        )}
        {error && (
          <div className="error-message" style={{
            background: '#ffebee',
            color: '#c62828',
            padding: '10px',
            marginTop: '10px',
            borderRadius: '5px'
          }}>
            ⚠️ {error}
          </div>
        )}
      </header>

      <div className="app-content">
        <div className="sidebar">
          {/* Вкладки для выбора типа загрузки */}
          <div className="upload-tabs" style={{ marginBottom: '20px' }}>
            <button
              onClick={() => handleTabChange('single')}
              style={{
                padding: '10px 20px',
                background: activeTab === 'single' ? '#007acc' : '#eee',
                color: activeTab === 'single' ? 'white' : '#333',
                border: 'none',
                cursor: 'pointer',
                width: '50%',
                borderTopLeftRadius: '5px',
                borderBottomLeftRadius: '5px'
              }}
            >
              📄 Один DICOM
            </button>
            <button
              onClick={() => handleTabChange('series')}
              style={{
                padding: '10px 20px',
                background: activeTab === 'series' ? '#007acc' : '#eee',
                color: activeTab === 'series' ? 'white' : '#333',
                border: 'none',
                cursor: 'pointer',
                width: '50%',
                borderTopRightRadius: '5px',
                borderBottomRightRadius: '5px'
              }}
            >
              📦 Серия DICOM (ZIP)
            </button>
          </div>

          {activeTab === 'single' && (
            <>
              <FileUpload onUploadSuccess={handleUploadSuccess} />
              <FileList
                refreshTrigger={refreshTrigger}
                onFileSelect={handleFileSelect}
              />
            </>
          )}

          {activeTab === 'series' && (
            <ZipUpload
              onUploadSuccess={handleZipUploadSuccess}
              onUploadError={(errorMsg) => {
                console.error('ZIP upload error:', errorMsg);
                setError('Ошибка загрузки ZIP: ' + errorMsg);
              }}
            />
          )}
        </div>

        <div className="main-content">
          {loading && (
            <div className="loading-overlay" style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: 'rgba(255, 255, 255, 0.8)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 1000
            }}>
              <div style={{
                background: 'white',
                padding: '30px',
                borderRadius: '10px',
                boxShadow: '0 4px 20px rgba(0,0,0,0.2)',
                textAlign: 'center'
              }}>
                <div style={{ fontSize: '24px', marginBottom: '10px' }}>⏳</div>
                <div>Обработка данных...</div>
              </div>
            </div>
          )}

          {activeTab === 'single' && selectedFile && (
            <div className="file-actions">
              <h3>Выбран файл: {selectedFile}</h3>
              <div style={{ display: 'flex', gap: '10px' }}>
                <button
                  onClick={handleSegment}
                  className="segment-button"
                  disabled={loading}
                  style={{
                    padding: '10px 20px',
                    background: loading ? '#ccc' : '#4CAF50',
                    color: 'white',
                    border: 'none',
                    borderRadius: '5px',
                    cursor: loading ? 'not-allowed' : 'pointer'
                  }}
                >
                  {loading ? 'Обработка...' : '🎯 Выполнить 2D сегментацию'}
                </button>
                <button
                  onClick={checkHealth}
                  className="health-button"
                  style={{
                    padding: '10px 20px',
                    background: '#666',
                    color: 'white',
                    border: 'none',
                    borderRadius: '5px',
                    cursor: 'pointer'
                  }}
                >
                  🔄 Проверить статус
                </button>
              </div>
            </div>
          )}

          {activeTab === 'single' && selectedFile && !segmentationData && (
            <DicomViewer filename={selectedFile} />
          )}

          {segmentationData && (
            <SegmentationResult data={segmentationData} />
          )}

          {!segmentationData && activeTab === 'series' && (
            <div className="welcome-message" style={{
              textAlign: 'center',
              padding: '40px',
              background: '#f5f5f5',
              borderRadius: '10px',
              marginTop: '20px'
            }}>
              <h2>📦 Загрузите серию DICOM в ZIP архиве</h2>
              <p style={{ fontSize: '16px', color: '#666', marginBottom: '20px' }}>
                После загрузки система автоматически построит 3D модель печени
              </p>

              <div style={{
                display: 'inline-block',
                textAlign: 'left',
                background: 'white',
                padding: '20px',
                borderRadius: '8px',
                boxShadow: '0 2px 10px rgba(0,0,0,0.1)'
              }}>
                <p><strong>Процесс обработки:</strong></p>
                <ul style={{ paddingLeft: '20px' }}>
                  <li>📦 Распаковка ZIP архива</li>
                  <li>🖼️ Чтение всех DICOM срезов</li>
                  <li>🧠 Сегментация печени на каждом срезе</li>
                  <li>🎮 Построение точной 3D модели</li>
                  <li>📊 Расчет объема и площади поверхности</li>
                  <li>📥 Экспорт модели в STL/PLY форматах</li>
                </ul>

                <div style={{
                  marginTop: '20px',
                  padding: '15px',
                  background: '#e8f5e9',
                  borderRadius: '5px',
                  fontSize: '14px'
                }}>
                  <p><strong>Требования к ZIP архиву:</strong></p>
                  <ul style={{ paddingLeft: '20px', marginBottom: 0 }}>
                    <li>Только файлы с расширением .dcm</li>
                    <li>Рекомендуется: 20-100 срезов</li>
                    <li>Все срезы должны быть из одного исследования</li>
                    <li>Максимальный размер архива: 500MB</li>
                  </ul>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default App;