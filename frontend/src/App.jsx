import { useState, useEffect, useRef, useCallback } from 'react';
import { 
  Upload, Play, RefreshCw, Layers, FileText, AlertCircle, Sparkles
} from 'lucide-react';
import gsap from 'gsap';
import { useGSAP } from '@gsap/react';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

import ControlPanel from './components/ControlPanel';
import BoundingBoxViewer from './components/BoundingBoxViewer';

gsap.registerPlugin(ScrollTrigger);

const DEFAULT_API_BASE = "http://127.0.0.1:8000/api";

function App() {
  // API URL state
  const [apiUrl, setApiUrl] = useState(() => {
    return localStorage.getItem('ocr_api_url') || DEFAULT_API_BASE;
  });

  // Image states
  const [originalFile, setOriginalFile] = useState(null);
  const [originalImage, setOriginalImage] = useState(null);
  const [processedImage, setProcessedImage] = useState(null);
  
  // OCR and Processing configurations
  const [config, setConfig] = useState({
    auto_flatten: false,
    grayscale: false,
    contrast: 1.0,
    brightness: 0,
    deskew: false,
    threshold_method: 'none',
    threshold_val: 127,
    adaptive_block_size: 11,
    adaptive_c: 2,
    morphology_op: 'none',
    morphology_kernel: 3,
    morphology_iterations: 1,
  });

  const debounceTimerRef = useRef(null);
  const containerRef = useRef(null);
  const lastRunRef = useRef(null);
  const initialModelSelectionRef = useRef(false);
  const modelSelectionRequestRef = useRef(0);

  const [engine, setEngine] = useState('easyocr');
  const [languages, setLanguages] = useState(['vi', 'en']);
  const [mergeBoxes, setMergeBoxes] = useState(false);

  // Results & stats
  const [results, setResults] = useState([]);
  const [detectedTables, setDetectedTables] = useState([]);
  const [executionStats, setExecutionStats] = useState(null);
  const [activeWordIndex, setActiveWordIndex] = useState(null);
  const [selectedWordIndex, setSelectedWordIndex] = useState(null);
  const [previewMetadata, setPreviewMetadata] = useState({});

  const [loading, setLoading] = useState(false);
  const [modelLoading, setModelLoading] = useState(false);
  const [backendStatus, setBackendStatus] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);

  const fetchBackendStatus = useCallback(async (url = apiUrl) => {
    try {
      const res = await fetch(`${url}/status`);
      if (res.ok) {
        const data = await res.json();
        setBackendStatus(data);
      } else setBackendStatus(null);
    } catch {
      setBackendStatus(null);
    }
  }, [apiUrl]);

  const fetchDefaultConfig = useCallback(async (url = apiUrl) => {
    try {
      const res = await fetch(`${url}/config/default`);
      if (res.ok) {
        const data = await res.json();
        setConfig(data);
      }
    } catch (error) {
      console.error(error);
    }
  }, [apiUrl]);

  const requestPreprocessingPreview = useCallback(async (currentConfig = null) => {
    if (!originalImage) return;
    const targetConfig = currentConfig || config;
    try {
      const res = await fetch(`${apiUrl}/preprocess`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image: originalImage, config: targetConfig })
      });
      if (res.ok) {
        const data = await res.json();
        setProcessedImage(data.processed_image);
        setPreviewMetadata(data.metadata || {});
      }
    } catch (error) {
      console.error(error);
    }
  }, [apiUrl, config, originalImage]);

  const requestModelSelection = useCallback(async (nextEngine = engine, nextLanguages = languages) => {
    const requestId = modelSelectionRequestRef.current + 1;
    modelSelectionRequestRef.current = requestId;
    initialModelSelectionRef.current = true;
    setModelLoading(true);
    setErrorMessage(null);
    try {
      const res = await fetch(`${apiUrl}/models/select`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ engine: nextEngine, languages: nextLanguages })
      });
      if (!res.ok) {
        const err = await res.json();
        const detail = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail);
        throw new Error(detail || "Could not load selected model.");
      }
      await fetchBackendStatus(apiUrl);
    } catch (error) {
      if (modelSelectionRequestRef.current === requestId) {
        setErrorMessage(error.message || "Could not load selected OCR model.");
      }
    } finally {
      if (modelSelectionRequestRef.current === requestId) {
        setModelLoading(false);
      }
    }
  }, [apiUrl, engine, fetchBackendStatus, languages]);

  const selectEngine = useCallback((nextEngine) => {
    setEngine(nextEngine);
    setResults([]);
    setSelectedWordIndex(null);
    setDetectedTables([]);
    setExecutionStats(null);
    lastRunRef.current = null;
    requestModelSelection(nextEngine, languages);
  }, [languages, requestModelSelection]);

  const selectLanguages = useCallback((nextLanguages) => {
    setLanguages(nextLanguages);
    lastRunRef.current = null;
    requestModelSelection(engine, nextLanguages);
  }, [engine, requestModelSelection]);

  const updateConfigAndPreview = (updatedFields, instant = false) => {
    setConfig(prev => {
      const newConfig = { ...prev, ...updatedFields };
      setResults([]);
      setSelectedWordIndex(null);
      setDetectedTables([]);
      setExecutionStats(null);

      if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);

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

  useEffect(() => {
    localStorage.setItem('ocr_api_url', apiUrl);
    fetchBackendStatus(apiUrl);
    fetchDefaultConfig(apiUrl);
  }, [apiUrl, fetchBackendStatus, fetchDefaultConfig]);

  useEffect(() => {
    if (backendStatus && !initialModelSelectionRef.current) {
      requestModelSelection(engine, languages);
    }
  }, [backendStatus, engine, languages, requestModelSelection]);

  useEffect(() => {
    if (originalImage) requestPreprocessingPreview(config);
  }, [config, originalImage, requestPreprocessingPreview]);

  useEffect(() => {
    const targetIndex = activeWordIndex !== null ? activeWordIndex : selectedWordIndex;
    if (targetIndex !== null) {
      const element = document.getElementById(`word-card-${targetIndex}`);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    }
  }, [activeWordIndex, selectedWordIndex]);

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

  const runFullOCR = async () => {
    if (!originalFile) return;

    // Client-side Cache check
    if (
      lastRunRef.current &&
      lastRunRef.current.file === originalFile &&
      JSON.stringify(lastRunRef.current.config) === JSON.stringify(config) &&
      lastRunRef.current.engine === engine &&
      JSON.stringify(lastRunRef.current.languages) === JSON.stringify(languages) &&
      lastRunRef.current.mergeBoxes === mergeBoxes
    ) {
      // Restore cached results instantly
      setProcessedImage(lastRunRef.current.processedImage);
      setResults(lastRunRef.current.results);
      setSelectedWordIndex(null);
      setDetectedTables(lastRunRef.current.detectedTables);
      setExecutionStats({
        ...lastRunRef.current.executionStats,
        isCached: true
      });
      return;
    }

    setLoading(true);
    setErrorMessage(null);
    try {
      const formData = new FormData();
      formData.append("file", originalFile);
      formData.append("config", JSON.stringify(config));
      formData.append("engine", engine);
      formData.append("languages", JSON.stringify(languages));
      formData.append("merge_boxes", mergeBoxes);

      const res = await fetch(`${apiUrl}/ocr`, {
        method: "POST",
        body: formData
      });
      
      if (res.ok) {
        const data = await res.json();
        const finalImage = data.processed_image_url || data.preprocessed_image;
        const finalResults = data.results;
        const finalTables = data.metadata.detected_tables || [];
        const finalStats = {
          time: data.execution_time_seconds,
          words: data.metadata.words_count,
          resolution: data.metadata.resolution,
          gpu: data.gpu_accelerated,
          skewAngle: data.metadata.deskew_angle
        };

        setProcessedImage(finalImage);
        setResults(finalResults);
        setSelectedWordIndex(null);
        setDetectedTables(finalTables);
        setExecutionStats(finalStats);

        // Cache the successful run
        lastRunRef.current = {
          file: originalFile,
          config: { ...config },
          engine,
          languages: [...languages],
          mergeBoxes,
          processedImage: finalImage,
          results: finalResults,
          detectedTables: finalTables,
          executionStats: finalStats
        };
      } else {
        const err = await res.json();
        setErrorMessage(err.detail || "Error running OCR.");
      }
    } catch {
      setErrorMessage("Could not connect to backend.");
    } finally {
      setLoading(false);
    }
  };

  useGSAP(() => {
    // Cinematic Hero Entry
    gsap.from('.hero-word', {
      y: 100,
      opacity: 0,
      duration: 1.2,
      stagger: 0.1,
      ease: 'power4.out',
    });

    gsap.from('.hero-pill', {
      scale: 0,
      opacity: 0,
      duration: 1.5,
      delay: 0.6,
      ease: 'elastic.out(1, 0.5)',
    });

    // Marquee
    gsap.to('.marquee-content', {
      xPercent: -50,
      repeat: -1,
      duration: 25,
      ease: 'none',
    });

    // Scrub Reveal
    gsap.to('.scrub-text', {
      backgroundPositionX: '100%',
      ease: 'none',
      scrollTrigger: {
        trigger: '.scrub-container',
        scrub: 1,
        start: 'top 80%',
        end: 'bottom 40%',
      }
    });

    // Bento Grid Stagger Entry
    gsap.from('.bento-cell', {
      y: 60,
      opacity: 0,
      duration: 0.8,
      stagger: 0.1,
      ease: 'power3.out',
      scrollTrigger: {
        trigger: '.bento-grid',
        start: 'top 85%',
      }
    });
  }, { scope: containerRef });

  return (
    <main ref={containerRef} className="w-full min-h-screen bg-zinc-950 text-white selection:bg-purple-500/30">
      
      {/* Navigation Pill */}
      <nav className="fixed top-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-4 bg-white/5 border border-white/10 backdrop-blur-xl px-6 py-3 rounded-full shadow-2xl">
        <Sparkles className="text-purple-400 w-5 h-5" />
        <span className="font-semibold tracking-tight text-sm">OCR PLAYGROUND</span>
        <div className="w-px h-4 bg-white/20"></div>
        <div className="flex items-center gap-2 text-xs font-medium">
          <span className={`w-2 h-2 rounded-full ${backendStatus ? 'bg-emerald-400 shadow-[0_0_10px_#34d399] animate-pulse' : 'bg-red-500'}`}></span>
          <span className="text-zinc-300">{backendStatus ? (backendStatus.gpu_acceleration ? 'GPU ENABLED' : 'CPU MODE') : 'OFFLINE'}</span>
        </div>
      </nav>

      {/* Cinematic Center Hero */}
      <section className="relative pt-48 pb-32 px-6 flex flex-col items-center justify-center text-center overflow-hidden">
        {/* Radial Background Blur */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-purple-600/20 rounded-full blur-[120px] pointer-events-none"></div>

        <h1 className="max-w-6xl mx-auto text-[clamp(3.5rem,7vw,7.5rem)] font-bold leading-[1.05] tracking-tighter flex flex-wrap justify-center items-center gap-x-4">
          <span className="hero-word overflow-hidden"><span className="inline-block">Extract</span></span>
          <span className="hero-word overflow-hidden"><span className="inline-block text-zinc-400">knowledge</span></span>
          <span className="hero-word overflow-hidden"><span className="inline-block">from</span></span>
          <br />
          <span className="hero-word overflow-hidden"><span className="inline-block">any</span></span>
          <span className="hero-pill inline-flex items-center justify-center w-32 h-14 md:w-48 md:h-20 mx-2 bg-gradient-to-br from-purple-500 to-cyan-400 rounded-full align-middle shadow-[0_0_40px_rgba(168,85,247,0.4)]">
            <Scan className="w-8 h-8 md:w-10 md:h-10 text-white" />
          </span>
          <span className="hero-word overflow-hidden"><span className="inline-block">document.</span></span>
        </h1>

        <p className="hero-word mt-10 max-w-2xl mx-auto text-lg md:text-xl text-zinc-400 font-medium leading-relaxed">
          Powered by state-of-the-art neural networks. AI-driven document deskewing, intelligent thresholding, and sub-second recognition logic.
        </p>
      </section>

      {/* Infinite Marquee */}
      <div className="w-full border-y border-white/5 bg-white/[0.01] py-8 overflow-hidden whitespace-nowrap flex relative">
        <div className="absolute inset-y-0 left-0 w-32 bg-gradient-to-r from-zinc-950 to-transparent z-10"></div>
        <div className="absolute inset-y-0 right-0 w-32 bg-gradient-to-l from-zinc-950 to-transparent z-10"></div>
        
        <div className="marquee-content flex gap-16 items-center px-8 text-zinc-500 font-semibold text-2xl tracking-widest uppercase">
          {Array(8).fill(["PYTORCH", "OPENCV", "PADDLE OCR", "EASYOCR"]).flat().map((tech, i) => (
            <span key={i} className="flex items-center gap-4">
              <span className="w-2 h-2 rounded-full bg-zinc-700"></span>
              {tech}
            </span>
          ))}
        </div>
      </div>

      {/* Scrubbing Text Desire Section */}
      <section className="scrub-container py-32 md:py-48 px-6 max-w-5xl mx-auto">
        <h2 
          className="scrub-text text-[clamp(2.5rem,5vw,4.5rem)] font-bold leading-tight tracking-tighter"
          style={{
            background: 'linear-gradient(to right, #fff 50%, rgba(255,255,255,0.1) 50%)',
            backgroundSize: '200% 100%',
            backgroundPositionX: '100%',
            WebkitBackgroundClip: 'text',
            color: 'transparent'
          }}
        >
          No more distorted scans. Our AI engine mathematically unwarps, corrects skew, and extracts raw text with pixel-perfect precision. 
        </h2>
      </section>

      {/* Gapless Bento Grid Workspace */}
      <section className="px-4 md:px-8 pb-48 max-w-[1800px] mx-auto">
        
        {errorMessage && (
          <div className="mb-6 p-4 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-400 flex items-center gap-3">
            <AlertCircle /> {errorMessage}
          </div>
        )}

        {config.auto_flatten && previewMetadata.auto_flattened === false && (
          <div className="mb-6 p-4 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center gap-3">
            <AlertCircle /> Không nhận diện được khung viền trang giấy. Hãy thử chụp lại trên nền tối.
          </div>
        )}

        <div className="bento-grid grid grid-cols-1 lg:grid-cols-12 grid-auto-rows-min gap-4 grid-flow-dense">
          
          {/* Bento 1: Upload & Action (Col 1-3) */}
          <div className="bento-cell lg:col-span-3 flex flex-col gap-4">
            <div 
              className="group relative h-48 rounded-3xl border border-white/10 bg-white/[0.02] overflow-hidden cursor-pointer flex flex-col items-center justify-center p-6 text-center hover:bg-white/[0.04] transition-colors"
              onClick={() => document.querySelector('.file-input').click()}
            >
              <input type="file" className="file-input hidden" accept="image/*" onChange={handleFileUpload} />
              <div className="w-14 h-14 rounded-full bg-white/5 flex items-center justify-center mb-4 group-hover:scale-110 group-hover:bg-purple-500/20 group-hover:text-purple-400 transition-all duration-500">
                <Upload />
              </div>
              <h3 className="font-semibold text-zinc-200">Upload Image</h3>
              <p className="text-xs text-zinc-500 mt-2">JPG, PNG, WEBP supported</p>
            </div>

            <button 
              onClick={runFullOCR} 
              disabled={loading || modelLoading || !originalImage}
              className="group relative h-24 rounded-3xl bg-white text-black font-bold text-lg flex items-center justify-center gap-3 overflow-hidden disabled:opacity-50 disabled:cursor-not-allowed hover:scale-[1.02] transition-transform duration-500"
            >
              <div className="absolute inset-0 bg-gradient-to-r from-purple-200 to-cyan-200 opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
              <span className="relative z-10 flex items-center gap-2">
                {(loading || modelLoading) ? <RefreshCw className="animate-spin" /> : <Play fill="currentColor" />}
                {modelLoading ? "Loading Model" : "Run Engine"}
              </span>
            </button>

            {/* Sidebar Controls wrapped in Bento */}
            <div className="rounded-3xl border border-white/10 bg-white/[0.02] p-6 backdrop-blur-xl">
              <ControlPanel 
                config={config}
                updateConfig={updateConfigAndPreview}
                engine={engine}
                setEngine={selectEngine}
                languages={languages}
                setLanguages={selectLanguages}
                backendStatus={backendStatus}
                mergeBoxes={mergeBoxes}
                setMergeBoxes={setMergeBoxes}
                apiUrl={apiUrl}
                setApiUrl={setApiUrl}
              />
            </div>
          </div>

          {/* Bento 2: Massive Canvas (Col 4-9) */}
          <div className="bento-cell lg:col-span-6 rounded-3xl border border-white/10 bg-black/50 overflow-hidden flex flex-col relative group">
            {originalImage ? (
              <div className="w-full h-full min-h-[600px] flex items-center justify-center p-4">
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
              </div>
            ) : (
              <div className="absolute inset-0 flex flex-col items-center justify-center text-zinc-600">
                <Layers size={64} className="opacity-20 mb-6" />
                <p className="font-medium">Canvas Awaiting Document</p>
              </div>
            )}
          </div>

          {/* Bento 3: Results & Data (Col 10-12) */}
          <div className="bento-cell lg:col-span-3 flex flex-col gap-4">
            
            {/* Stats Card */}
            {executionStats ? (
              <div className="rounded-3xl border border-white/10 bg-white/[0.02] p-6 grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-zinc-500 uppercase font-semibold">Time</p>
                  <p className="text-xl font-bold text-purple-400 mt-1">
                    {executionStats.isCached ? "Instant ⚡" : `${executionStats.time}s`}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-zinc-500 uppercase font-semibold">Words</p>
                  <p className="text-xl font-bold text-cyan-400 mt-1">{executionStats.words}</p>
                </div>
                <div>
                  <p className="text-xs text-zinc-500 uppercase font-semibold">Compute</p>
                  <p className="text-xl font-bold text-white mt-1">{executionStats.gpu ? 'GPU' : 'CPU'}</p>
                </div>
                <div>
                  <p className="text-xs text-zinc-500 uppercase font-semibold">Skew</p>
                  <p className="text-xl font-bold text-white mt-1">{executionStats.skewAngle || 0}°</p>
                </div>
              </div>
            ) : (
              <div className="h-32 rounded-3xl border border-white/10 bg-white/[0.02] flex items-center justify-center text-zinc-600 font-medium">
                No Stats Yet
              </div>
            )}

            {/* Results List */}
            <div className="flex-1 rounded-3xl border border-white/10 bg-white/[0.02] p-6 flex flex-col max-h-[800px]">
              <h3 className="text-sm font-semibold text-zinc-400 mb-4 flex justify-between">
                EXTRACTED DATA <span className="text-white">{results.length}</span>
              </h3>
              
              <div className="flex-1 overflow-y-auto pr-2 flex flex-col gap-2 custom-scrollbar">
                {results.length > 0 ? results.map((item, index) => {
                  const isSelected = activeWordIndex === index || selectedWordIndex === index;
                  return (
                    <div 
                      key={index}
                      id={`word-card-${index}`}
                      className={`p-4 rounded-2xl border transition-all duration-300 cursor-pointer flex justify-between items-center group-hover:scale-[1.02] ${
                        isSelected 
                          ? 'bg-white/10 border-white/20 shadow-lg' 
                          : 'bg-white/[0.01] border-white/5 hover:bg-white/[0.03]'
                      }`}
                      onMouseEnter={() => setActiveWordIndex(index)}
                      onMouseLeave={() => setActiveWordIndex(null)}
                      onClick={() => setSelectedWordIndex(index)}
                    >
                      <span className="text-sm font-medium text-zinc-200 line-clamp-2 pr-4">{item.text}</span>
                      <span className={`text-xs font-mono font-bold px-2 py-1 rounded-md ${
                        item.confidence > 85 ? 'bg-emerald-500/10 text-emerald-400' :
                        item.confidence > 60 ? 'bg-amber-500/10 text-amber-400' :
                        'bg-red-500/10 text-red-400'
                      }`}>
                        {item.confidence}%
                      </span>
                    </div>
                  )
                }) : (
                  <div className="flex-1 flex flex-col items-center justify-center text-zinc-600 text-sm">
                    <FileText size={32} className="opacity-20 mb-4" />
                    Waiting for extraction
                  </div>
                )}
              </div>
            </div>

          </div>

          {/* Table Data appended at bottom if exists */}
          {detectedTables && detectedTables.length > 0 && (
            <div className="bento-cell lg:col-span-12 rounded-3xl border border-white/10 bg-white/[0.02] p-8 overflow-hidden">
              <h3 className="text-xl font-bold text-white mb-6">Restored Tables</h3>
              <div className="grid grid-cols-1 gap-6">
                {detectedTables.map((table) => (
                  <div key={table.id} className="overflow-x-auto rounded-2xl border border-white/10 bg-black/50 p-6">
                    <div dangerouslySetInnerHTML={{ __html: table.html }} className="text-zinc-300" />
                  </div>
                ))}
              </div>
            </div>
          )}

        </div>
      </section>

    </main>
  );
}

// Minimal missing icons
const Scan = ({ className }) => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M3 7V5a2 2 0 0 1 2-2h2"></path>
    <path d="M17 3h2a2 2 0 0 1 2 2v2"></path>
    <path d="M21 17v2a2 2 0 0 1-2 2h-2"></path>
    <path d="M7 21H5a2 2 0 0 1-2-2v-2"></path>
    <line x1="7" y1="12" x2="17" y2="12"></line>
  </svg>
);

export default App;
