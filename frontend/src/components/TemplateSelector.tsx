/**
 * Subtitle template selector component
 */

import { useState } from 'react';
import { useTaskStore } from '@/stores/taskStore';
import { SUBTITLE_TEMPLATES } from '@/utils/constants';
import { TemplatePreview } from './TemplatePreview';
import type { SubtitleTemplate } from '@/types';

interface TemplateSelectorProps {
  onTemplateSelect?: (template: SubtitleTemplate) => void;
}

export function TemplateSelector({ onTemplateSelect }: TemplateSelectorProps) {
  const selectedTemplate = useTaskStore((state) => state.selectedTemplate);
  const setSelectedTemplate = useTaskStore((state) => state.setSelectedTemplate);
  const [hoveredTemplate, setHoveredTemplate] = useState<SubtitleTemplate | null>(null);

  const handleSelect = (templateId: SubtitleTemplate) => {
    setSelectedTemplate(templateId);
    if (onTemplateSelect) {
      onTemplateSelect(templateId);
    }
  };

  return (
    <div className="w-full">
      <h3 className="text-lg font-semibold text-foreground mb-4">选择字幕模板</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {SUBTITLE_TEMPLATES.map((template) => (
          <div
            key={template.id}
            className={`
              relative border-2 rounded-lg p-4 cursor-pointer transition-all
              ${
                selectedTemplate === template.id
                  ? 'border-primary bg-primary/5 shadow-md'
                  : 'border-border hover:border-primary/50 hover:shadow-sm'
              }
            `}
            onClick={() => handleSelect(template.id)}
            onMouseEnter={() => setHoveredTemplate(template.id)}
            onMouseLeave={() => setHoveredTemplate(null)}
          >
            {/* Selected Indicator */}
            {selectedTemplate === template.id && (
              <div className="absolute top-2 right-2 w-6 h-6 bg-primary rounded-full flex items-center justify-center z-10">
                <svg
                  className="w-4 h-4 text-primary-foreground"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={3}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              </div>
            )}

            {/* Template Preview - CSS Dynamic Rendering */}
            <div className="aspect-video rounded-md mb-3 overflow-hidden">
              <TemplatePreview
                templateId={template.id}
                animated={hoveredTemplate === template.id}
              />
            </div>

            {/* Template Info */}
            <div>
              <h4 className="font-semibold text-foreground mb-1">{template.name}</h4>
              <p className="text-sm text-muted-foreground">{template.description}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
