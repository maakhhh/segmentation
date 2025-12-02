import React, { useState } from 'react';
import { SegmentationResult as SegmentationResultType } from '../types/api';

interface SegmentationResultProps {
  data: SegmentationResultType;
}

const SegmentationResult: React.FC<SegmentationResultProps> = ({ data }) => {
  const { segmentation, dicom_info } = data;
  const [activeTab, setActiveTab] = useState<'metrics' | 'visualization'>('metrics');

  return (
    <div className="segmentation-result">
      
      {/* Табы для переключения между метриками и визуализацией */}
      <div className="tabs">
        <button 
          className={`tab-button ${activeTab === 'metrics' ? 'active' : ''}`}
          onClick={() => setActiveTab('metrics')}
        >
          📊 Метрики
        </button>
        <button 
          className={`tab-button ${activeTab === 'visualization' ? 'active' : ''}`}
          onClick={() => setActiveTab('visualization')}
        >
          🖼️ Визуализация
        </button>
      </div>

      {activeTab === 'metrics' && (
        <div className="result-grid">
          <div className="result-card">
            <h4>Метрики сегментации</h4>
            <div className="metrics">
              <div className="metric">
                <span className="metric-label">Площадь печени:</span>
                <span className="metric-value">
                  {(segmentation.metrics.liver_area_ratio * 100).toFixed(2)}%
                </span>
              </div>
              <div className="metric">
                <span className="metric-label">Пикселей печени:</span>
                <span className="metric-value">
                  {segmentation.metrics.liver_pixels.toLocaleString()}
                </span>
              </div>
              <div className="metric">
                <span className="metric-label">Всего пикселей:</span>
                <span className="metric-value">
                  {segmentation.metrics.total_pixels.toLocaleString()}
                </span>
              </div>
            </div>
          </div>

          <div className="result-card">
            <h4>Информация о маске</h4>
            <div className="metrics">
              <div className="metric">
                <span className="metric-label">Размер маски:</span>
                <span className="metric-value">
                  {segmentation.mask_shape.join(' × ')}
                </span>
              </div>
              <div className="metric">
                <span className="metric-label">Площадь в пикселях:</span>
                <span className="metric-value">
                  {segmentation.mask_area_pixels.toLocaleString()}
                </span>
              </div>
              <div className="metric">
                <span className="metric-label">Статус:</span>
                <span className="metric-value status-success">
                  {segmentation.success ? '✅ Успешно' : '❌ Ошибка'}
                </span>
              </div>
            </div>
          </div>

          <div className="result-card">
            <h4>Информация DICOM</h4>
            <div className="metrics">
              <div className="metric">
                <span className="metric-label">Модальность:</span>
                <span className="metric-value">{dicom_info.modality}</span>
              </div>
              <div className="metric">
                <span className="metric-label">Размер среза:</span>
                <span className="metric-value">
                  {dicom_info.rows} × {dicom_info.columns}
                </span>
              </div>
              <div className="metric">
                <span className="metric-label">Толщина среза:</span>
                <span className="metric-value">{dicom_info.slice_thickness} мм</span>
              </div>
              <div className="metric">
                <span className="metric-label">Описание исследования:</span>
                <span className="metric-value">
                  {dicom_info.study_description || 'Не указано'}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'visualization' && segmentation.visualization && (
        <div className="visualization-tab">
          <div className="visualization-container">
            <h4>Наложение маски сегментации</h4>
            <p className="visualization-description">
              <span className="legend-red">🔴 Красная область</span> - сегментированная печень
            </p>
            <img 
              src={`data:image/png;base64,${segmentation.visualization}`} 
              alt="Segmentation visualization" 
              className="visualization-image"
            />
            <div className="visualization-info">
              <p>
                Обнаружено <strong>{segmentation.metrics.liver_pixels.toLocaleString()}</strong> пикселей печени, 
                что составляет <strong>{(segmentation.metrics.liver_area_ratio * 100).toFixed(2)}%</strong> от общей площади среза.
              </p>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'visualization' && !segmentation.visualization && (
        <div className="no-visualization">
          <p>Визуализация недоступна для этого результата</p>
        </div>
      )}
    </div>
  );
};

export default SegmentationResult;