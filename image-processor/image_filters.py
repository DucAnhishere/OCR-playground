import cv2
import numpy as np
import base64

def decode_image(base64_str: str) -> np.ndarray:
    """Decodes a base64 encoded image string into an OpenCV image (numpy array)."""
    if "," in base64_str:
        base64_str = base64_str.split(",")[1]
    img_data = base64.b64decode(base64_str)
    nparr = np.frombuffer(img_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img

def encode_image(img: np.ndarray) -> str:
    """Encodes an OpenCV image (numpy array) into a JPEG base64 string."""
    _, buffer = cv2.imencode('.jpg', img)
    base64_str = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/jpeg;base64,{base64_str}"

def apply_contrast_brightness(img: np.ndarray, alpha: float, beta: float) -> np.ndarray:
    """
    Adjusts contrast and brightness of the image.
    alpha (contrast): 1.0 to 3.0 (default 1.0)
    beta (brightness): 0 to 100 (default 0)
    """
    return cv2.convertScaleAbs(img, alpha=alpha, beta=beta)

def apply_grayscale(img: np.ndarray) -> np.ndarray:
    """Converts image to grayscale."""
    if len(img.shape) == 3:
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img

def apply_threshold(img: np.ndarray, method: str, thresh_val: int = 127, block_size: int = 11, c_val: int = 2) -> np.ndarray:
    """
    Applies binarization (thresholding) to the image.
    Methods: 'binary', 'otsu', 'adaptive'
    """
    # Ensure image is grayscale first
    gray = apply_grayscale(img)
    
    if method == 'binary':
        _, thresh = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY)
        return thresh
    elif method == 'otsu':
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return thresh
    elif method == 'adaptive':
        # block_size must be an odd number >= 3
        if block_size % 2 == 0:
            block_size += 1
        block_size = max(3, block_size)
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, block_size, c_val
        )
        return thresh
    return gray

def apply_morphology(img: np.ndarray, op: str, kernel_size: int = 3, iterations: int = 1) -> np.ndarray:
    """
    Applies morphological dilation or erosion to clean noise or connect broken strokes.
    op: 'dilation', 'erosion'
    """
    if kernel_size < 1:
        kernel_size = 1
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
    
    if op == 'dilation':
        return cv2.dilate(img, kernel, iterations=iterations)
    elif op == 'erosion':
        return cv2.erode(img, kernel, iterations=iterations)
    return img

def apply_deskew(img: np.ndarray) -> tuple[np.ndarray, float]:
    """
    Detects rotation angle of the text and rotates the image back (deskewing)
    using the minimum area rectangle of all non-zero pixels.
    """
    gray = apply_grayscale(img)
    
    # Invert the image (black background, white text for coordinate finding)
    inverted = cv2.bitwise_not(gray)
    
    # Binarize the image to get clear contours
    _, thresh = cv2.threshold(inverted, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Get all coordinates of non-zero pixels
    coords = np.column_stack(np.where(thresh > 0))
    
    if len(coords) == 0:
        return img, 0.0  # Empty image, no rotation
        
    # Find minimum bounding box around all text pixels
    rect = cv2.minAreaRect(coords)
    angle = rect[-1]
    
    # OpenCV minAreaRect returns angle in [-90, 0)
    # We normalize the angle to be between -45 and 45 degrees
    if angle < -45:
        angle = -(90 + angle)
    elif angle > 45:
        angle = 90 - angle
    else:
        angle = -angle
        
    # If the angle is very small, we don't need to rotate
    if abs(angle) < 0.5:
        return img, 0.0
        
    # Perform rotation
    (h, w) = img.shape[:2]
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    
    # Warp image to rotate, filling empty borders with white (255) or duplicating borders
    rotated = cv2.warpAffine(
        img, rotation_matrix, (w, h), 
        flags=cv2.INTER_CUBIC, 
        borderMode=cv2.BORDER_REPLICATE
    )
    
    return rotated, angle

def apply_perspective_transform(img: np.ndarray) -> tuple[np.ndarray, bool, str]:
    """
    Automatically detects the document in the image and flattens it (Perspective Transform)
    using classical OpenCV edge & contour detection.
    
    Returns the warped image, success status, and the method used ("opencv").
    """
    h_img, w_img = img.shape[:2]
    total_area = h_img * w_img
    orig = img.copy()

    print("[OpenCV Preprocessing] Running classical contour detection...")
    try:
        # 1. Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 2. Apply morphological closing to merge text and lines
        close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
        closed = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, close_kernel)
        
        # 3. Heavily blur to smooth textures
        blurred = cv2.GaussianBlur(closed, (15, 15), 0)
        
        # 4. Canny edge detection
        edged = cv2.Canny(blurred, 30, 120)
        edged = cv2.dilate(edged, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
        
        # 5. Find contours and sort by size
        contours, _ = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:8]
        
        doc_contour = None
        for c in contours:
            area = cv2.contourArea(c)
            if area < 0.15 * total_area:
                continue
                
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            
            if len(approx) == 4:
                doc_contour = approx
                break
                
        # Try Otsu fallback if Canny fails
        if doc_contour is None:
            _, thresh = cv2.threshold(closed, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)))
            contours, _ = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]
            for c in contours:
                area = cv2.contourArea(c)
                if area < 0.15 * total_area:
                    continue
                peri = cv2.arcLength(c, True)
                approx = cv2.approxPolyDP(c, 0.02 * peri, True)
                if len(approx) == 4:
                    doc_contour = approx
                    break
                    
        if doc_contour is None:
            return img, False, "none"
            
        pts = doc_contour.reshape(4, 2)
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        
        (tl, tr, br, bl) = rect
        
        widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
        widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
        maxWidth = max(int(widthA), int(widthB))
        
        heightA = np.sqrt(((br[1] - tr[1]) ** 2) + ((br[0] - tr[0]) ** 2))
        heightB = np.sqrt(((bl[1] - tl[1]) ** 2) + ((bl[0] - tl[0]) ** 2))
        maxHeight = max(int(heightA), int(heightB))
        
        if maxWidth <= 0 or maxHeight <= 0:
            return img, False, "none"
            
        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]
        ], dtype="float32")
        
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(orig, M, (maxWidth, maxHeight))
        return warped, True, "opencv"
    except Exception as e:
        print(f"[OpenCV Error] Perspective transform failed: {e}")
        return img, False, "none"

def preprocess_pipeline(img: np.ndarray, config: dict) -> tuple[np.ndarray, dict]:
    """
    Runs the complete preprocessing pipeline based on a configuration dictionary.
    Returns the processed image and metadata.
    """
    processed = img.copy()
    meta = {}
    
    # 0. Perspective Transformation (Flatten sheet of paper)
    if config.get("auto_flatten", False):
        warped, success, method = apply_perspective_transform(processed)
        if success:
            processed = warped
            meta["auto_flattened"] = True
            meta["flatten_method"] = method
        else:
            meta["auto_flattened"] = False
            meta["flatten_method"] = "none"
            
    # 1. Adjust Contrast & Brightness
    if config.get("contrast", 1.0) != 1.0 or config.get("brightness", 0.0) != 0.0:
        processed = apply_contrast_brightness(
            processed, 
            float(config.get("contrast", 1.0)), 
            int(config.get("brightness", 0.0))
        )
        
    # 2. Deskewing
    if config.get("deskew", False):
        processed, angle = apply_deskew(processed)
        meta["deskew_angle"] = round(angle, 2)
        
    # 3. Grayscale (Mandatory if threshold is requested)
    if config.get("grayscale", False) or config.get("threshold_method") in ['binary', 'otsu', 'adaptive']:
        processed = apply_grayscale(processed)
        
    # 4. Thresholding (Binarization)
    thresh_method = config.get("threshold_method", "none")
    if thresh_method in ['binary', 'otsu', 'adaptive']:
        processed = apply_threshold(
            processed, 
            thresh_method, 
            thresh_val=int(config.get("threshold_val", 127)),
            block_size=int(config.get("adaptive_block_size", 11)),
            c_val=int(config.get("adaptive_c", 2))
        )
        
    # 5. Morphological ops (dilation/erosion)
    morph_op = config.get("morphology_op", "none")
    if morph_op in ['dilation', 'erosion']:
        processed = apply_morphology(
            processed, 
            morph_op, 
            kernel_size=int(config.get("morphology_kernel", 3)),
            iterations=int(config.get("morphology_iterations", 1))
        )
        
    return processed, meta
