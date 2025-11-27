/**
 * Task List Page - View and manage all tasks
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getTasks, deleteTask } from '@/services/taskService';
import { useUIStore } from '@/stores/uiStore';
import { formatRelativeTime } from '@/utils/format';
import { TaskStatus, type VideoTask } from '@/types';

export function TaskListPage() {
  const [selectedStatus, setSelectedStatus] = useState<TaskStatus | 'all'>('all');
  const [taskToDelete, setTaskToDelete] = useState<string | null>(null);
  const showToast = useUIStore((state) => state.showToast);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['tasks', selectedStatus],
    queryFn: async () => {
      const response = await getTasks({
        status: selectedStatus,
        sortBy: 'createdAt',
        order: 'desc',
      });
      if (response.success && response.data) {
        return response.data;
      }
      throw new Error(response.message || '获取任务列表失败');
    },
  });

  const handleDeleteTask = async (taskId: string) => {
    try {
      const response = await deleteTask(taskId);
      if (response.success) {
        showToast({
          type: 'success',
          message: '任务已删除',
        });
        refetch();
        setTaskToDelete(null);
      } else {
        throw new Error(response.message || '删除任务失败');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '删除任务失败';
      showToast({
        type: 'error',
        message: errorMessage,
      });
    }
  };

  const tasks = data?.tasks || [];
  const isEmpty = tasks.length === 0;

  const statusTabs = [
    { value: 'all' as const, label: '全部' },
    { value: TaskStatus.PROCESSING, label: '进行中' },
    { value: TaskStatus.COMPLETED, label: '已完成' },
    { value: TaskStatus.FAILED, label: '失败' },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-foreground">任务列表</h1>
              <p className="text-muted-foreground mt-2">管理所有视频生成任务</p>
            </div>
            <Link
              to="/"
              className="inline-flex items-center gap-2 rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              创建新任务
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        {/* Status Tabs */}
        <div className="flex gap-2 mb-6 border-b border-border">
          {statusTabs.map((tab) => (
            <button
              key={tab.value}
              onClick={() => setSelectedStatus(tab.value)}
              className={`
                px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px
                ${
                  selectedStatus === tab.value
                    ? 'border-primary text-primary'
                    : 'border-transparent text-muted-foreground hover:text-foreground'
                }
              `}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="text-center py-12">
            <div className="animate-spin h-12 w-12 border-4 border-primary border-t-transparent rounded-full mx-auto mb-4" />
            <p className="text-muted-foreground">加载中...</p>
          </div>
        )}

        {/* Empty State */}
        {!isLoading && isEmpty && (
          <div className="text-center py-12">
            <div className="w-24 h-24 mx-auto mb-6 rounded-full bg-muted flex items-center justify-center">
              <svg className="w-12 h-12 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold text-foreground mb-2">还没有任何任务</h3>
            <p className="text-muted-foreground mb-6">去创建第一个吧!</p>
            <Link
              to="/"
              className="inline-flex items-center justify-center gap-2 rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2"
            >
              开始创建
            </Link>
          </div>
        )}

        {/* Task Grid */}
        {!isLoading && !isEmpty && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {tasks.map((task) => (
              <TaskCard
                key={task.id}
                task={task}
                onDelete={() => setTaskToDelete(task.id)}
              />
            ))}
          </div>
        )}

        {/* Delete Confirmation Dialog */}
        {taskToDelete && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-card border border-border rounded-lg p-6 max-w-md mx-4">
              <h3 className="text-xl font-semibold text-foreground mb-4">确认删除</h3>
              <p className="text-muted-foreground mb-6">
                确定要删除这个任务吗?此操作无法撤销。
              </p>
              <div className="flex gap-3 justify-end">
                <button
                  onClick={() => setTaskToDelete(null)}
                  className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-10 px-4 py-2"
                >
                  取消
                </button>
                <button
                  onClick={() => handleDeleteTask(taskToDelete)}
                  className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 bg-destructive text-destructive-foreground hover:bg-destructive/90 h-10 px-4 py-2"
                >
                  删除
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

interface TaskCardProps {
  task: VideoTask;
  onDelete: () => void;
}

function TaskCard({ task, onDelete }: TaskCardProps) {
  const canDelete = [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED].includes(task.status);

  return (
    <Link to={`/tasks/${task.id}`} className="block">
      <div className="bg-card border border-border rounded-lg p-5 hover:shadow-md transition-shadow h-full flex flex-col">
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <h3 className="font-semibold text-foreground truncate flex-1 mr-2">{task.filename}</h3>
          <span
            className={`
              px-2 py-1 rounded text-xs font-medium flex-shrink-0
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

        {/* Progress */}
        {task.status === TaskStatus.PROCESSING && (
          <div className="mb-3">
            <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
              <span>进度</span>
              <span>{Math.round(task.progress)}%</span>
            </div>
            <div className="w-full h-1.5 bg-secondary rounded-full overflow-hidden">
              <div
                className="h-full bg-primary transition-all duration-300"
                style={{ width: `${task.progress}%` }}
              />
            </div>
          </div>
        )}

        {/* Info */}
        <div className="text-sm text-muted-foreground space-y-1 flex-1">
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{formatRelativeTime(task.createdAt)}</span>
          </div>
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
            </svg>
            <span>{task.subtitleTemplate}</span>
          </div>
        </div>

        {/* Actions */}
        {canDelete && (
          <div className="mt-4 pt-4 border-t border-border">
            <button
              onClick={(e) => {
                e.preventDefault();
                onDelete();
              }}
              className="w-full inline-flex items-center justify-center gap-2 rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 border border-destructive/20 text-destructive hover:bg-destructive/10 h-9 px-3"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
              删除
            </button>
          </div>
        )}
      </div>
    </Link>
  );
}
