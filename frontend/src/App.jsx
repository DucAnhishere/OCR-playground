import React, { useState, useEffect } from 'react';
import { 
  Upload, Play, RefreshCw, Cpu, Layers, BookOpen, 
  Settings2, FileText, CheckCircle2, AlertCircle, Sparkles
} from 'lucide-react';

import ControlPanel from './components/ControlPanel';
import BoundingBoxViewer from './components/BoundingBoxViewer';
import './App.css';

const API_BASE = "http://127.0.0.1:8000/api";

function App() {
  // Image states
  const [originalFile, setOriginalFile] = useState(null); // File object
  const [originalImage, setOriginalImage] = useState(null); // base64 (for live preview)
  const [processedImage, setProcessedImage] = useState(null); // base64 or URL
  
  // OCR and Processing configurations
  const [config, setConfig] = useState({
    auto_flatten: false,
    grayscale: false,
    contrast: 1.0,
    brightness: 0,
    deskew: false,
    threshold_method: 'none', // default to no binarization
    threshold_val: 127,
    adaptive_block_size: 11,
    adaptive_c: 2,
    morphology_op: 'none',
    morphology_kernel: 3,
    morphology_iterations: 1,
  });

  const debounceTimerRef = React.useRef(null);

  const updateConfigAndPreview = (updatedFields, instant = false) => {
    setConfig(prev => {
      const newConfig = { ...prev, ...updatedFields };
      
      // Clear previous OCR results to avoid coordinates misalignment
      setResults([]);
      setSelectedWordIndex(null);
      setDetectedTables([]);
      setExecutionStats(null);

      // Clear any existing debounce timer
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }

      if (instant) {
        requestPreprocessingPreview(newConfig);
      } else {
        debounceTimerRef.current = setTimeout(() => {
          requestPreprocessingPreview(newConfig);
        }, 300);
      }

      return newConfig;
    });
  };

  const [engine, setEngine] = useState('easyocr');
  const [languages, setLanguages] = useState(['vi', 'en']);
  const [mergeBoxes, setMergeBoxes] = useState(true);

  // Results & stats
  const [results, setResults] = useState([]);
  const [detectedTables, setDetectedTables] = useState([]);
  const [executionStats, setExecutionStats] = useState(null);
  const [activeWordIndex, setActiveWordIndex] = useState(null);
  const [selectedWordIndex, setSelectedWordIndex] = useState(null);
  const [previewMetadata, setPreviewMetadata] = useState({});

  // Auto-scroll sidebar list to show the hovered or selected word card
  useEffect(() => {
    const targetIndex = activeWordIndex !== null ? activeWordIndex : selectedWordIndex;
    if (targetIndex !== null) {
      const element = document.getElementById(`word-card-${targetIndex}`);
      if (element) {
        element.scrollIntoView({
          behavior: 'smooth',
          block: 'nearest'
        });
      }
    }
  }, [activeWordIndex, selectedWordIndex]);

  // App statuses
  const [loading, setLoading] = useState(false);
  const [backendStatus, setBackendStatus] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);

  // Poll backend status and default config on mount
  useEffect(() => {
    fetchBackendStatus();
    fetchDefaultConfig();
  }, []);

  // Request preprocessing live preview instantly when a new image is loaded
  useEffect(() => {
    if (originalImage) {
      requestPreprocessingPreview(config);
    }
  }, [originalImage]);

  const fetchBackendStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/status`);
      if (res.ok) {
        const data = await res.json();
        setBackendStatus(data);
      } else {
        setBackendStatus(null);
      }
    } catch (e) {
      console.error("Backend status check failed", e);
      setBackendStatus(null);
    }
  };

  const fetchDefaultConfig = async () => {
    try {
      const res = await fetch(`${API_BASE}/config/default`);
      if (res.ok) {
        const data = await res.json();
        setConfig(data);
      }
    } catch (e) {
      console.error("Failed to fetch default config from backend", e);
    }
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      setOriginalFile(file);
      const reader = new FileReader();
      reader.onload = (event) => {
        setOriginalImage(event.target.result);
        setProcessedImage(event.target.result);
        setResults([]);
        setSelectedWordIndex(null);
        setDetectedTables([]);
        setExecutionStats(null);
        setErrorMessage(null);
        setPreviewMetadata({});
      };
      reader.readAsDataURL(file);
    }
  };



  const requestPreprocessingPreview = async (currentConfig = null) => {
    if (!originalImage) return;
    const targetConfig = currentConfig || config;
    try {
      const res = await fetch(`${API_BASE}/preprocess`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          image: originalImage,
          config: targetConfig
        })
      });
      if (res.ok) {
        const data = await res.json();
        setProcessedImage(data.processed_image);
        setPreviewMetadata(data.metadata || {});
      }
    } catch (e) {
      console.error("Live preview failed", e);
    }
  };

  const runFullOCR = async () => {
    if (!originalFile) return;
    setLoading(true);
    setErrorMessage(null);
    try {
      const formData = new FormData();
      formData.append("file", originalFile);
      formData.append("config", JSON.stringify(config));
      formData.append("engine", engine);
      formData.append("languages", JSON.stringify(languages));
      formData.append("merge_boxes", mergeBoxes);

      const res = await fetch(`${API_BASE}/ocr`, {
        method: "POST",
        body: formData
      });
      
      if (res.ok) {
        const data = await res.json();
        setProcessedImage(data.processed_image_url || data.preprocessed_image);
        setResults(data.results);
        setSelectedWordIndex(null);
        setDetectedTables(data.metadata.detected_tables || []);
        setExecutionStats({
          time: data.execution_time_seconds,
          words: data.metadata.words_count,
          resolution: data.metadata.resolution,
          gpu: data.gpu_accelerated,
          skewAngle: data.metadata.deskew_angle
        });
      } else {
        const err = await res.json();
        setErrorMessage(err.detail || "Có lỗi xảy ra trong quá trình chạy OCR.");
      }
    } catch (e) {
      setErrorMessage("Không thể kết nối tới server backend. Vui lòng kiểm tra xem FastAPI đã chạy chưa.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      
      {/* Top Header */}
      <header className="app-header">
        <div className="brand-section">
          <div className="brand-icon-wrapper">
            <Sparkles size={24} style={{ color: '#fff' }} />
          </div>
          <div className="brand-title">
            <h1>OCR Playground</h1>
            <p>Xử Lý Ảnh & Nhận Diện Chữ Thực Chiến</p>
          </div>
        </div>

        <div className="backend-status">
          <span className={`status-dot ${backendStatus ? 'online' : ''}`}></span>
          {backendStatus ? (
            <span>
              Backend Online ({backendStatus.gpu_acceleration ? `GPU: ${backendStatus.gpu_type}` : 'CPU'})
            </span>
          ) : (
            <span>Backend Offline (Vui lòng chạy app.py)</span>
          )}
          {backendStatus && (
            <button 
              onClick={fetchBackendStatus} 
              style={{ background: 'none', border: 'none', color: '#9ca3af', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
            >
              <RefreshCw size={12} style={{ marginLeft: '4px' }} />
            </button>
          )}
        </div>
      </header>

      {/* Main Content Area */}
      {errorMessage && (
        <div style={{
          background: 'rgba(239, 68, 68, 0.1)',
          border: '1px solid rgba(239, 68, 68, 0.2)',
          padding: '1rem',
          borderRadius: '12px',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          color: '#fca5a5'
        }}>
          <AlertCircle size={20} />
          <p>{errorMessage}</p>
        </div>
      )}

      <div className="app-grid">
          
          {/* Sidebar Controls */}
          <ControlPanel 
            config={config}
            updateConfig={updateConfigAndPreview}
            engine={engine}
            setEngine={setEngine}
            languages={languages}
            setLanguages={setLanguages}
            backendStatus={backendStatus}
            mergeBoxes={mergeBoxes}
            setMergeBoxes={setMergeBoxes}
          />

          {/* Main Visual Board */}
          <div className="workspace-wrapper">
            
            {/* Upload Zone */}
            <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
                <span style={{ fontSize: '0.95rem', color: '#f3f4f6', fontWeight: 600 }}>Tải ảnh tài liệu cần nhận diện:</span>
                
                <label className="btn-secondary" style={{ cursor: 'pointer', margin: 0 }}>
                  <Upload size={16} />
                  Tải Ảnh Của Bạn
                  <input type="file" className="file-input" accept="image/*" onChange={handleFileUpload} />
                </label>
              </div>

              {!originalImage && (
                <div className="upload-zone" onClick={() => document.querySelector('.file-input').click()}>
                  <div className="upload-icon-box">
                    <Upload size={24} />
                  </div>
                  <div>
                    <p><span className="highlight">Nhấn để tải ảnh</span> hoặc kéo thả file vào đây</p>
                    <p style={{ fontSize: '0.75rem', marginTop: '0.25rem' }}>Hỗ trợ JPG, PNG, WEBP (Ảnh chụp hóa đơn, sách, danh thiếp)</p>
                  </div>
                </div>
              )}
            </div>

            {config.auto_flatten && previewMetadata.auto_flattened === false && (
              <div style={{
                background: 'rgba(245, 158, 11, 0.1)',
                border: '1px solid rgba(245, 158, 11, 0.2)',
                padding: '0.75rem 1rem',
                borderRadius: '12px',
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                color: '#fef08a',
                marginBottom: '1rem',
                fontSize: '0.875rem',
                lineHeight: '1.4'
              }}>
                <AlertCircle size={18} style={{ color: '#fbbf24', flexShrink: 0 }} />
                <span>
                  <strong>Không nhận diện được khung viền trang giấy:</strong> Thuật toán Auto-Flatten yêu cầu tài liệu phải có viền nền rõ ràng bao quanh để định vị 4 góc. Hãy thử chụp lại hình ảnh có phần nền tối bên ngoài viền tờ giấy/tài liệu để tạo độ tương phản tối ưu!
                </span>
              </div>
            )}

            {/* Live Interactive Board */}
            {originalImage && (
              <div className="ocr-workspace-grid">
                
                {/* Visualizer Card */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                  
                  {/* Bounding Box Viewer */}
                  <BoundingBoxViewer 
                    originalImage={originalImage}
                    processedImage={processedImage}
                    results={results}
                    loading={loading}
                    activeWordIndex={activeWordIndex}
                    setActiveWordIndex={setActiveWordIndex}
                    selectedWordIndex={selectedWordIndex}
                    setSelectedWordIndex={setSelectedWordIndex}
                  />

                  {/* OCR Statistics Row */}
                  {executionStats && (
                    <div className="stats-row">
                      <div className="stat-item">
                        <span className="stat-label">Thời gian chạy</span>
                        <span className="stat-value" style={{ color: '#a855f7' }}>
                          {executionStats.time}s
                        </span>
                      </div>
                      <div className="stat-item">
                        <span className="stat-label">Số từ phát hiện</span>
                        <span className="stat-value" style={{ color: '#06b6d4' }}>
                          {executionStats.words} từ
                        </span>
                      </div>
                      <div className="stat-item">
                        <span className="stat-label">Tăng tốc GPU</span>
                        <span className="stat-value" style={{ color: executionStats.gpu ? '#10b981' : '#f59e0b' }}>
                          {executionStats.gpu ? 'Có (MPS)' : 'Không (CPU)'}
                        </span>
                      </div>
                      <div className="stat-item">
                        <span className="stat-label">Góc xoay tự động</span>
                        <span className="stat-value" style={{ color: '#f3f4f6' }}>
                          {executionStats.skewAngle ? `${executionStats.skewAngle}°` : '0°'}
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Action Bar */}
                  <button className="btn-primary" onClick={runFullOCR} disabled={loading || !originalImage}>
                    <Play size={18} fill="#fff" />
                    Chạy Tiền Xử Lý & OCR Nhận Diện
                  </button>

                  {/* HTML Table Preview (Rendered dynamically in the main workspace if PP-Structure detected tables) */}
                  {detectedTables && detectedTables.length > 0 && (
                    <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '0.5rem' }}>
                      <h3 className="card-title" style={{ color: '#a855f7', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '0.5rem', margin: 0 }}>
                        📊 Bảng Biểu Khôi Phục (PP-Structure V3)
                      </h3>
                      {detectedTables.map((table) => (
                        <div key={table.id} className="detected-table-wrapper" style={{
                          background: 'rgba(0, 0, 0, 0.25)',
                          border: '1px solid rgba(255, 255, 255, 0.05)',
                          padding: '1.25rem',
                          borderRadius: '8px',
                          overflowX: 'auto',
                        }}>
                          <div 
                            className="structure-table-container"
                            dangerouslySetInnerHTML={{ __html: table.html }} 
                          />
                        </div>
                      ))}
                    </div>
                  )}

                </div>

                {/* Sidebar details list of recognized words */}
                <div className="glass-card details-panel">
                  <div className="details-list-header">
                    <span>Văn bản quét được</span>
                    <span style={{ color: '#9ca3af' }}>{results.length} từ</span>
                  </div>

                  {results.length > 0 ? (
                    <div className="details-scroll">
                      {results.map((item, index) => {
                        let confClass = 'conf-high';
                        if (item.confidence < 60) confClass = 'conf-low';
                        else if (item.confidence < 85) confClass = 'conf-mid';
                        const isSelected = activeWordIndex === index || selectedWordIndex === index;

                        return (
                          <div 
                            key={index}
                            id={`word-card-${index}`}
                            className={`word-card ${isSelected ? 'active' : ''}`}
                            onMouseEnter={() => setActiveWordIndex(index)}
                            onMouseLeave={() => setActiveWordIndex(null)}
                            onClick={() => setSelectedWordIndex(index)}
                          >
                            <span className="word-text">"{item.text}"</span>
                            <span className={`word-conf ${confClass}`}>{item.confidence}%</span>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#9ca3af', gap: '0.5rem', textAlign: 'center' }}>
                      <FileText size={32} style={{ opacity: 0.2 }} />
                      <p style={{ fontSize: '0.85rem' }}>
                        Chưa có dữ liệu thô.<br />Nhấn nút "Chạy OCR" để bắt đầu quét.
                      </p>
                    </div>
                  )}
                </div>

              </div>
            )}
          </div>

      </div>
    </div>
  );
}

export default App;
