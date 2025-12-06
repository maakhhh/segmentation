import React, { useState } from 'react';
import { apiService } from '../services/api';

interface ZipUploadProps {
  onUploadSuccess?: (result: any) => void;
  onUploadError?: (error: string) => void;
}

const ZipUpload: React.FC<ZipUploadProps> = ({ onUploadSuccess, onUploadError }) => {
  const [uploading, setUploading] = useState<boolean>(false);
  const [progress, setProgress] = useState<number>(0);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (file.name.toLowerCase().endsWith('.zip')) {
        setSelectedFile(file);
      } else {
        alert('Пожалуйста, выберите ZIP архив с DICOM файлами');
      }
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setUploading(true);
    setProgress(0);

    try {
      // Создаем FormData
      const formData = new FormData();
      formData.append('file', selectedFile);

      // Симуляция прогресса (в реальном приложении используйте axios с onUploadProgress)
      const progressInterval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 500);

      // Отправляем запрос
      const response = await fetch('http://localhost:8000/zip/upload-series', {
        method: 'POST',
        headers: {
          'X-User': localStorage.getItem('userId') || 'default-user',
        },
        body: formData,
      });

      clearInterval(progressInterval);

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const result = await response.json();
      setProgress(100);

      if (onUploadSuccess) {
        onUploadSuccess(result);
      }

      setTimeout(() => {
        setUploading(false);
        setProgress(0);
        setSelectedFile(null);
        // Очищаем input
        const fileInput = document.getElementById('zip-file-input') as HTMLInputElement;
        if (fileInput) fileInput.value = '';
      }, 1000);

    } catch (error) {
      console.error('Ошибка загрузки ZIP:', error);
      if (onUploadError) {
        onUploadError(error instanceof Error ? error.message : 'Неизвестная ошибка');
      }
      setUploading(false);
      setProgress(0);
    }
  };

  return (
    <div className="zip-upload" style={{
      border: '2px dashed #007acc',
      borderRadius: '10px',
      padding: '20px',
      textAlign: 'center',
      backgroundColor: '#f9f9f9',
      marginBottom: '20px'
    }}>
      <h3 style={{ marginTop: 0, color: '#007acc' }}>📦 Загрузите серию DICOM в ZIP</h3>

      <p style={{ color: '#666', marginBottom: '20px' }}>
        Загрузите ZIP архив, содержащий серию DICOM файлов КТ-исследования.
        Система построит 3D модель печени на основе всех срезов.
      </p>

      <div style={{ marginBottom: '20px' }}>
        <input
          id="zip-file-input"
          type="file"
          accept=".zip"
          onChange={handleFileSelect}
          disabled={uploading}
          style={{
            padding: '10px',
            border: '1px solid #ddd',
            borderRadius: '5px',
            width: '100%',
            maxWidth: '400px'
          }}
        />
      </div>

      {selectedFile && (
        <div style={{
          background: '#e3f2fd',
          padding: '10px',
          borderRadius: '5px',
          marginBottom: '15px'
        }}>
          <strong>Выбран файл:</strong> {selectedFile.name}
          <br />
          <small>Размер: {(selectedFile.size / 1024 / 1024).toFixed(2)} MB</small>
        </div>
      )}

      <button
        onClick={handleUpload}
        disabled={!selectedFile || uploading}
        style={{
          padding: '12px 30px',
          background: !selectedFile || uploading ? '#ccc' : '#007acc',
          color: 'white',
          border: 'none',
          borderRadius: '5px',
          cursor: !selectedFile || uploading ? 'not-allowed' : 'pointer',
          fontSize: '16px'
        }}
      >
        {uploading ? 'Загрузка...' : '🚀 Загрузить и построить 3D модель'}
      </button>

      {uploading && (
        <div style={{ marginTop: '20px' }}>
          <div style={{
            width: '100%',
            background: '#eee',
            borderRadius: '10px',
            overflow: 'hidden',
            height: '20px'
          }}>
            <div
              style={{
                width: `${progress}%`,
                background: progress === 100 ? '#4CAF50' : '#007acc',
                height: '100%',
                transition: 'width 0.3s',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'white',
                fontSize: '12px'
              }}
            >
              {progress}%
            </div>
          </div>
          <p style={{ marginTop: '10px', fontSize: '14px', color: '#666' }}>
            Обработка ZIP архива, сегментация и 3D реконструкция...
          </p>
        </div>
      )}

      <div style={{ marginTop: '20px', fontSize: '14px', color: '#666', textAlign: 'left' }}>
        <p><strong>Требования к ZIP архиву:</strong></p>
        <ul style={{ textAlign: 'left', paddingLeft: '20px' }}>
          <li>Только файлы с расширением .dcm</li>
          <li>Рекомендуется: 20-100 срезов</li>
          <li>Все срезы должны быть из одного исследования</li>
          <li>Максимальный размер архива: 500MB</li>
        </ul>
      </div>
    </div>
  );
};

export default ZipUpload;