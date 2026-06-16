import React, { useState, useEffect, useRef } from 'react';
import { RefreshCw, Crop } from 'lucide-react';

const BoundingBoxViewer = ({ 
  originalImage, 
  processedImage, 
  results, 
  loading, 
  activeWordIndex, 
  setActiveWordIndex,
  selectedWordIndex,
  setSelectedWordIndex
}) => {
  const containerRef = useRef(null);
  const imageRef = useRef(null);
  const [scale, setScale] = useState({ x: 1, y: 1 });
  const [imgDimensions, setImgDimensions] = useState({ width: 0, height: 0 });

  // Recalculate scaling ratios when image loads or window resizes
  const updateScaleFactors = () => {
    if (imageRef.current) {
      const renderedWidth = imageRef.current.clientWidth;
      const renderedHeight = imageRef.current.clientHeight;
      const naturalWidth = imageRef.current.naturalWidth;
      const naturalHeight = imageRef.current.naturalHeight;

      if (naturalWidth && naturalHeight) {
        setScale({
          x: renderedWidth / naturalWidth,
          y: renderedHeight / naturalHeight
        });
        setImgDimensions({
          width: renderedWidth,
          height: renderedHeight
        });
      }
    }
  };

  // Re-run scaling calculations on window resize
  useEffect(() => {
    window.addEventListener('resize', updateScaleFactors);
    return () => window.removeEventListener('resize', updateScaleFactors);
  }, []);

  // Update scale factors when processed image or results change
  useEffect(() => {
    // Small timeout to let browser layout finalize before measurement
    const timer = setTimeout(updateScaleFactors, 100);
    return () => clearTimeout(timer);
  }, [processedImage, results]);

  return (
    <div className="viewer-card">
      <div className="viewer-header">
        <h3 className="viewer-title">
          <Crop size={18} style={{ color: '#06b6d4' }} />
          Trực Quan Hóa Khung Chữ (Interactive Canvas)
        </h3>
        {results.length > 0 && (
          <span className="badge-info">
            Phát hiện {results.length} ký tự/từ
          </span>
        )}
      </div>

      <div className="image-canvas-container" ref={containerRef}>
        {/* Loading Overlay */}
        {loading && (
          <div className="loading-spinner-overlay">
            <div className="spinner"></div>
            <p style={{ fontWeight: 600, color: '#a855f7' }}>Đang chạy AI nhận dạng chữ...</p>
          </div>
        )}

        {/* Display Image (Always show processed or original fallback) */}
        {processedImage ? (
          <div style={{ position: 'relative', display: 'inline-block' }}>
            <img 
              ref={imageRef}
              src={processedImage} 
              alt="OCR Work" 
              onLoad={updateScaleFactors}
              style={{ display: 'block' }}
            />
            
            {/* Active scanline animation if loading */}
            {loading && <div className="scanline-effect"></div>}

            {/* Bounding Box Markers layer */}
            {!loading && results && results.length > 0 && (
              <div 
                className="bbox-overlay-layer" 
                style={{ 
                  position: 'absolute', 
                  top: 0, 
                  left: 0, 
                  width: `${imgDimensions.width}px`, 
                  height: `${imgDimensions.height}px` 
                }}
              >
                {results.map((item, index) => {
                  const left = item.box.x * scale.x;
                  const top = item.box.y * scale.y;
                  const width = item.box.w * scale.x;
                  const height = item.box.h * scale.y;
                  const isHighlighted = activeWordIndex === index || selectedWordIndex === index;
                  
                  return (
                    <div 
                      key={index}
                      className={`bbox-marker ${isHighlighted ? 'active' : ''}`}
                      style={{
                        left: `${left}px`,
                        top: `${top}px`,
                        width: `${width}px`,
                        height: `${height}px`
                      }}
                      onMouseEnter={() => setActiveWordIndex(index)}
                      onMouseLeave={() => setActiveWordIndex(null)}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedWordIndex && setSelectedWordIndex(index);
                      }}
                      title={`Chữ: "${item.text}" | Độ tin cậy: ${item.confidence}%`}
                    />
                  );
                })}
              </div>
            )}
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: '#9ca3af', gap: '0.5rem' }}>
            <ImageIcon size={40} style={{ opacity: 0.3 }} />
            <p>Tải ảnh lên ở tab trên để xem trước OpenCV và chạy OCR</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default BoundingBoxViewer;
