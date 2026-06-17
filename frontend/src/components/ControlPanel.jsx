import React from 'react';
import { Sliders, Cpu, Eye, Image as ImageIcon } from 'lucide-react';

const ControlPanel = ({ config, updateConfig, engine, setEngine, languages, setLanguages, backendStatus, mergeBoxes, setMergeBoxes }) => {
  
  const handleSliderChange = (key, value) => {
    updateConfig({ [key]: value }, false); // Debounced preview for sliders
  };

  const handleCheckboxChange = (key, checked) => {
    updateConfig({ [key]: checked }, true); // Instant preview for checkboxes
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
    <div className="sidebar">
      {/* OCR Engine Selection */}
      <div className="glass-card">
        <h3 className="card-title">
          <Cpu size={18} />
          Cấu Hình OCR Engine
        </h3>
        <div className="config-group">
          <div className="control-item">
            <label className="control-label">Chọn OCR Engine</label>
            <select value={engine} onChange={(e) => setEngine(e.target.value)}>
              <option value="easyocr">EasyOCR (Deep Learning AI)</option>
              <option value="paddleocr" disabled={!backendStatus || !backendStatus.paddleocr_installed}>
                PaddleOCR (Baidu PP-OCRv5) {backendStatus && !backendStatus.paddleocr_installed ? ' (Chưa cài)' : ''}
              </option>
              <option value="vietocr" disabled={!backendStatus || !backendStatus.vietocr_installed}>
                VietOCR (Paddle Detector + VietOCR Rec) {backendStatus && !backendStatus.vietocr_installed ? ' (Chưa cài)' : ''}
              </option>
              <option value="paddle_structure" disabled={!backendStatus || !backendStatus.paddle_structure_installed}>
                PP-Structure V3 (Layout & Tables) {backendStatus && !backendStatus.paddle_structure_installed ? ' (Chưa cài)' : ''}
              </option>
            </select>
          </div>

          <div className="control-item">
            <label className="control-label">Ngôn Ngữ Nhận Diện</label>
            <div style={{ display: 'flex', gap: '1rem', marginTop: '0.25rem' }}>
              <label className="checkbox-label">
                <input 
                  type="checkbox" 
                  checked={languages.includes('vi')} 
                  onChange={() => toggleLanguage('vi')}
                />
                Tiếng Việt (vi)
              </label>
              <label className="checkbox-label">
                <input 
                  type="checkbox" 
                  checked={languages.includes('en')} 
                  onChange={() => toggleLanguage('en')}
                />
                Tiếng Anh (en)
              </label>
            </div>
          </div>

          <div className="control-item" style={{ marginTop: '0.5rem' }}>
            <label className="checkbox-label" style={{ fontWeight: 500, color: '#f3f4f6' }}>
              <input 
                type="checkbox" 
                checked={mergeBoxes} 
                onChange={(e) => setMergeBoxes(e.target.checked)}
              />
              Tự động gộp cụm chữ (Merge Boxes)
            </label>
          </div>
        </div>
      </div>

      {/* OpenCV Image Preprocessing Controls */}
      <div className="glass-card">
        <h3 className="card-title">
          <Sliders size={18} />
          Bộ Lọc Tiền Xử Lý (OpenCV)
        </h3>
        <div className="config-group">
          
          {/* Contrast & Brightness */}
          <div className="control-item">
            <div className="control-label">
              <span>Độ tương phản (Contrast)</span>
              <span className="label-val">x{config.contrast.toFixed(1)}</span>
            </div>
            <input 
              type="range" 
              min="0.5" 
              max="3.0" 
              step="0.1" 
              value={config.contrast} 
              onChange={(e) => handleSliderChange('contrast', parseFloat(e.target.value))} 
            />
          </div>

          <div className="control-item">
            <div className="control-label">
              <span>Độ sáng (Brightness)</span>
              <span className="label-val">{config.brightness > 0 ? `+${config.brightness}` : config.brightness}</span>
            </div>
            <input 
              type="range" 
              min="-100" 
              max="100" 
              step="5" 
              value={config.brightness} 
              onChange={(e) => handleSliderChange('brightness', parseInt(e.target.value))} 
            />
          </div>

          {/* Flatten & Deskew & Grayscale */}
          <div className="control-item" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', margin: '0.25rem 0' }}>
            <label className="checkbox-label" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <input 
                type="checkbox" 
                checked={config.auto_flatten} 
                onChange={(e) => handleCheckboxChange('auto_flatten', e.target.checked)} 
              />
              <span style={{ fontWeight: 600, color: '#a855f7' }}>✨ Trải phẳng phối cảnh (Auto-Flatten)</span>
            </label>

            <div style={{ display: 'flex', gap: '1.5rem' }}>
              <label className="checkbox-label" style={{ flex: 1 }}>
                <input 
                  type="checkbox" 
                  checked={config.grayscale} 
                  onChange={(e) => handleCheckboxChange('grayscale', e.target.checked)} 
                />
                Ảnh xám (Grayscale)
              </label>
              
              <label className="checkbox-label" style={{ flex: 1 }}>
                <input 
                  type="checkbox" 
                  checked={config.deskew} 
                  onChange={(e) => handleCheckboxChange('deskew', e.target.checked)} 
                />
                Thẳng chữ (Deskew)
              </label>
            </div>
          </div>

          {(engine === 'paddleocr' || engine === 'vietocr') && config.grayscale && (
            <div style={{ 
              fontSize: '0.75rem', 
              color: '#fbbf24', 
              background: 'rgba(245, 158, 11, 0.12)', 
              border: '1px solid rgba(245, 158, 11, 0.25)',
              padding: '0.65rem',
              borderRadius: '8px',
              marginTop: '0.75rem',
              lineHeight: '1.3'
            }}>
              ⚠️ <strong>Lưu ý:</strong> Paddle/VietOCR yêu cầu ảnh màu BGR 3 kênh. Hệ thống đã tự động đồng bộ lại số kênh màu đầu vào ở Backend để suy diễn chính xác.
            </div>
          )}

        </div>
      </div>
    </div>
  );
};

export default ControlPanel;
