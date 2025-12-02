import React, { useEffect, useState } from "react";
import { apiService } from "../services/api";

interface SeriesData {
  series_name: string;
  files: string[];
}

interface Props {
  refreshTrigger: number;
  onSelect: (seriesName: string) => void;
  selectedSeries?: string | null; // ← ДОБАВЬТЕ ЭТО
}

const SeriesList: React.FC<Props> = ({ refreshTrigger, onSelect, selectedSeries }) => {
  const [series, setSeries] = useState<SeriesData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadSeries();
  }, [refreshTrigger]);

  const loadSeries = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiService.listSeries();
      setSeries(data);
    } catch (err: any) {
      setError(err.message || "Ошибка загрузки серий");
      setSeries([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSeriesClick = (seriesName: string) => {
    onSelect(seriesName);
  };

  return (
    <div className="series-list">
      <h3>Серии ({series.length})</h3>
      
      {loading && <p>Загрузка...</p>}
      {error && <p className="error">Ошибка: {error}</p>}
      
      {!loading && !error && series.length === 0 ? (
        <p>Нет загруженных серий</p>
      ) : (
        <ul>
          {series.map((item) => (
            <li 
              key={item.series_name} 
              onClick={() => handleSeriesClick(item.series_name)}
              className={`series-item ${selectedSeries === item.series_name ? 'selected' : ''}`}
            >
              <div className="series-name">📦 {item.series_name}</div>
              <div className="file-count">({item.files.length} файлов)</div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default SeriesList;