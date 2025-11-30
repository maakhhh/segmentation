import React, { useState } from 'react';
import { apiService } from '../services/api';

interface FileUploadProps {
  onUploadSuccess: () => void;
}

const FileUpload: React.FC<FileUploadProps> = ({ onUploadSuccess }) => {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState('');

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadMessage('');

    try {
      await apiService.uploadFile(file);
      setUploadMessage(`✅ Файл "${file.name}" успешно загружен`);
      onUploadSuccess();
    } catch (error) {
      setUploadMessage(`❌ Ошибка загрузки: ${error}`);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="file-upload">
      <h3>Загрузка DICOM файлов</h3>
      <div className="upload-area">
        <input
          type="file"
          id="file-upload"
          accept=".dcm,.png,.jpg,.jpeg"
          onChange={handleFileUpload}
          disabled={isUploading}
        />
        <label htmlFor="file-upload" className="upload-button">
          {isUploading ? 'Загрузка...' : 'Выберите файл'}
        </label>
      </div>
      {uploadMessage && <div className="upload-message">{uploadMessage}</div>}
    </div>
  );
};

export default FileUpload;