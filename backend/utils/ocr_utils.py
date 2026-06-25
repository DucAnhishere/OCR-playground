
def merge_adjacent_words(words: list[dict], gap_ratio: float = 1.5) -> list[dict]:
    """
    Groups and merges horizontally aligned, adjacent OCR word bounding boxes.
    This implementation uses a robust local tracing algorithm that handles skewed/tilted text lines.
    
    Args:
        words (list[dict]): A list of dictionaries representing words:
            {
                "text": str,
                "confidence": float (0-100),
                "box": {"x": int, "y": int, "w": int, "h": int}
            }
        gap_ratio (float): The threshold factor for horizontal merging. 
                           If horizontal gap < max(height_A, height_B) * gap_ratio, they are merged.
                           Default is 1.5.
                           
    Returns:
        list[dict]: Standardized merged words list.
    """
    if not words:
        return []
        
    # 1. Preprocess words to have easy access to coordinates and center Y
    ungrouped = []
    for w in words:
        box = w["box"]
        ungrouped.append({
            "text": w["text"],
            "confidence": w["confidence"],
            "x": box["x"],
            "y": box["y"],
            "w": box["w"],
            "h": box["h"],
            "cy": box["y"] + box["h"] / 2
        })
        
    lines = []
    
    # 2. Group words into lines using local left-to-right tracing
    while ungrouped:
        # Start a new line with the leftmost remaining word
        current = min(ungrouped, key=lambda w: w["x"])
        ungrouped.remove(current)
        line = [current]
        
        # Trace the line horizontally to the right
        while True:
            candidates = []
            for w in ungrouped:
                # Candidate must be to the right (allowing a tiny horizontal overlap of 20% of current width)
                if w["x"] >= current["x"] + current["w"] * -0.2:
                    gap = w["x"] - (current["x"] + current["w"])
                    max_gap = max(current["h"], w["h"]) * gap_ratio
                    
                    if gap <= max_gap:
                        # Verify vertical alignment (dy) is within 60% of word height
                        dy = abs(w["cy"] - current["cy"])
                        max_dy = max(current["h"], w["h"]) * 0.6
                        
                        if dy <= max_dy:
                            candidates.append((gap, w))
            
            if not candidates:
                break
                
            # Choose the closest candidate horizontally
            candidates.sort(key=lambda item: item[0])
            best_w = candidates[0][1]
            
            current = best_w
            ungrouped.remove(current)
            line.append(current)
            
        lines.append(line)
        
    # 3. Merge the words in each line
    merged_results = []
    for line in lines:
        # Ensure the line is strictly ordered left-to-right
        line.sort(key=lambda w: w["x"])
        
        current_word = line[0]
        for next_word in line[1:]:
            # Calculate the bounding box that encompasses both words
            merged_x = current_word["x"]
            merged_w = (next_word["x"] + next_word["w"]) - current_word["x"]
            merged_y = min(current_word["y"], next_word["y"])
            merged_h = max(current_word["y"] + current_word["h"], next_word["y"] + next_word["h"]) - merged_y
            
            # Combine text and average the confidence score
            merged_text = current_word["text"] + " " + next_word["text"]
            merged_conf = round((current_word["confidence"] + next_word["confidence"]) / 2, 2)
            
            current_word = {
                "text": merged_text,
                "confidence": merged_conf,
                "x": merged_x,
                "y": merged_y,
                "w": merged_w,
                "h": merged_h,
                "cy": merged_y + merged_h / 2
            }
            
        merged_results.append({
            "text": current_word["text"],
            "confidence": current_word["confidence"],
            "box": {
                "x": int(current_word["x"]),
                "y": int(current_word["y"]),
                "w": int(current_word["w"]),
                "h": int(current_word["h"])
            }
        })
        
    # 4. Sort final results top to bottom, then left to right for structured ordering
    merged_results.sort(key=lambda w: (w["box"]["y"], w["box"]["x"]))
    return merged_results
