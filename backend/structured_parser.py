import re

def extract_structured_data(ocr_results: list[dict]) -> dict:
    """
    Analyzes OCR results to extract structured information like Total, Email, Phone, Date.
    """
    # 1. Reconstruct lines of text by grouping words by vertical overlap (y coordinate)
    words = []
    for r in ocr_results:
        box = r["box"]
        # calculate center y
        cy = box["y"] + box["h"] / 2
        words.append({
            "text": r["text"],
            "x": box["x"],
            "y": box["y"],
            "w": box["w"],
            "h": box["h"],
            "cy": cy
        })
        
    # Group words into lines
    lines = []
    if not words:
        return {}
        
    # Sort words top to bottom, then left to right
    words.sort(key=lambda w: (w["y"], w["x"]))
    
    current_line = [words[0]]
    for w in words[1:]:
        # If center Y is close to the current line's average center Y, group them
        line_cy = sum(item["cy"] for item in current_line) / len(current_line)
        # Allow vertical threshold of 60% of average word height
        height_thresh = sum(item["h"] for item in current_line) / len(current_line) * 0.7
        
        if abs(w["cy"] - line_cy) < height_thresh:
            current_line.append(w)
        else:
            # Sort current line left to right before saving
            current_line.sort(key=lambda x: x["x"])
            lines.append(" ".join([item["text"] for item in current_line]))
            current_line = [w]
            
    # Add last line
    current_line.sort(key=lambda x: x["x"])
    lines.append(" ".join([item["text"] for item in current_line]))
    
    full_text = "\n".join(lines)
    
    # --- Extraction Heuristics ---
    extracted = {
        "merchant_name": "Không phát hiện",
        "email": "Không phát hiện",
        "phone_number": "Không phát hiện",
        "date": "Không phát hiện",
        "total_amount": "Không phát hiện",
        "detected_lines_count": len(lines)
    }
    
    # 1. Merchant: Usually the first line of text with letters
    for line in lines[:3]:
        clean = re.sub(r'[^A-Za-z0-9\sÀ-ỹ]', '', line).strip()
        if len(clean) > 3 and not any(k in clean.lower() for k in ["hóa đơn", "invoice", "receipt", "ngày", "date"]):
            extracted["merchant_name"] = clean
            break
            
    # 2. Email Regex
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', full_text)
    if email_match:
        extracted["email"] = email_match.group(0)
        
    # 3. Phone number Regex (Vietnamese style / global)
    phone_match = re.search(r'(?:\+?84|0)(?:\s*\d){9,10}', full_text)
    if phone_match:
        extracted["phone_number"] = re.sub(r'\s+', '', phone_match.group(0))
        
    # 4. Date Regex: DD/MM/YYYY, YYYY-MM-DD etc.
    date_match = re.search(r'\b\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}\b|\b\d{4}[-/.]\d{1,2}[-/.]\d{1,2}\b', full_text)
    if date_match:
        extracted["date"] = date_match.group(0)
        
    # 5. Total Amount Heuristics: search for keywords and find numbers nearby
    total_keywords = [
        "total", "tổng cộng", "tong cong", "thanh toán", 
        "thanh toan", "amount", "tiền mặt", "cash", "grand total"
    ]
    
    amount_patterns = [
        r'\b\d{1,3}(?:[.,]\d{3})+(?:\s*[đdđ]|[vV][nN][dD])?\b',  # 150.000 đ
        r'\b\d+(?:\.\d{2})?\b'                                   # 150.00
    ]
    
    found_totals = []
    
    # Scan lines for total keywords
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in total_keywords):
            # Check if there is an amount on the same line
            for pattern in amount_patterns:
                matches = re.findall(pattern, line)
                if matches:
                    found_totals.append((i, matches[-1]))
                    
            # Check next line if no amount found on the same line
            if not found_totals and i + 1 < len(lines):
                next_line = lines[i + 1]
                for pattern in amount_patterns:
                    matches = re.findall(pattern, next_line)
                    if matches:
                        found_totals.append((i + 1, matches[0]))
                        
    if found_totals:
        # Return the first total amount detected
        extracted["total_amount"] = found_totals[0][1]
    else:
        # Fallback: scan whole text for currency patterns and pick the largest one (in invoices, total is usually the largest)
        all_amounts = []
        for pattern in amount_patterns:
            for match in re.findall(pattern, full_text):
                # Clean up formatting to extract raw integer
                num_str = re.sub(r'[^0-9]', '', match)
                if num_str:
                    all_amounts.append((match, int(num_str)))
        if all_amounts:
            # Sort by value descending and pick the largest that isn't a date/phone number outlier
            # Limit range to avoid capturing phone numbers
            valid_amounts = [a for a in all_amounts if a[1] < 1000000000] # less than 1 billion
            if valid_amounts:
                valid_amounts.sort(key=lambda x: x[1], reverse=True)
                extracted["total_amount"] = valid_amounts[0][0]
                
    return extracted
