import React from 'react';
import { Sliders, Cpu } from 'lucide-react';

const ControlPanel = ({ config, updateConfig, engine, setEngine, languages, setLanguages, backendStatus, mergeBoxes, setMergeBoxes }) => {
  
  const handleSliderChange = (key, value) => {
    updateConfig({ [key]: value }, false); 
  };

  const handleCheckboxChange = (key, checked) => {
    updateConfig({ [key]: checked }, true); 
  };

  const toggleLanguage = (langCode) => {
    if (languages.includes(langCode)) {
      if (languages.length > 1) {
        setLanguages(languages.filter(l => l !== langCode));
      }
    } else {
      setLanguages([...languages, langCode]);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      
      {/* OCR Engine Selection */}
      <div className="flex flex-col gap-4">
        <h3 className="flex items-center gap-2 text-white font-semibold border-b border-white/5 pb-2">
          <Cpu className="text-purple-400 w-5 h-5" />
          OCR Engine Config
        </h3>
        
        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-2">
            <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Select Engine</label>
            <select 
              className="w-full bg-white/5 border border-white/10 rounded-xl p-3 text-sm text-white outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/50 transition-all appearance-none cursor-pointer"
              value={engine} 
              onChange={(e) => setEngine(e.target.value)}
            >
              <option value="easyocr" className="bg-zinc-900">EasyOCR (Deep Learning)</option>
              <option value="paddleocr" disabled={!backendStatus || !backendStatus.paddleocr_installed} className="bg-zinc-900">
                PaddleOCR {backendStatus && !backendStatus.paddleocr_installed ? '(Not installed)' : ''}
              </option>
              <option value="vietocr" disabled={!backendStatus || !backendStatus.vietocr_installed} className="bg-zinc-900">
                VietOCR {backendStatus && !backendStatus.vietocr_installed ? '(Not installed)' : ''}
              </option>
              <option value="paddle_structure" disabled={!backendStatus || !backendStatus.paddle_structure_installed} className="bg-zinc-900">
                PP-Structure V3 {backendStatus && !backendStatus.paddle_structure_installed ? '(Not installed)' : ''}
              </option>
            </select>
          </div>

          <div className="flex flex-col gap-2">
            <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Languages</label>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 cursor-pointer group">
                <div className={`w-5 h-5 rounded flex items-center justify-center border transition-all ${languages.includes('vi') ? 'bg-gradient-to-br from-purple-500 to-cyan-400 border-transparent' : 'border-white/20 bg-white/5 group-hover:border-purple-500/50'}`}>
                  {languages.includes('vi') && <span className="text-white text-xs font-bold">✓</span>}
                </div>
                <input type="checkbox" className="hidden" checked={languages.includes('vi')} onChange={() => toggleLanguage('vi')} />
                <span className="text-sm text-zinc-300">Vietnamese</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer group">
                <div className={`w-5 h-5 rounded flex items-center justify-center border transition-all ${languages.includes('en') ? 'bg-gradient-to-br from-purple-500 to-cyan-400 border-transparent' : 'border-white/20 bg-white/5 group-hover:border-purple-500/50'}`}>
                  {languages.includes('en') && <span className="text-white text-xs font-bold">✓</span>}
                </div>
                <input type="checkbox" className="hidden" checked={languages.includes('en')} onChange={() => toggleLanguage('en')} />
                <span className="text-sm text-zinc-300">English</span>
              </label>
            </div>
          </div>

          <div className="mt-2">
            <label className="flex items-center gap-2 cursor-pointer group">
              <div className={`w-5 h-5 rounded flex items-center justify-center border transition-all ${mergeBoxes ? 'bg-gradient-to-br from-purple-500 to-cyan-400 border-transparent' : 'border-white/20 bg-white/5 group-hover:border-cyan-500/50'}`}>
                {mergeBoxes && <span className="text-white text-xs font-bold">✓</span>}
              </div>
              <input type="checkbox" className="hidden" checked={mergeBoxes} onChange={(e) => setMergeBoxes(e.target.checked)} />
              <span className="text-sm font-medium text-zinc-200">Merge Adjacent Boxes</span>
            </label>
          </div>
        </div>
      </div>

      {/* OpenCV Filters */}
      <div className="flex flex-col gap-4 mt-2">
        <h3 className="flex items-center gap-2 text-white font-semibold border-b border-white/5 pb-2">
          <Sliders className="text-cyan-400 w-5 h-5" />
          Pre-processing Filters
        </h3>
        
        <div className="flex flex-col gap-5">
          {/* Contrast */}
          <div className="flex flex-col gap-2">
            <div className="flex justify-between items-center text-sm">
              <span className="text-zinc-400 font-medium">Contrast</span>
              <span className="font-mono text-cyan-400">x{config.contrast.toFixed(1)}</span>
            </div>
            <input 
              type="range" 
              className="w-full h-1.5 bg-white/10 rounded-full appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:bg-gradient-to-br [&::-webkit-slider-thumb]:from-purple-500 [&::-webkit-slider-thumb]:to-cyan-400 [&::-webkit-slider-thumb]:rounded-full hover:[&::-webkit-slider-thumb]:scale-125 transition-all"
              min="0.5" max="3.0" step="0.1" 
              value={config.contrast} 
              onChange={(e) => handleSliderChange('contrast', parseFloat(e.target.value))} 
            />
          </div>

          {/* Brightness */}
          <div className="flex flex-col gap-2">
            <div className="flex justify-between items-center text-sm">
              <span className="text-zinc-400 font-medium">Brightness</span>
              <span className="font-mono text-cyan-400">{config.brightness > 0 ? `+${config.brightness}` : config.brightness}</span>
            </div>
            <input 
              type="range" 
              className="w-full h-1.5 bg-white/10 rounded-full appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:bg-gradient-to-br [&::-webkit-slider-thumb]:from-purple-500 [&::-webkit-slider-thumb]:to-cyan-400 [&::-webkit-slider-thumb]:rounded-full hover:[&::-webkit-slider-thumb]:scale-125 transition-all"
              min="-100" max="100" step="5" 
              value={config.brightness} 
              onChange={(e) => handleSliderChange('brightness', parseInt(e.target.value))} 
            />
          </div>

          {/* Toggles */}
          <div className="flex flex-col gap-4">
            <label className="flex items-center gap-3 cursor-pointer group p-3 rounded-xl bg-purple-500/5 border border-purple-500/20 hover:bg-purple-500/10 transition-colors">
              <div className={`w-5 h-5 rounded flex items-center justify-center border transition-all ${config.auto_flatten ? 'bg-purple-500 border-transparent shadow-[0_0_10px_rgba(168,85,247,0.5)]' : 'border-purple-500/30 bg-transparent'}`}>
                {config.auto_flatten && <span className="text-white text-xs font-bold">✓</span>}
              </div>
              <input type="checkbox" className="hidden" checked={config.auto_flatten} onChange={(e) => handleCheckboxChange('auto_flatten', e.target.checked)} />
              <span className="text-sm font-bold text-purple-300">✨ Auto-Flatten</span>
            </label>

            <div className="flex gap-4">
              <label className="flex items-center gap-2 cursor-pointer group flex-1">
                <div className={`w-4 h-4 rounded flex items-center justify-center border transition-all ${config.grayscale ? 'bg-zinc-400 border-transparent' : 'border-white/20 bg-white/5'}`}>
                  {config.grayscale && <span className="text-zinc-950 text-[10px] font-bold">✓</span>}
                </div>
                <input type="checkbox" className="hidden" checked={config.grayscale} onChange={(e) => handleCheckboxChange('grayscale', e.target.checked)} />
                <span className="text-sm text-zinc-400">Grayscale</span>
              </label>
              
              <label className="flex items-center gap-2 cursor-pointer group flex-1">
                <div className={`w-4 h-4 rounded flex items-center justify-center border transition-all ${config.deskew ? 'bg-cyan-500 border-transparent' : 'border-white/20 bg-white/5'}`}>
                  {config.deskew && <span className="text-white text-[10px] font-bold">✓</span>}
                </div>
                <input type="checkbox" className="hidden" checked={config.deskew} onChange={(e) => handleCheckboxChange('deskew', e.target.checked)} />
                <span className="text-sm text-zinc-400">Deskew</span>
              </label>
            </div>
          </div>

          {(engine === 'paddleocr' || engine === 'vietocr') && config.grayscale && (
            <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs text-amber-400/80 mt-2 leading-relaxed">
              ⚠️ <strong>Notice:</strong> Paddle/VietOCR requires 3-channel BGR images. The backend has auto-converted this to prevent engine failures.
            </div>
          )}

        </div>
      </div>

    </div>
  );
};

export default ControlPanel;
