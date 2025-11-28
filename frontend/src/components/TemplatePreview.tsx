/**
 * 字幕模板预览组件
 * 使用CSS动态生成各模板的视觉效果预览
 */

import type { SubtitleTemplate } from '@/types';

interface TemplatePreviewProps {
  templateId: SubtitleTemplate;
  animated?: boolean;
}

// 模板样式定义 - 基于后端PyCaps模板的CSS样式
const TEMPLATE_STYLES: Record<SubtitleTemplate, {
  container: React.CSSProperties;
  word: React.CSSProperties;
  wordActive: React.CSSProperties;
}> = {
  hype: {
    container: {
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px'
    },
    word: {
      fontFamily: '"Comic Sans MS", cursive',
      fontSize: '20px',
      fontWeight: 800,
      color: '#DDDDDD',
      textShadow: '-2px -2px 0 #000, 2px -2px 0 #000, -2px 2px 0 #000, 2px 2px 0 #000, 3px 3px 5px rgba(0,0,0,0.5)',
      padding: '3px 5px',
      display: 'inline-block',
      marginRight: '4px'
    },
    wordActive: {
      color: '#FFFF00',
      transform: 'scale(1.1)',
      transition: 'all 0.2s ease'
    }
  },

  minimalist: {
    container: {
      background: 'linear-gradient(135deg, #434343 0%, #000000 100%)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px'
    },
    word: {
      fontFamily: '"Helvetica Neue", "Arial", sans-serif',
      fontSize: '14px',
      color: 'rgba(255, 255, 255, 0.7)',
      backgroundColor: 'rgba(0, 0, 0, 0.6)',
      padding: '4px 5px',
      textShadow: '1px 1px 2px rgba(0,0,0,0.8)',
      display: 'inline-block'
    },
    wordActive: {
      color: '#FFFFFF',
      transition: 'color 0.2s ease'
    }
  },

  explosive: {
    container: {
      background: 'linear-gradient(135deg, #FF512F 0%, #DD2476 100%)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px'
    },
    word: {
      fontFamily: 'Impact, sans-serif',
      fontSize: '24px',
      fontWeight: 'bold',
      color: '#FFDD00',
      textShadow: '0 0 3px #FF8800, 0 0 6px #FF8800, 0 0 9px #FF4400, 1px 1px 1px #000000',
      padding: '5px 8px',
      display: 'inline-block',
      marginRight: '4px'
    },
    wordActive: {
      color: '#FFFFFF',
      textShadow: '0 0 4px #FFAA00, 0 0 8px #FF8800, 0 0 12px #FF0000, 0 0 20px #FF0000, 1px 1px 1px #000000',
      transform: 'scale(1.15)',
      transition: 'all 0.3s ease'
    }
  },

  vibrant: {
    container: {
      background: 'linear-gradient(135deg, #00C9FF 0%, #92FE9D 100%)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px'
    },
    word: {
      fontFamily: 'Impact, sans-serif',
      fontSize: '24px',
      fontWeight: 900,
      color: 'white',
      textShadow: '-1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000, 2px 2px 0 #FF00FF, -2px -2px 0 #00FFFF',
      padding: '4px 6px',
      display: 'inline-block',
      marginRight: '4px'
    },
    wordActive: {
      transform: 'scale(1.1) rotate(-2deg)',
      transition: 'all 0.2s ease'
    }
  },

  classic: {
    container: {
      background: 'linear-gradient(135deg, #2C3E50 0%, #34495E 100%)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px'
    },
    word: {
      fontFamily: 'Georgia, serif',
      fontSize: '18px',
      color: '#ECF0F1',
      textShadow: '2px 2px 4px rgba(0,0,0,0.8)',
      padding: '4px 6px',
      display: 'inline-block',
      marginRight: '4px'
    },
    wordActive: {
      color: '#3498DB',
      fontWeight: 'bold',
      transition: 'all 0.2s ease'
    }
  },

  fast: {
    container: {
      background: 'linear-gradient(135deg, #F09819 0%, #EDDE5D 100%)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px'
    },
    word: {
      fontFamily: 'Arial, sans-serif',
      fontSize: '16px',
      fontWeight: 'bold',
      color: '#2C3E50',
      padding: '2px 4px',
      display: 'inline-block',
      marginRight: '2px'
    },
    wordActive: {
      color: '#E74C3C',
      transform: 'skewX(-5deg)',
      transition: 'all 0.1s ease'
    }
  },

  'line-focus': {
    container: {
      background: 'linear-gradient(135deg, #232526 0%, #414345 100%)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px'
    },
    word: {
      fontFamily: 'Arial, sans-serif',
      fontSize: '16px',
      color: 'rgba(255, 255, 255, 0.5)',
      padding: '3px 5px',
      display: 'inline-block',
      marginRight: '4px'
    },
    wordActive: {
      color: '#FFFFFF',
      backgroundColor: 'rgba(52, 152, 219, 0.3)',
      borderLeft: '3px solid #3498DB',
      paddingLeft: '8px',
      transition: 'all 0.2s ease'
    }
  },

  model: {
    container: {
      background: 'linear-gradient(135deg, #8E2DE2 0%, #4A00E0 100%)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px'
    },
    word: {
      fontFamily: '"Courier New", monospace',
      fontSize: '16px',
      color: '#00FF00',
      backgroundColor: 'rgba(0, 0, 0, 0.7)',
      padding: '4px 6px',
      display: 'inline-block',
      marginRight: '4px',
      borderRadius: '2px'
    },
    wordActive: {
      color: '#00FFFF',
      boxShadow: '0 0 10px #00FFFF',
      transition: 'all 0.2s ease'
    }
  },

  'neo-minimal': {
    container: {
      background: 'linear-gradient(135deg, #FFFFFF 0%, #ECE9E6 100%)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px'
    },
    word: {
      fontFamily: '"SF Pro Display", system-ui, sans-serif',
      fontSize: '16px',
      color: '#1A1A1A',
      padding: '3px 6px',
      display: 'inline-block',
      marginRight: '4px'
    },
    wordActive: {
      color: '#007AFF',
      borderBottom: '2px solid #007AFF',
      transition: 'all 0.2s ease'
    }
  },

  'retro-gaming': {
    container: {
      background: 'linear-gradient(135deg, #000000 0%, #1A1A1A 100%)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px'
    },
    word: {
      fontFamily: '"Press Start 2P", "Courier New", monospace',
      fontSize: '12px',
      color: '#00FF00',
      textShadow: '0 0 5px #00FF00, 2px 2px 0 #003300',
      padding: '6px 8px',
      display: 'inline-block',
      marginRight: '6px'
    },
    wordActive: {
      color: '#FFFF00',
      textShadow: '0 0 10px #FFFF00, 2px 2px 0 #333300',
      animation: 'blink 0.5s infinite',
      transition: 'all 0.2s ease'
    }
  },

  'word-focus': {
    container: {
      background: 'linear-gradient(135deg, #1E3C72 0%, #2A5298 100%)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px'
    },
    word: {
      fontFamily: 'Arial, sans-serif',
      fontSize: '18px',
      color: 'rgba(255, 255, 255, 0.4)',
      padding: '4px 6px',
      display: 'inline-block',
      marginRight: '4px',
      filter: 'blur(1px)'
    },
    wordActive: {
      color: '#FFFFFF',
      fontSize: '22px',
      fontWeight: 'bold',
      filter: 'blur(0px)',
      textShadow: '0 0 8px rgba(255, 255, 255, 0.8)',
      transform: 'scale(1.2)',
      transition: 'all 0.3s ease'
    }
  },

  default: {
    container: {
      background: 'linear-gradient(135deg, #4B6CB7 0%, #182848 100%)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px'
    },
    word: {
      fontFamily: 'Arial, sans-serif',
      fontSize: '16px',
      color: '#FFFFFF',
      textShadow: '1px 1px 2px rgba(0,0,0,0.8)',
      padding: '4px 6px',
      display: 'inline-block',
      marginRight: '4px'
    },
    wordActive: {
      fontWeight: 'bold',
      transition: 'all 0.2s ease'
    }
  }
};

export function TemplatePreview({ templateId, animated = false }: TemplatePreviewProps) {
  const styles = TEMPLATE_STYLES[templateId] || TEMPLATE_STYLES.default;
  const demoText = ['创建', '精彩', '视频'];

  return (
    <div
      className="w-full h-full rounded-md overflow-hidden"
      style={styles.container}
    >
      <div className="text-center">
        {demoText.map((word, index) => (
          <span
            key={index}
            style={{
              ...styles.word,
              ...(animated && index === 1 ? styles.wordActive : {})
            }}
          >
            {word}
          </span>
        ))}
      </div>

      <style>{`
        @keyframes blink {
          0%, 49% { opacity: 1; }
          50%, 100% { opacity: 0.5; }
        }
      `}</style>
    </div>
  );
}
