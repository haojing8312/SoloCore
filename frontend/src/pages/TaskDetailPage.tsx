/**
 * Task Detail Page - View single task details with polling
 */

import { useParams, Link } from 'react-router-dom';
import { useTaskPolling } from '@/hooks/useTaskPolling';
import { ProgressBar } from '@/components/ProgressBar';
import { VideoPlayer } from '@/components/VideoPlayer';
import { cancelTask } from '@/services/taskService';
import { useUIStore } from '@/stores/uiStore';
import { formatDate, formatDuration } from '@/utils/format';
import { TaskStatus, canCancelTask } from '@/types';
import { useState } from 'react';

export function TaskDetailPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const showToast = useUIStore((state) => state.showToast);
  const [isCancelling, setIsCancelling] = useState(false);

  const { task, isLoading, isError, error, refetch } = useTaskPolling({
    taskId: taskId || '',
    enabled: !!taskId,
  });

  const handleCancelTask = async () => {
    if (!taskId || !task) return;

    setIsCancelling(true);
    try {
      const response = await cancelTask(taskId);
      if (response.success) {
        showToast({
          type: 'success',
          message: '任务已取消',
        });
        refetch();
      } else {
        throw new Error(response.message || '取消任务失败');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '取消任务失败';
      showToast({
        type: 'error',
        message: errorMessage,
      });
    } finally {
      setIsCancelling(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin h-12 w-12 border-4 border-primary border-t-transparent rounded-full mx-auto mb-4" />
          <p className="text-muted-foreground">加载中...</p>
        </div>
      </div>
    );
  }

  if (isError || !task) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center max-w-md">
          <h1 className="text-2xl font-bold text-foreground mb-4">加载失败</h1>
          <p className="text-muted-foreground mb-6">
            {error?.message || '无法获取任务状态,请稍后重试'}
          </p>
          <Link
            to="/"
            className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2"
          >
            返回首页
          </Link>
        </div>
      </div>
    );
  }

  const isCompleted = task.status === TaskStatus.COMPLETED;
  const isFailed = task.status === TaskStatus.FAILED;
  const isProcessing = task.status === TaskStatus.PROCESSING;

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-foreground">{task.filename}</h1>
              <p className="text-muted-foreground mt-2">
                任务 ID: {task.id} · 创建于 {formatDate(task.createdAt)}
              </p>
            </div>
            <Link
              to="/"
              className="inline-flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              返回首页
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <div className="max-w-3xl mx-auto space-y-8">
          {/* Status Card */}
          <div className="bg-card border border-border rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-foreground">任务状态</h2>
              <span
                className={`
                  px-3 py-1 rounded-full text-sm font-medium
                  ${task.status === TaskStatus.COMPLETED ? 'bg-green-500/10 text-green-500' : ''}
                  ${task.status === TaskStatus.PROCESSING ? 'bg-blue-500/10 text-blue-500' : ''}
                  ${task.status === TaskStatus.FAILED ? 'bg-red-500/10 text-red-500' : ''}
                  ${task.status === TaskStatus.PENDING ? 'bg-yellow-500/10 text-yellow-500' : ''}
                  ${task.status === TaskStatus.CANCELLED ? 'bg-gray-500/10 text-gray-500' : ''}
                `}
              >
                {task.status === TaskStatus.COMPLETED && '已完成'}
                {task.status === TaskStatus.PROCESSING && '处理中'}
                {task.status === TaskStatus.FAILED && '失败'}
                {task.status === TaskStatus.PENDING && '等待中'}
                {task.status === TaskStatus.CANCELLED && '已取消'}
              </span>
            </div>

            {/* Progress Bar for processing tasks */}
            {isProcessing && (
              <div className="mb-4">
                <ProgressBar progress={task.progress} currentPhase={task.currentPhase} />
              </div>
            )}

            {/* Task Info */}
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">字幕模板:</span>
                <span className="ml-2 text-foreground font-medium">{task.subtitleTemplate}</span>
              </div>
              {task.duration && (
                <div>
                  <span className="text-muted-foreground">视频时长:</span>
                  <span className="ml-2 text-foreground font-medium">{formatDuration(task.duration)}</span>
                </div>
              )}
            </div>

            {/* Error Message */}
            {isFailed && task.errorMessage && (
              <div className="mt-4 p-4 bg-destructive/10 border border-destructive/20 rounded-lg">
                <p className="text-sm text-destructive">{task.errorMessage}</p>
              </div>
            )}

            {/* Cancel Button */}
            {canCancelTask(task.status) && (
              <div className="mt-6">
                <button
                  onClick={handleCancelTask}
                  disabled={isCancelling}
                  className="w-full inline-flex items-center justify-center gap-2 rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-10 px-4 py-2"
                >
                  {isCancelling ? '取消中...' : '取消任务'}
                </button>
              </div>
            )}
          </div>

          {/* Video Player for completed tasks */}
          {isCompleted && task.videoUrl && (
            <div className="bg-card border border-border rounded-lg p-6">
              <h2 className="text-xl font-semibold text-foreground mb-4">生成的视频</h2>
              <VideoPlayer videoUrl={task.videoUrl} filename={task.filename} />
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
