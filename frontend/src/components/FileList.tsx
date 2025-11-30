import React, { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import { FileInfo } from '../types/api';

interface FileListProps {
  refreshTrigger: number;
  onFileSelect: (filename: string) => void;
}

const FileList: React.FC<FileListProps> = ({ refreshTrigger, onFileSelect }) => {
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadFiles();
  }, [refreshTrigger]);

  const loadFiles = async () => {
    setLoading(true);
    try {
      const fileList = await apiService.listFiles();
      setFiles(fileList);
    } catch (error) {
      console.error('Error loading files:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  if (loading) return <div>Загрузка файлов...</div>;

  return (
    <div className="file-list">
      <h3>Загруженные файлы ({files.length})</h3>
      {files.length === 0 ? (
        <p>Нет загруженных файлов</p>
      ) : (
        <div className="files-grid">
          {files.map((file) => (
            <div key={file.name} className="file-card" onClick={() => onFileSelect(file.name)}>
              <div className="file-name">{file.name}</div>
              <div className="file-size">{formatFileSize(file.size)}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default FileList;