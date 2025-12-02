import React, { useState, useEffect } from "react";
import FileUpload from "./components/FileUpload";
import FileList from "./components/FileList";
import DicomViewer from "./components/DicomViewer";
import SegmentationResult from "./components/SegmentationResult";
import SeriesSegmentationResults from "./components/SeriesSegmentationResults"; // Добавить
import { apiService } from "./services/api";
import { HealthStatus } from "./types/api";
import "./App.css";

import SeriesUpload from "./components/SeriesUpload";
import SeriesList from "./components/SeriesList";

const App: React.FC = () => {
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);

  // ---- обычные файлы ----
  const [selectedFile, setSelectedFile] = useState<string>("");
  const [refreshFiles, setRefreshFiles] = useState(0);
  const [fileSegmentation, setFileSegmentation] = useState<any>(null);

  // ---- серии ----
  const [selectedSeries, setSelectedSeries] = useState<string | null>(null);
  const [refreshSeries, setRefreshSeries] = useState(0);
  const [seriesSegmentation, setSeriesSegmentation] = useState<any>(null);

  // ---- UI ----
  const [activeTab, setActiveTab] = useState<"files" | "series">("files");

  useEffect(() => {
    loadHealth();
  }, []);

  const loadHealth = async () => {
    try {
      const status = await apiService.getHealth();
      setHealthStatus(status);
    } catch (e) {
      console.error("Health check failed:", e);
    }
  };

  // --------------------------------------------------------
  // HANDLE FILE SEGMENTATION
  // --------------------------------------------------------
  const handleSegmentFile = async () => {
    if (!selectedFile) return;

    try {
      const result = await apiService.segmentFile(selectedFile);
      setFileSegmentation(result);
    } catch (e) {
      alert("Ошибка сегментации файла: " + e);
    }
  };

  // --------------------------------------------------------
  // HANDLE SERIES SEGMENTATION
  // --------------------------------------------------------
  const handleSegmentSeries = async () => {
    if (!selectedSeries) return;
    try {
      const result = await apiService.segmentSeries(selectedSeries);
      setSeriesSegmentation(result);
    } catch (e) {
      alert("Ошибка сегментации серии: " + e);
    }
  };

  // --------------------------------------------------------
  // HANDLE SERIES SELECTION
  // --------------------------------------------------------
  const handleSelectSeries = (seriesName: string) => {
    setSelectedSeries(seriesName);
    setSeriesSegmentation(null);
  };

  // --------------------------------------------------------
  // HANDLE TAB SWITCH
  // --------------------------------------------------------
  const handleTabSwitch = (tab: "files" | "series") => {
    setActiveTab(tab);
    // Сбрасываем выбранные элементы при переключении вкладок
    if (tab === "files") {
      setSelectedSeries(null);
      setSeriesSegmentation(null);
    } else {
      setSelectedFile("");
      setFileSegmentation(null);
    }
  };

  // --------------------------------------------------------
  // HANDLE FILE SELECTION
  // --------------------------------------------------------
  const handleSelectFile = (filename: string) => {
    setSelectedFile(filename);
    setFileSegmentation(null);
  };

  return (
    <div className="app">
      {/* HEADER */}
      <header className="app-header">
        <h1>🍃 Сервис сегментации печени</h1>
      </header>

      {/* TABS */}
      <div className="tabs-main" style={{ marginTop: '1.5rem' }}>
        <button
          className={`main-tab ${activeTab === "files" ? "active" : ""}`}
          onClick={() => handleTabSwitch("files")}
        >
          Одиночные файлы
        </button>
        <button
          className={`main-tab ${activeTab === "series" ? "active" : ""}`}
          onClick={() => handleTabSwitch("series")}
        >
          Серии (ZIP)
        </button>
      </div>

      {/* MAIN CONTENT */}
      <div className="app-content">
        {/* --------------------------------------------------------
            TAB: FILES
        -------------------------------------------------------- */}
        {activeTab === "files" && (
          <>
            <div className="sidebar">
              <FileUpload onUploadSuccess={() => setRefreshFiles(p => p + 1)} />
              <FileList
                refreshTrigger={refreshFiles}
                onFileSelect={handleSelectFile}
              />
            </div>

            <div className="main-content">
              {selectedFile ? (
                <>
                  <div className="file-actions">
                    <div className="file-header">
                      <h3>Выбран файл:</h3>
                      <div className="selected-filename">{selectedFile}</div>
                    </div>
                    <button className="segment-button" onClick={handleSegmentFile}>
                      🎯 Сегментировать файл
                    </button>
                  </div>

                  <DicomViewer filename={selectedFile} />

                  {fileSegmentation && (
                    <div className="segmentation-section">
                      <h3 className="section-title">Результаты сегментации</h3>
                      <SegmentationResult data={fileSegmentation} />
                    </div>
                  )}
                </>
              ) : (
                <div className="empty-state">
                  <div className="empty-icon">📄</div>
                  <h3>Выберите файл для просмотра</h3>
                  <p>Загрузите DICOM файл и выберите его из списка для отображения и сегментации</p>
                </div>
              )}
            </div>
          </>
        )}

        {/* --------------------------------------------------------
            TAB: SERIES
        -------------------------------------------------------- */}
        {activeTab === "series" && (
          <>
            <div className="sidebar">
              <SeriesUpload onSuccess={() => setRefreshSeries(p => p + 1)} />

              <SeriesList
                refreshTrigger={refreshSeries}
                onSelect={handleSelectSeries}
                selectedSeries={selectedSeries}
              />
            </div>

            <div className="main-content">
              {selectedSeries ? (
                <>
                  <div className="file-actions">
                    <div className="file-header">
                      <h3>Выбрана серия:</h3>
                      <div className="selected-filename">{selectedSeries}</div>
                    </div>
                    <button className="segment-button" onClick={handleSegmentSeries}>
                      🎯 Сегментировать серию
                    </button>
                  </div>

                  {seriesSegmentation ? (
                    <SeriesSegmentationResults
                      data={seriesSegmentation}
                      seriesName={selectedSeries}
                    />
                  ) : (
                    <div className="empty-state">
                      <div className="empty-icon">🔬</div>
                      <h3>Серия готова к сегментации</h3>
                      <p>Нажмите кнопку "Сегментировать серию" для начала обработки всех файлов в серии</p>
                    </div>
                  )}
                </>
              ) : (
                <div className="empty-state">
                  <div className="empty-icon">🗂️</div>
                  <h3>Выберите серию для обработки</h3>
                  <p>Загрузите ZIP архив с DICOM файлами и выберите серию из списка для сегментации</p>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default App;