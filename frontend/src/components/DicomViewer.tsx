import React, { useState, useEffect } from 'react';
import { apiService } from '../services/api';

interface DicomViewerProps {
  filename: string;
}

const DicomViewer: React.FC<DicomViewerProps> = ({ filename }) => {
  const [imageUrl, setImageUrl] = useState<string>('');
  const [dicomInfo, setDicomInfo] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (filename) {
      loadDicomData();
    }
  }, [filename]);

  const loadDicomData = async () => {
    setLoading(true);
    try {
      // Загружаем превью
      const blob = await apiService.getDicomPreview(filename);
      const url = URL.createObjectURL(blob);
      setImageUrl(url);

      // Загружаем информацию
      const info = await apiService.getDicomInfo(filename);
      setDicomInfo(info);
    } catch (error) {
      console.error('Error loading DICOM data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Загрузка DICOM...</div>;

  return (
    <div className="dicom-viewer">
      <h3>Просмотр DICOM: {filename}</h3>
      <div className="dicom-content">
        {imageUrl && (
          <div className="image-container">
            <img src={imageUrl} alt="DICOM preview" className="dicom-image" />
          </div>
        )}
        {dicomInfo && (
          <div className="dicom-info">
            <h4>Информация о файле:</h4>
            <div className="info-grid">
              <div>Модальность:</div>
              <div>{dicomInfo.info.modality}</div>
              
              <div>Размер:</div>
              <div>{dicomInfo.info.rows} × {dicomInfo.info.columns}</div>
              
              <div>Толщина среза:</div>
              <div>{dicomInfo.info.slice_thickness} мм</div>
              
              <div>Диапазон значений:</div>
              <div>{dicomInfo.image_info.min_value} - {dicomInfo.image_info.max_value}</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default DicomViewer;