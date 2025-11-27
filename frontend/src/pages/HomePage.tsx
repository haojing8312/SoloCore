/**
 * Home Page - File upload and template selection
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileUpload } from '@/components/FileUpload';
import { TemplateSelector } from '@/components/TemplateSelector';
import { useTaskStore } from '@/stores/taskStore';
import { useUIStore } from '@/stores/uiStore';
import { createTask } from '@/services/taskService';
import { TASK_CONFIG } from '@/utils/constants';

export function HomePage() {
  const navigate = useNavigate();
  const [isCreatingTask, setIsCreatingTask] = useState(false);
  const uploadedFileId = useTaskStore((state) => state.uploadedFileId);
  const selectedTemplate = useTaskStore((state) => state.selectedTemplate);
  const showToast = useUIStore((state) => state.showToast);

  const handleCreateTask = async () => {
    // Validation
    if (!uploadedFileId) {
      showToast({
        type: 'error',
        message: '请先上传文件',
      });
      return;
    }

    if (!selectedTemplate) {
      showToast({
        type: 'error',
        message: '请选择一个字幕模板',
      });
      return;
    }

    setIsCreatingTask(true);

    try {
      const response = await createTask({
        fileId: uploadedFileId,
        subtitleTemplate: selectedTemplate,
        scriptStyle: TASK_CONFIG.DEFAULT_SCRIPT_STYLE,
        multiVideoCount: TASK_CONFIG.MULTI_VIDEO_COUNT,
      });

      if (response.success && response.data) {
        showToast({
          type: 'success',
          message: '任务创建成功',
        });
        // Navigate to task detail page
        navigate(`/tasks/${response.data.taskId}`);
      } else {
        throw new Error(response.message || '任务创建失败');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '任务创建失败,请重试';
      showToast({
        type: 'error',
        message: errorMessage,
      });
    } finally {
      setIsCreatingTask(false);
    }
  };

  const canCreateTask = uploadedFileId && selectedTemplate && !isCreatingTask;

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="container mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold text-foreground">TextLoom</h1>
          <p className="text-muted-foreground mt-2">
            AI 驱动的文档转视频平台 - 将 Markdown 文档转换为精美的视频内容
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto space-y-8">
          {/* File Upload Section */}
          <section>
            <h2 className="text-2xl font-semibold text-foreground mb-4">1. 上传文档</h2>
            <FileUpload />
          </section>

          {/* Template Selection Section */}
          <section>
            <h2 className="text-2xl font-semibold text-foreground mb-4">2. 选择字幕模板</h2>
            <TemplateSelector />
          </section>

          {/* Create Task Button */}
          <section className="flex justify-center pt-4">
            <button
              onClick={handleCreateTask}
              disabled={!canCreateTask}
              className={`
                inline-flex items-center justify-center gap-2 rounded-md text-base font-medium
                ring-offset-background transition-colors focus-visible:outline-none
                focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2
                h-12 px-8 py-3
                ${
                  canCreateTask
                    ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                    : 'bg-muted text-muted-foreground cursor-not-allowed'
                }
              `}
            >
              {isCreatingTask ? (
                <>
                  <svg
                    className="animate-spin h-5 w-5"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  创建中...
                </>
              ) : (
                <>
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                    />
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  开始生成
                </>
              )}
            </button>
          </section>
        </div>
      </main>
    </div>
  );
}
