
def merge_adjacent_words(words: list[dict], gap_ratio: float = 1.5) -> list[dict]:
    """
    Groups and merges horizontally aligned, adjacent OCR word bounding boxes.
    
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
        
    # 1. Precalculate Center Y and Height for each word to assist with line grouping
    words_processed = []
    for w in words:
        box = w["box"]
        cy = box["y"] + box["h"] / 2
        words_processed.append({
            "text": w["text"],
            "confidence": w["confidence"],
            "x": box["x"],
            "y": box["y"],
            "w": box["w"],
            "h": box["h"],
            "cy": cy
        })
        
    # 2. Sort words from top to bottom, then left to right
    words_processed.sort(key=lambda item: (item["y"], item["x"]))
    
    # 3. Group words into horizontal lines based on vertical overlap
    lines = []
    current_line = [words_processed[0]]
    
    for w in words_processed[1:]:
        # Calculate the average center Y of current line
        line_cy = sum(item["cy"] for item in current_line) / len(current_line)
        # Average height of words in the current line
        line_h = sum(item["h"] for item in current_line) / len(current_line)
        # Allowance threshold (70% of average word height)
        height_thresh = line_h * 0.7
        
        if abs(w["cy"] - line_cy) < height_thresh:
            current_line.append(w)
        else:
            # Sort current line left-to-right before finalizing
            current_line.sort(key=lambda item: item["x"])
            lines.append(current_line)
            current_line = [w]
            
    # Append the last line
    current_line.sort(key=lambda item: item["x"])
    lines.append(current_line)
    
    # 4. Merge adjacent words on each line
    merged_results = []
    
    for line in lines:
        if not line:
            continue
            
        merged_line = []
        current_word = line[0]
        
        for next_word in line[1:]:
            # Calculate horizontal gap between current word and next word
            gap = next_word["x"] - (current_word["x"] + current_word["w"])
            
            # The gap threshold scales with the font size (represented by height)
            threshold = max(current_word["h"], next_word["h"]) * gap_ratio
            
            if gap <= threshold:
                # Merge!
                merged_x = current_word["x"]
                merged_w = (next_word["x"] + next_word["w"]) - current_word["x"]
                merged_y = min(current_word["y"], next_word["y"])
                merged_h = max(current_word["y"] + current_word["h"], next_word["y"] + next_word["h"]) - merged_y
                
                # Combine text strings with a space
                merged_text = current_word["text"] + " " + next_word["text"]
                # Average confidence
                merged_conf = round((current_word["confidence"] + next_word["confidence"]) / 2, 2)
                
                # Update current_word to represent the merged box
                current_word = {
                    "text": merged_text,
                    "confidence": merged_conf,
                    "x": merged_x,
                    "y": merged_y,
                    "w": merged_w,
                    "h": merged_h,
                    "cy": merged_y + merged_h / 2
                }
            else:
                # Far apart -> save current_word and move on to next
                merged_line.append(current_word)
                current_word = next_word
                
        # Append the last word of the line
        merged_line.append(current_word)
        
        # Convert back to standard dict format
        for item in merged_line:
            merged_results.append({
                "text": item["text"],
                "confidence": item["confidence"],
                "box": {
                    "x": int(item["x"]),
                    "y": int(item["y"]),
                    "w": int(item["w"]),
                    "h": int(item["h"])
                }
            })
            
    # 5. Sort final results top to bottom, then left to right to maintain neat ordering
    merged_results.sort(key=lambda w: (w["box"]["y"], w["box"]["x"]))
    
    return merged_results
