/**
 * Video player component with download button
 */

interface VideoPlayerProps {
  videoUrl: string;
  filename?: string;
  onPlay?: () => void;
}

export function VideoPlayer({ videoUrl, filename, onPlay }: VideoPlayerProps) {
  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = videoUrl;
    link.download = filename || 'video.mp4';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="w-full">
      {/* Video Player */}
      <div className="relative bg-black rounded-lg overflow-hidden mb-4">
        <video
          src={videoUrl}
          controls
          className="w-full h-auto"
          onPlay={onPlay}
          onError={(e) => {
            console.error('Video playback error:', e);
          }}
        >
          您的浏览器不支持视频播放。
        </video>
      </div>

      {/* Download Button */}
      <button
        onClick={handleDownload}
        className="w-full inline-flex items-center justify-center gap-2 rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2"
      >
        <svg
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
          />
        </svg>
        下载视频
      </button>
    </div>
  );
}
