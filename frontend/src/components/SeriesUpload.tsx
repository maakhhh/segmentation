import React, { useState, useRef, useEffect } from 'react';
import { apiService } from '../services/api';

interface Props {
  onSuccess: () => void;
}

const SeriesUpload: React.FC<Props> = ({ onSuccess }) => {
  const [seriesName, setSeriesName] = useState("");
  const [zipFile, setZipFile] = useState<File | null>(null);
  const [status, setStatus] = useState<{ type: 'info' | 'success' | 'error', message: string } | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (file: File | null) => {
    if (file && !file.name.toLowerCase().endsWith('.zip')) {
      setStatus({ type: 'error', message: '❌ Выберите ZIP файл' });
      return;
    }
    setZipFile(file);
    if (file) {
      const fileSizeMB = (file.size / (1024 * 1024)).toFixed(1);
      setStatus({ type: 'info', message: `📦 Выбран файл: ${file.name} (${fileSizeMB} MB)` });
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    handleFileSelect(file);
  };

  const uploadSeries = async () => {
    if (!zipFile || !seriesName.trim()) {
      setStatus({ type: 'error', message: '❌ Введите название серии и выберите ZIP файл' });
      return;
    }

    if (seriesName.includes('/') || seriesName.includes('\\')) {
      setStatus({ type: 'error', message: '❌ Название серии не должно содержать / или \\' });
      return;
    }

    setIsUploading(true);
    setStatus({ type: 'info', message: '⏳ Загрузка серии...' });

    try {
      await apiService.uploadSeries(seriesName, zipFile);
      setStatus({ type: 'success', message: `✅ Серия "${seriesName}" успешно загружена!` });
      setSeriesName("");
      setZipFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      onSuccess();
    } catch (err: any) {
      setStatus({ type: 'error', message: `❌ Ошибка загрузки: ${err.message || 'Неизвестная ошибка'}` });
    } finally {
      setIsUploading(false);
    }
  };

  const handleClickUpload = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  return (
    <div className="series-upload">
      <h3>Загрузка серии (ZIP)</h3>

      <div className="form-group">
        <label htmlFor="series-name">Название серии</label>
        <input 
          id="series-name"
          type="text"
          placeholder="Например: abdomen_ct_01"
          value={seriesName}
          onChange={(e) => setSeriesName(e.target.value)}
          disabled={isUploading}
        />
      </div>

      <div className="form-group">
        <label>ZIP архив с DICOM файлами</label>
        <div 
          className={`file-input-label ${isDragging ? 'dragover' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={handleClickUpload}
        >
          <div className="file-icon">📦</div>
          {zipFile ? (
            <>
              <div className="file-name" title={zipFile.name}>
                {zipFile.name}
              </div>
              <div className="file-size">
                {(zipFile.size / (1024 * 1024)).toFixed(1)} MB
              </div>
            </>
          ) : (
            <>
              <span>Нажмите для выбора файла</span>
            </>
          )}
        </div>
        <input 
          ref={fileInputRef}
          type="file"
          accept=".zip"
          onChange={(e) => handleFileSelect(e.target.files?.[0] || null)}
          disabled={isUploading}
        />
        <div className="drag-drop-info">Поддерживаются только ZIP архивы с DICOM файлами</div>
      </div>

      <button 
        onClick={uploadSeries} 
        disabled={isUploading || !zipFile || !seriesName.trim()}
      >
        {isUploading ? '⏳ Загрузка...' : 'Загрузить серию'}
      </button>

      {status && (
        <div className={`upload-message ${status.type}`}>
          {status.message}
        </div>
      )}

      {isUploading && (
        <div className="upload-progress">
          <div className="progress-bar" style={{ width: '70%' }} />
        </div>
      )}
    </div>
  );
};

export default SeriesUpload;