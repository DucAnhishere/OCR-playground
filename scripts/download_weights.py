import os
import shutil
import sys
from pathlib import Path

# Add backend directory to path to resolve imports if necessary (since script is in scripts/)
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.append(str(backend_dir))

# Ensure local weights directories exist
weights_dir = Path(__file__).parent.parent / "weights"
easyocr_dest = weights_dir / "easyocr"
paddle_dest = weights_dir / "paddleocr"
paddlex_dest = weights_dir / "paddlex"
vietocr_dest = weights_dir / "vietocr"
torch_dest = weights_dir / "torch"

for d in [easyocr_dest, paddle_dest, paddlex_dest, vietocr_dest, torch_dest]:
    d.mkdir(parents=True, exist_ok=True)

print("============ STARTING MODEL WEIGHTS PRE-DOWNLOAD ============")
print("This script runs on your host machine to download models reliably.")
print("=============================================================")

# 1. Download EasyOCR
print("\n[1/3] Downloading EasyOCR models...")
try:
    import easyocr
    # Trigger download to ~/.EasyOCR/
    easyocr.Reader(['en', 'vi'], gpu=False)
    
    # Copy to project folder
    src = Path.home() / ".EasyOCR"
    if src.exists():
        print(f"Copying EasyOCR weights from {src} to {easyocr_dest}...")
        shutil.copytree(src, easyocr_dest, dirs_exist_ok=True)
        print("✅ EasyOCR weights copied successfully.")
except Exception as e:
    print(f"❌ Failed to download EasyOCR: {e}")

# 2. Download PaddleOCR & PP-Structure
print("\n[2/3] Downloading PaddleOCR models...")
try:
    from paddleocr import PaddleOCR, PPStructureV3
    PaddleOCR(use_textline_orientation=True, lang='en')
    PaddleOCR(use_textline_orientation=True, lang='vi')
    import numpy as np
    structure = PPStructureV3()
    # Run a mock prediction to force-download all lazy-loaded PP-Structure sub-models
    print("Running mock PP-Structure prediction to trigger all sub-model downloads...")
    dummy_img = np.ones((100, 100, 3), dtype=np.uint8) * 255
    structure.predict(dummy_img)

    # Copy to project folder
    src = Path.home() / ".paddleocr"
    if src.exists():
        print(f"Copying PaddleOCR weights from {src} to {paddle_dest}...")
        shutil.copytree(src, paddle_dest, dirs_exist_ok=True)
        print("✅ PaddleOCR weights copied successfully.")
        
    src_paddlex = Path.home() / ".paddlex"
    if src_paddlex.exists():
        print(f"Copying PaddleX weights from {src_paddlex} to {paddlex_dest}...")
        shutil.copytree(src_paddlex, paddlex_dest, dirs_exist_ok=True)
        print("✅ PaddleX weights copied successfully.")
except Exception as e:
    print(f"❌ Failed to download PaddleOCR: {e}")

# 3. Download VietOCR & PyTorch VGG weights
print("\n[3/3] Downloading VietOCR models...")
try:
    from vietocr.tool.predictor import Predictor
    from vietocr.tool.config import Cfg
    config = Cfg.load_config_from_name('vgg_transformer')
    config['device'] = 'cpu'
    Predictor(config)
    
    # Download VietOCR weights directly to project folder
    vietocr_file = vietocr_dest / "vgg_transformer.pth"
    if not vietocr_file.exists():
        print("Downloading VietOCR weights directly to project folder...")
        url = 'https://vocr.vn/data/vietocr/vgg_transformer.pth'
        import requests
        from tqdm import tqdm
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(vietocr_file, 'wb') as f:
                for chunk in tqdm(r.iter_content(chunk_size=8192)):
                    f.write(chunk)
        print("✅ VietOCR weights downloaded/saved successfully.")
    else:
        print("✅ VietOCR weights already exist in project folder.")
        
    # Copy PyTorch VGG weights
    src_torch = Path.home() / ".cache" / "torch"
    if src_torch.exists():
        print(f"Copying Torch cache from {src_torch} to {torch_dest}...")
        shutil.copytree(src_torch, torch_dest, dirs_exist_ok=True)
        print("✅ PyTorch weights copied successfully.")
except Exception as e:
    print(f"❌ Failed to download VietOCR: {e}")

print("\n=============================================================")
print("🎉 Weight pre-downloads complete!")
print(f"All weights copied to local project directory: {weights_dir}")
print("=============================================================")
