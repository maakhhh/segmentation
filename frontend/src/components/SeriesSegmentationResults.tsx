import React, { useState } from 'react';
import { SeriesSegmentationResult } from '../types/api';

interface SeriesSegmentationResultsProps {
  data: SeriesSegmentationResult;
  seriesName: string;
}

const SeriesSegmentationResults: React.FC<SeriesSegmentationResultsProps> = ({ 
  data, 
  seriesName 
}) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'slices'>('overview');
  const [currentSliceIndex, setCurrentSliceIndex] = useState(0);
  
  const { segmentation, volume_shape, total_volume } = data;
  const totalSlices = segmentation.length;
  
  // Общая статистика по всем срезам
  const totalLiverPixels = segmentation.reduce((sum, slice) => 
    sum + slice.metrics.liver_pixels, 0
  );
  
  const avgLiverRatio = segmentation.reduce((sum, slice) => 
    sum + slice.metrics.liver_area_ratio, 0
  ) / totalSlices;
  
  const successfulSlices = segmentation.filter(s => s.success).length;
  const slicesWithVisualization = segmentation.filter(s => s.visualization).length;

  // Навигация по срезам
  const goToPrevSlice = () => {
    setCurrentSliceIndex(prev => Math.max(0, prev - 1));
  };

  const goToNextSlice = () => {
    setCurrentSliceIndex(prev => Math.min(totalSlices - 1, prev + 1));
  };

  const goToSliceWithVisualization = (direction: 'next' | 'prev') => {
    let newIndex = currentSliceIndex;
    const step = direction === 'next' ? 1 : -1;
    
    while (true) {
      newIndex = (newIndex + step + totalSlices) % totalSlices;
      if (segmentation[newIndex].visualization) {
        setCurrentSliceIndex(newIndex);
        break;
      }
      if (newIndex === currentSliceIndex) break; // Полный круг
    }
  };

  const currentSlice = segmentation[currentSliceIndex];

  return (
    <div className="series-segmentation-results">
      <div className="series-results-header">
        <h2>Результаты сегментации серии: {seriesName}</h2>
        <div className="series-stats">
          <span className="stat-item">
            <span className="stat-label">Срезов:</span>
            <span className="stat-value">{totalSlices}</span>
          </span>
          <span className="stat-item">
            <span className="stat-label">Успешно:</span>
            <span className="stat-value success">{successfulSlices}</span>
          </span>
          <span className="stat-item">
            <span className="stat-label">С визуализацией:</span>
            <span className="stat-value">{slicesWithVisualization}</span>
          </span>
          <span className="stat-item">
            <span className="stat-label">Размер объема:</span>
            <span className="stat-value">{volume_shape.join(' × ')}</span>
          </span>
          {total_volume && (
            <span className="stat-item">
              <span className="stat-label">Объем печени:</span>
              <span className="stat-value">{total_volume.toFixed(2)} мл</span>
            </span>
          )}
        </div>
      </div>

      {/* Табы для переключения между обзором и отдельными срезами */}
      <div className="series-tabs">
        <button
          className={`series-tab ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          📊 Обзор серии
        </button>
        <button
          className={`series-tab ${activeTab === 'slices' ? 'active' : ''}`}
          onClick={() => setActiveTab('slices')}
        >
          🖼️ Просмотр срезов
        </button>
      </div>

      {/* Обзор серии */}
      {activeTab === 'overview' && (
        <div className="series-overview">
          <div className="overview-grid">
            <div className="overview-card">
              <h4>📈 Общая статистика</h4>
              <div className="overview-metrics">
                <div className="overview-metric">
                  <div className="metric-title">Средняя площадь печени</div>
                  <div className="metric-value">{(avgLiverRatio * 100).toFixed(2)}%</div>
                  <div className="metric-description">от площади среза</div>
                </div>
                <div className="overview-metric">
                  <div className="metric-title">Всего пикселей печени</div>
                  <div className="metric-value">{totalLiverPixels.toLocaleString()}</div>
                  <div className="metric-description">пикселей</div>
                </div>
                <div className="overview-metric">
                  <div className="metric-title">Успешно сегментировано</div>
                  <div className="metric-value">{successfulSlices}/{totalSlices}</div>
                  <div className="metric-description">срезов</div>
                </div>
              </div>
            </div>

            <div className="overview-card">
              <h4>📊 Распределение по срезам</h4>
              <div className="distribution-chart">
                {segmentation.slice(0, 10).map((slice, index) => (
                  <div key={index} className="chart-bar-container">
                    <div className="chart-bar-label">Срез {index + 1}</div>
                    <div className="chart-bar">
                      <div 
                        className="chart-bar-fill"
                        style={{ 
                          width: `${slice.metrics.liver_area_ratio * 100}%`,
                          backgroundColor: slice.success ? 
                            (slice.visualization ? '#27ae60' : '#f39c12') : '#e74c3c'
                        }}
                      />
                    </div>
                    <div className="chart-bar-value">
                      {(slice.metrics.liver_area_ratio * 100).toFixed(1)}%
                    </div>
                  </div>
                ))}
                {totalSlices > 10 && (
                  <div className="chart-more">
                    ... и еще {totalSlices - 10} срезов
                  </div>
                )}
                <div className="chart-legend">
                  <div className="legend-item">
                    <span className="legend-color" style={{backgroundColor: '#27ae60'}}></span>
                    <span>Срез с визуализацией</span>
                  </div>
                  <div className="legend-item">
                    <span className="legend-color" style={{backgroundColor: '#f39c12'}}></span>
                    <span>Срез без визуализации</span>
                  </div>
                  <div className="legend-item">
                    <span className="legend-color" style={{backgroundColor: '#e74c3c'}}></span>
                    <span>Ошибка сегментации</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="overview-card">
              <h4>📋 Детали серии</h4>
              <div className="series-details">
                <div className="detail-row">
                  <span className="detail-label">Размер объема:</span>
                  <span className="detail-value">{volume_shape.join(' × ')}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Общее количество срезов:</span>
                  <span className="detail-value">{totalSlices}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Размер среза:</span>
                  <span className="detail-value">{volume_shape[1]} × {volume_shape[2]}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">С визуализацией:</span>
                  <span className="detail-value">{slicesWithVisualization}</span>
                </div>
                {total_volume && (
                  <div className="detail-row">
                    <span className="detail-label">Общий объем печени:</span>
                    <span className="detail-value highlight">{total_volume.toFixed(2)} мл</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Просмотр отдельных срезов */}
      {activeTab === 'slices' && (
        <div className="slices-view">
          <div className="slice-navigation">
            <button 
              className="nav-button" 
              onClick={goToPrevSlice}
              disabled={currentSliceIndex === 0}
            >
              ◀ Предыдущий
            </button>
            
            <div className="slice-controls">
              <div className="slice-info">
                <span className="slice-number">
                  Срез {currentSliceIndex + 1} из {totalSlices}
                </span>
                <div className="slice-stats">
                  <span className="slice-stat">
                    Площадь: {(currentSlice.metrics.liver_area_ratio * 100).toFixed(2)}%
                  </span>
                  <span className="slice-stat">
                    Пикселей: {currentSlice.metrics.liver_pixels.toLocaleString()}
                  </span>
                  <span className={`slice-status ${currentSlice.success ? 'success' : 'error'}`}>
                    {currentSlice.success ? 'Успешно' : 'Ошибка'}
                  </span>
                </div>
              </div>
            </div>
            
            <button 
              className="nav-button" 
              onClick={goToNextSlice}
              disabled={currentSliceIndex === totalSlices - 1}
            >
              Следующий ▶
            </button>
          </div>

          <div className="slice-content">
            {currentSlice.visualization ? (
              <div className="slice-visualization">
                <h4>Визуализация среза {currentSliceIndex + 1}</h4>
                <p className="visualization-description">
                  <span className="legend-red">🔴 Красная область</span> - сегментированная печень
                </p>
                <img 
                  src={`data:image/png;base64,${currentSlice.visualization}`} 
                  alt={`Сегментация среза ${currentSliceIndex + 1}`}
                  className="slice-image"
                />
                <div className="slice-metrics">
                  <div className="slice-metric">
                    <span>Площадь печени:</span>
                    <strong>{(currentSlice.metrics.liver_area_ratio * 100).toFixed(2)}%</strong>
                  </div>
                  <div className="slice-metric">
                    <span>Пикселей печени:</span>
                    <strong>{currentSlice.metrics.liver_pixels.toLocaleString()}</strong>
                  </div>
                  <div className="slice-metric">
                    <span>Всего пикселей:</span>
                    <strong>{currentSlice.metrics.total_pixels.toLocaleString()}</strong>
                  </div>
                  <div className="slice-metric">
                    <span>Площадь в пикселях:</span>
                    <strong>{currentSlice.mask_area_pixels.toLocaleString()}</strong>
                  </div>
                </div>
              </div>
            ) : (
              <div className="no-visualization">
                <div className="no-vis-icon">🖼️</div>
                <h4>Визуализация недоступна для среза {currentSliceIndex + 1}</h4>
                <p>Этот срез был успешно сегментирован, но визуализация не была создана.</p>
                
                <div className="slice-metrics-only">
                  <h4>Метрики среза {currentSliceIndex + 1}</h4>
                  <div className="metrics-grid">
                    <div className="metric-box">
                      <div className="metric-title">Площадь печени</div>
                      <div className="metric-value">
                        {(currentSlice.metrics.liver_area_ratio * 100).toFixed(2)}%
                      </div>
                    </div>
                    <div className="metric-box">
                      <div className="metric-title">Пикселей печени</div>
                      <div className="metric-value">
                        {currentSlice.metrics.liver_pixels.toLocaleString()}
                      </div>
                    </div>
                    <div className="metric-box">
                      <div className="metric-title">Всего пикселей</div>
                      <div className="metric-value">
                        {currentSlice.metrics.total_pixels.toLocaleString()}
                      </div>
                    </div>
                    <div className="metric-box">
                      <div className="metric-title">Статус</div>
                      <div className={`metric-value ${currentSlice.success ? 'success' : 'error'}`}>
                        {currentSlice.success ? '✅ Успешно' : '❌ Ошибка'}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Миниатюры срезов */}
          <div className="slice-thumbnails">
            {segmentation.slice(0, 20).map((slice, index) => (
              <button
                key={index}
                className={`thumbnail ${index === currentSliceIndex ? 'active' : ''} ${
                  slice.success ? (slice.visualization ? 'with-vis' : 'no-vis') : 'error'
                }`}
                onClick={() => setCurrentSliceIndex(index)}
                title={`Срез ${index + 1}: ${(slice.metrics.liver_area_ratio * 100).toFixed(1)}%`}
              >
                {index + 1}
                {slice.visualization && <span className="vis-indicator">👁</span>}
              </button>
            ))}
            {totalSlices > 20 && (
              <span className="thumbnail-more">...</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default SeriesSegmentationResults;