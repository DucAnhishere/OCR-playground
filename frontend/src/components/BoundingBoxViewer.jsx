import React, { useState, useEffect, useRef } from 'react';
import { RefreshCw, Crop, Image as ImageIcon } from 'lucide-react';

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

  useEffect(() => {
    window.addEventListener('resize', updateScaleFactors);
    return () => window.removeEventListener('resize', updateScaleFactors);
  }, []);

  useEffect(() => {
    const timer = setTimeout(updateScaleFactors, 100);
    return () => clearTimeout(timer);
  }, [processedImage, results]);

  return (
    <div className="flex flex-col gap-4 w-full h-full relative group">
      
      {/* Header Overlay */}
      <div className="absolute top-4 left-4 right-4 z-20 flex justify-between items-center pointer-events-none">
        <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-black/40 backdrop-blur-md border border-white/10 pointer-events-auto shadow-lg">
          <Crop className="w-4 h-4 text-cyan-400" />
          <h3 className="text-sm font-semibold text-white tracking-wide">Interactive Canvas</h3>
        </div>
        
        {results.length > 0 && (
          <div className="px-3 py-1.5 rounded-lg bg-purple-500/20 border border-purple-500/30 backdrop-blur-md pointer-events-auto">
            <span className="text-xs font-bold text-purple-300">
              {results.length} blocks detected
            </span>
          </div>
        )}
      </div>

      <div className="relative w-full h-full min-h-[600px] flex items-center justify-center rounded-2xl overflow-hidden" ref={containerRef}>
        
        {/* Loading Overlay */}
        {loading && (
          <div className="absolute inset-0 z-30 bg-black/60 backdrop-blur-sm flex flex-col items-center justify-center">
            <RefreshCw className="w-12 h-12 text-purple-500 animate-spin mb-4" />
            <p className="font-semibold text-purple-300 tracking-wide">Processing Document Matrix...</p>
          </div>
        )}

        {processedImage ? (
          <div className="relative inline-block max-w-full max-h-full transition-transform duration-700 group-hover:scale-[1.01]">
            <img 
              ref={imageRef}
              src={processedImage} 
              alt="OCR Work" 
              onLoad={updateScaleFactors}
              className="block max-w-full max-h-[80vh] object-contain rounded-xl shadow-2xl"
            />
            
            {/* Active scanline animation if loading */}
            {loading && <div className="scanline-effect rounded-xl overflow-hidden"></div>}

            {/* Bounding Box Markers layer */}
            {!loading && results && results.length > 0 && (
              <div 
                className="absolute top-0 left-0 pointer-events-none" 
                style={{ width: `${imgDimensions.width}px`, height: `${imgDimensions.height}px` }}
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
                      className={`absolute pointer-events-auto cursor-pointer transition-all duration-300 ease-out border-2 ${
                        isHighlighted 
                          ? 'border-emerald-400 bg-emerald-400/20 z-20 shadow-[0_0_20px_rgba(16,185,129,0.5)] scale-110' 
                          : 'border-purple-500/50 bg-purple-500/10 hover:border-cyan-400 hover:bg-cyan-400/20 hover:z-10 hover:shadow-[0_0_15px_rgba(6,182,212,0.4)]'
                      }`}
                      style={{
                        left: `${left}px`,
                        top: `${top}px`,
                        width: `${width}px`,
                        height: `${height}px`,
                        borderRadius: '4px'
                      }}
                      onMouseEnter={() => setActiveWordIndex(index)}
                      onMouseLeave={() => setActiveWordIndex(null)}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedWordIndex && setSelectedWordIndex(index);
                      }}
                      title={`Text: "${item.text}" | Confidence: ${item.confidence}%`}
                    />
                  );
                })}
              </div>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center text-zinc-600 gap-4">
            <ImageIcon className="w-16 h-16 opacity-20" />
            <p className="text-sm font-medium">Awaiting document upload</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default BoundingBoxViewer;
