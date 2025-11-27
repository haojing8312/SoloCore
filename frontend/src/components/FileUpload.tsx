/**
 * File upload component with drag & drop support
 */

import { useCallback, useState } from 'react';
import { useFileUpload } from '@/hooks/useFileUpload';
import { useTaskStore } from '@/stores/taskStore';
import { formatFileSize } from '@/utils/format';

interface FileUploadProps {
  onFileUploaded?: (fileId: string) => void;
}

export function FileUpload({ onFileUploaded }: FileUploadProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const { upload, isUploading, error } = useFileUpload();
  const uploadProgress = useTaskStore((state) => state.uploadProgress);

  const handleFileSelect = useCallback(
    async (file: File) => {
      setSelectedFile(file);
      const fileId = await upload(file);
      if (fileId && onFileUploaded) {
        onFileUploaded(fileId);
      }
    },
    [upload, onFileUploaded]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setIsDragging(false);

      const files = e.dataTransfer.files;
      if (files.length > 0) {
        handleFileSelect(files[0]);
      }
    },
    [handleFileSelect]
  );

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files && files.length > 0) {
        handleFileSelect(files[0]);
      }
    },
    [handleFileSelect]
  );

  return (
    <div className="w-full">
      <div
        className={`
          relative border-2 border-dashed rounded-lg p-8 text-center transition-colors
          ${isDragging ? 'border-primary bg-primary/5' : 'border-border'}
          ${isUploading ? 'pointer-events-none opacity-50' : 'cursor-pointer hover:border-primary'}
        `}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => document.getElementById('file-input')?.click()}
      >
        <input
          id="file-input"
          type="file"
          accept=".md,.markdown,.txt"
          className="hidden"
          onChange={handleInputChange}
          disabled={isUploading}
        />

        <div className="flex flex-col items-center gap-4">
          {/* Upload Icon */}
          <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
            <svg
              className="w-8 h-8 text-primary"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
          </div>

          {/* Upload Text */}
          <div>
            <p className="text-lg font-medium text-foreground mb-1">
              {isUploading ? '上传中...' : '点击上传或拖拽文件到此处'}
            </p>
            <p className="text-sm text-muted-foreground">
              支持 .md, .markdown, .txt 格式，最大 10MB
            </p>
          </div>

          {/* Selected File Info */}
          {selectedFile && !isUploading && (
            <div className="text-sm text-muted-foreground">
              已选择: {selectedFile.name} ({formatFileSize(selectedFile.size)})
            </div>
          )}

          {/* Upload Progress */}
          {isUploading && (
            <div className="w-full max-w-xs">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-muted-foreground">上传进度</span>
                <span className="text-sm font-medium text-foreground">{uploadProgress}%</span>
              </div>
              <div className="w-full h-2 bg-secondary rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mt-4 p-4 bg-destructive/10 border border-destructive/20 rounded-lg">
          <p className="text-sm text-destructive">{error}</p>
        </div>
      )}
    </div>
  );
}
