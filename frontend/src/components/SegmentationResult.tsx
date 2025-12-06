import React, { useState, useEffect } from 'react';
import { SegmentationResult as SegmentationResultType } from '../types/api';
import ThreeDViewer from './ThreeDViewer';
import { apiService } from '../services/api';

// Вспомогательные функции
const getVolumeColor = (volume: number): string => {
  if (volume === 0) return '#666';
  if (volume < 1000) return '#f44336';   // красный — мало
  if (volume > 1600) return '#ff9800';   // оранжевый — много
  return '#4CAF50';                      // зелёный — норма
};

const getVolumeAssessment = (volume: number): string => {
  if (volume === 0) return 'Нет данных';
  if (volume < 1000) return 'Уменьшенный объём';
  if (volume > 1600) return 'Увеличенный объём';
  return 'Нормальный объём';
};

interface SegmentationResultProps {
  data: any;
}

const SegmentationResult: React.FC<SegmentationResultProps> = ({ data }) => {
  const isZipResult = data.type === 'zip' || !!data.series_info;

  const [activeTab, setActiveTab] = useState<'metrics' | 'visualization' | '3d'>(
    isZipResult ? '3d' : 'metrics'
  );
  const [reconstructionData, setReconstructionData] = useState<any>(null);
  const [loading3D, setLoading3D] = useState(false);
  const [exporting, setExporting] = useState(false);

  // Если 3D-модель уже пришла с бэкенда
  useEffect(() => {
    if (data.reconstruction) {
      setReconstructionData(data.reconstruction);
    }
  }, [data]);

  const handleCreate3D = async () => {
    if (!data.filename || isZipResult) return;
    setLoading3D(true);
    try {
      const result = await apiService.reconstruct3D(data.filename);
      setReconstructionData(result.reconstruction);
      setActiveTab('3d');
    } catch (err) {
      console.error(err);
      alert('Ошибка создания 3D-модели');
    } finally {
      setLoading3D(false);
    }
  };

  const handleExport = async (format: 'stl' | 'ply') => {
    if (!data.filename) return;
    setExporting(true);
    try {
      const blob = await apiService.export3DModel(data.filename, format);
      apiService.downloadFile(blob, `liver_model_${data.filename}.${format}`);
    } catch (err) {
      console.error(err);
      alert('Ошибка экспорта');
    } finally {
      setExporting(false);
    }
  };

  if (!data) {
    return <div style={{ padding: '20px', textAlign: 'center' }}>Нет данных</div>;
  }

  const { filename, segmentation, dicom_info, series_info } = data;

  return (
    <div
      style={{
        background: 'white',
        borderRadius: '10px',
        padding: '20px',
        boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
        marginTop: '20px',
      }}
    >
      <h3 style={{ marginTop: 0 }}>
        {isZipResult ? 'Результаты обработки ZIP-архива' : 'Результаты сегментации'}
      </h3>

      {/* Инфо о файле */}
      <div style={{ background: '#e3f2fd', padding: '10px 15px', borderRadius: '5px', marginBottom: '20px' }}>
        <strong>Файл:</strong> {filename}
        {isZipResult && series_info && (
          <div style={{ marginTop: '5px' }}>
            <strong>Срезов:</strong> {series_info.num_slices} | <strong>Размер:</strong>{' '}
            {series_info.volume_shape?.join(' × ')}
          </div>
        )}
      </div>

      {/* Кнопка создания 3D для одиночного файла */}
      {!isZipResult && !reconstructionData && (
        <div style={{ marginBottom: '20px' }}>
          <button
            onClick={handleCreate3D}
            disabled={loading3D}
            style={{
              padding: '12px 24px',
              background: '#4CAF50',
              color: 'white',
              border: 'none',
              borderRadius: '5px',
              cursor: loading3D ? 'not-allowed' : 'pointer',
              opacity: loading3D ? 0.7 : 1,
              fontSize: '16px',
            }}
          >
            {loading3D ? 'Создание 3D...' : 'Создать 3D модель'}
          </button>
        </div>
      )}

      {/* Табы */}
      <div style={{ display: 'flex', gap: '20px', marginBottom: '20px', borderBottom: '1px solid #ddd' }}>
        {!isZipResult && (
          <>
            <button
              onClick={() => setActiveTab('metrics')}
              style={{
                padding: '10px 20px',
                border: 'none',
                background: 'transparent',
                borderBottom: activeTab === 'metrics' ? '3px solid #007acc' : '3px solid transparent',
                color: activeTab === 'metrics' ? '#007acc' : '#333',
                fontWeight: activeTab === 'metrics' ? 'bold' : 'normal',
                cursor: 'pointer',
              }}
            >
              Метрики 2D
            </button>
            <button
              onClick={() => setActiveTab('visualization')}
              style={{
                padding: '10px 20px',
                border: 'none',
                background: 'transparent',
                borderBottom: activeTab === 'visualization' ? '3px solid #007acc' : '3px solid transparent',
                color: activeTab === 'visualization' ? '#007acc' : '#333',
                fontWeight: activeTab === 'visualization' ? 'bold' : 'normal',
                cursor: 'pointer',
              }}
            >
              Визуализация 2D
            </button>
          </>
        )}

        <button
          onClick={() => reconstructionData && setActiveTab('3d')}
          disabled={!reconstructionData && !isZipResult}
          style={{
            padding: '10px 20px',
            border: 'none',
            background: 'transparent',
            borderBottom: activeTab === '3d' ? '3px solid #007acc' : '3px solid transparent',
            color: reconstructionData || isZipResult ? (activeTab === '3d' ? '#007acc' : '#333') : '#999',
            fontWeight: activeTab === '3d' ? 'bold' : 'normal',
            cursor: reconstructionData || isZipResult ? 'pointer' : 'not-allowed',
          }}
        >
          3D Модель {isZipResult ? '(ZIP)' : ''}
        </button>
      </div>

      {/* 2D Метрики */}
      {activeTab === 'metrics' && segmentation && !isZipResult && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px' }}>
          {/* Карточка: Метрики сегментации */}
          <div style={{ padding: '20px', background: '#f9f9f9', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
            <h4 style={{ marginTop: 0, color: '#007acc' }}>Метрики сегментации</h4>
            {segmentation.metrics && (
              <>
                <div style={{ marginBottom: '10px' }}>
                  <span style={{ fontWeight: 'bold' }}>Площадь печени:</span>
                  <span style={{ float: 'right' }}>
                    {(segmentation.metrics.liver_area_ratio * 100).toFixed(2)}%
                  </span>
                </div>
                <div style={{ marginBottom: '10px' }}>
                  <span style={{ fontWeight: 'bold' }}>Пикселей печени:</span>
                  <span style={{ float: 'right' }}>
                    {segmentation.metrics.liver_pixels?.toLocaleString()}
                  </span>
                </div>
                <div style={{ marginBottom: '10px' }}>
                  <span style={{ fontWeight: 'bold' }}>Всего пикселей:</span>
                  <span style={{ float: 'right' }}>
                    {segmentation.metrics.total_pixels?.toLocaleString()}
                  </span>
                </div>
              </>
            )}
          </div>

          {/* Карточка: Информация о маске */}
          {segmentation.mask_shape && (
            <div style={{ padding: '20px', background: '#f9f9f9', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
              <h4 style={{ marginTop: 0, color: '#007acc' }}>Информация о маске</h4>
              <div style={{ marginBottom: '10px' }}>
                <span style={{ fontWeight: 'bold' }}>Размер маски:</span>
                <span style={{ float: 'right' }}>{segmentation.mask_shape.join(' × ')}</span>
              </div>
              <div style={{ marginBottom: '10px' }}>
                <span style={{ fontWeight: 'bold' }}>Площадь в пикселях:</span>
                <span style={{ float: 'right' }}>{segmentation.mask_area_pixels?.toLocaleString()}</span>
              </div>
              <div style={{ marginBottom: '10px' }}>
                <span style={{ fontWeight: 'bold' }}>Статус:</span>
                <span style={{ float: 'right', color: segmentation.success ? '#4CAF50' : '#f44336' }}>
                  {segmentation.success ? 'Успешно' : 'Ошибка'}
                </span>
              </div>
            </div>
          )}

          {/* Карточка: Информация DICOM */}
          {dicom_info && (
            <div style={{ padding: '20px', background: '#f9f9f9', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
              <h4 style={{ marginTop: 0, color: '#007acc' }}>Информация DICOM</h4>
              <div style={{ marginBottom: '10px' }}>
                <span style={{ fontWeight: 'bold' }}>Модальность:</span>
                <span style={{ float: 'right' }}>{dicom_info.modality}</span>
              </div>
              <div style={{ marginBottom: '10px' }}>
                <span style={{ fontWeight: 'bold' }}>Размер среза:</span>
                <span style={{ float: 'right' }}>{dicom_info.rows} × {dicom_info.columns}</span>
              </div>
              <div style={{ marginBottom: '10px' }}>
                <span style={{ fontWeight: 'bold' }}>Толщина среза:</span>
                <span style={{ float: 'right' }}>{dicom_info.slice_thickness} мм</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 2D Визуализация */}
      {activeTab === 'visualization' && segmentation?.visualization && !isZipResult && (
        <div style={{ textAlign: 'center' }}>
          <h4>Наложение маски сегментации</h4>
          <p style={{ color: '#666' }}>
            <span style={{ color: '#f44336', fontWeight: 'bold' }}>Красная область</span> — сегментированная печень
          </p>
          <img
            src={`data:image/png;base64,${segmentation.visualization}`}
            alt="Segmentation"
            style={{ maxWidth: '100%', borderRadius: '8px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }}
          />
        </div>
      )}

      {/* 3D Вкладка */}
      {activeTab === '3d' && (reconstructionData || isZipResult) && (
        <div>
          {/* Заголовок + кнопки экспорта */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px', marginBottom: '20px' }}>
            <h4 style={{ margin: 0 }}>{isZipResult ? '3D Модель печени из серии DICOM' : '3D Модель печени'}</h4>
            <div>
              <button onClick={() => handleExport('stl')} disabled={exporting} style={{ padding: '10px 20px', background: '#2196F3', color: 'white', border: 'none', borderRadius: '5px', marginLeft: '8px' }}>
                {exporting ? 'Экспорт...' : 'Скачать STL'}
              </button>
              <button onClick={() => handleExport('ply')} disabled={exporting} style={{ padding: '10px 20px', background: '#2196F3', color: 'white', border: 'none', borderRadius: '5px', marginLeft: '8px' }}>
                {exporting ? 'Экспорт...' : 'Скачать PLY'}
              </button>
            </div>
          </div>

          {/* Инфо о серии (для ZIP) */}
          {isZipResult && series_info && (
            <div style={{ background: '#e8f5e9', padding: '15px', borderRadius: '8px', marginBottom: '20px' }}>
              <h5 style={{ margin: '0 0 10px 0', color: '#2e7d32' }}>Информация о серии</h5>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' }}>
                <div><strong>Срезов:</strong> {series_info.num_slices}</div>
                <div><strong>Размер:</strong> {series_info.volume_shape?.join(' × ')}</div>
                <div><strong>Разрешение:</strong> {series_info.spacing?.map((s: number) => s.toFixed(2)).join(' × ')} мм</div>
                <div><strong>Файлов:</strong> {series_info.num_dicom_files}</div>
              </div>
            </div>
          )}

          {/* 3D Viewer */}
          {reconstructionData?.stl_base64 ? (
            <ThreeDViewer stlBase64={reconstructionData.stl_base64} />
          ) : (
            <div style={{ textAlign: 'center', padding: '40px', background: '#f5f5f5', borderRadius: '8px' }}>
              <p>3D модель загружается...</p>
            </div>
          )}

          {/* ЕДИНСТВЕННЫЙ КРАСИВЫЙ БЛОК МЕТРИК */}
          {(reconstructionData?.metrics || data.reconstruction?.metrics) && (
            <div style={{ marginTop: '30px' }}>
              <h5>Метрики 3D модели</h5>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '20px' }}>
                {/* Объём */}
                <div style={{ padding: '20px', background: 'linear-gradient(135deg, #e3f2fd, #bbdefb)', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }}>
                  <div style={{ fontSize: '14px', color: '#1565c0' }}>Объём печени</div>
                  <div style={{ fontSize: '1.5em', fontWeight: 'bold', color: '#0d47a1' }}>
                    {(reconstructionData?.metrics?.volume_ml || data.reconstruction?.metrics?.volume_ml || 0).toFixed(1)} мл
                  </div>
                  <div style={{ fontSize: '0.9em', color: getVolumeColor(reconstructionData?.metrics?.volume_ml || data.reconstruction?.metrics?.volume_ml || 0) }}>
                    {getVolumeAssessment(reconstructionData?.metrics?.volume_ml || data.reconstruction?.metrics?.volume_ml || 0)}
                  </div>
                </div>

                {/* Площадь поверхности */}
                <div style={{ padding: '20px', background: 'linear-gradient(135deg, #e8f5e9, #c8e6c9)', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }}>
                  <div style={{ fontSize: '14px', color: '#2e7d32' }}>Площадь поверхности</div>
                  <div style={{ fontSize: '1.5em', fontWeight: 'bold', color: '#1b5e20' }}>
                    {(reconstructionData?.metrics?.surface_area_cm2 || data.reconstruction?.metrics?.surface_area_cm2 || 0).toFixed(1)} см²
                  </div>
                </div>

                {/* Вершины */}
                <div style={{ padding: '20px', background: 'linear-gradient(135deg, #f3e5f5, #e1bee7)', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }}>
                  <div style={{ fontSize: '14px', color: '#6a1b9a' }}>Вершин</div>
                  <div style={{ fontSize: '1.5em', fontWeight: 'bold', color: '#4a148c' }}>
                    {(reconstructionData?.mesh_info?.num_vertices || data.reconstruction?.mesh_info?.num_vertices || 0).toLocaleString()}
                  </div>
                </div>

                {/* Грани */}
                <div style={{ padding: '20px', background: 'linear-gradient(135deg, #fff3e0, #ffe0b2)', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }}>
                  <div style={{ fontSize: '14px', color: '#e65100' }}>Граней</div>
                  <div style={{ fontSize: '1.5em', fontWeight: 'bold', color: '#bf360c' }}>
                    {(reconstructionData?.mesh_info?.num_faces || data.reconstruction?.mesh_info?.num_faces || 0).toLocaleString()}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Если 3D ещё нет */}
      {activeTab === '3d' && !reconstructionData && !isZipResult && (
        <div style={{ textAlign: 'center', padding: '40px', background: '#f5f5f5', borderRadius: '8px' }}>
          <p>3D модель ещё не создана.</p>
          <p style={{ color: '#666' }}>Нажмите кнопку «Создать 3D модель» выше.</p>
        </div>
      )}
    </div>
  );
};

export default SegmentationResult;