/**
 * Progress bar component with phase indicator
 */

import { TaskPhase } from '@/types';
import { formatProgress } from '@/utils/format';

interface ProgressBarProps {
  progress: number;
  currentPhase?: TaskPhase;
}

const PHASE_LABELS: Record<TaskPhase, string> = {
  [TaskPhase.MATERIAL_PROCESSING]: '素材处理',
  [TaskPhase.MATERIAL_ANALYSIS]: '素材分析',
  [TaskPhase.SCRIPT_GENERATION]: '脚本生成',
  [TaskPhase.VIDEO_GENERATION]: '视频生成',
};

export function ProgressBar({ progress, currentPhase }: ProgressBarProps) {
  return (
    <div className="w-full">
      {/* Progress Info */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-foreground">
          {currentPhase ? PHASE_LABELS[currentPhase] : '准备中...'}
        </span>
        <span className="text-sm font-bold text-primary">{formatProgress(progress)}</span>
      </div>

      {/* Progress Bar */}
      <div className="w-full h-3 bg-secondary rounded-full overflow-hidden">
        <div
          className="h-full bg-primary transition-all duration-500 ease-out"
          style={{ width: `${Math.min(progress, 100)}%` }}
        />
      </div>

      {/* Phase Indicators */}
      {currentPhase && (
        <div className="mt-4 grid grid-cols-4 gap-2">
          {Object.entries(PHASE_LABELS).map(([phase, label]) => {
            const phaseValue = phase as TaskPhase;
            const isActive = currentPhase === phaseValue;
            const isCompleted = getPhaseProgress(currentPhase) > getPhaseProgress(phaseValue);

            return (
              <div
                key={phase}
                className={`
                  text-center p-2 rounded-md text-xs
                  ${isActive ? 'bg-primary/10 text-primary font-medium' : ''}
                  ${isCompleted ? 'bg-primary/5 text-muted-foreground' : ''}
                  ${!isActive && !isCompleted ? 'text-muted-foreground/50' : ''}
                `}
              >
                {isCompleted && '✓ '}
                {label}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function getPhaseProgress(phase: TaskPhase): number {
  const phaseMap: Record<TaskPhase, number> = {
    [TaskPhase.MATERIAL_PROCESSING]: 0,
    [TaskPhase.MATERIAL_ANALYSIS]: 25,
    [TaskPhase.SCRIPT_GENERATION]: 50,
    [TaskPhase.VIDEO_GENERATION]: 75,
  };
  return phaseMap[phase] || 0;
}
