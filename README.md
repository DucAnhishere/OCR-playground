# OCR Playground (Sân chơi Tiền xử lý Ảnh & Nhận diện Chữ Thực Chiến)

OCR Playground là một ứng dụng web tương tác trực quan được xây dựng nhằm giúp các nhà phát triển thử nghiệm, tối ưu hóa các bộ lọc tiền xử lý ảnh bằng **OpenCV**, so sánh hiệu năng giữa các động cơ OCR nổi tiếng (**EasyOCR** & **Tesseract**) và tìm hiểu quy trình trích xuất thông tin cấu trúc từ tài liệu thực tế (như hóa đơn, biên lai, danh thiếp).

Dự án được xây dựng với kiến trúc chuẩn mực, tuân thủ nguyên lý thiết kế SOLID, dễ dàng bảo trì và mở rộng động các bộ lọc hoặc động cơ OCR mới.

---

## ✨ Tính Năng Nổi Bật

1. **Xử lý ảnh trực tiếp (Live Preprocessing)**: Kéo trượt điều chỉnh các tham số OpenCV (độ tương phản, độ sáng, nhị phân hóa Otsu/Adaptive Threshold, dilation/erosion) và xem trước ảnh kết quả ngay lập tức trên UI.
2. **Tự động xoay thẳng ảnh (Auto-Deskew)**: Tự động phân tích hướng nghiêng của văn bản trên tài liệu và xoay thẳng lại góc chuẩn trước khi chạy OCR.
3. **Hợp nhất Bounding Box liền kề (Adjacent Box Merging)**: Backend tự động gom các hộp nhận diện cấp độ từ (word-level) nằm gần nhau và thẳng hàng thành các cụm từ/câu ngắn giúp hiển thị trực quan và tăng độ chính xác khi phân tích dữ liệu dạng bảng/cột.
4. **Đồng bộ hóa Cấu hình Động (Single Source of Truth)**: Toàn bộ thông số cấu hình mặc định được quản lý tập trung tại Backend (`schemas.py`). Frontend tự động fetch cấu hình này lúc khởi chạy để render UI, loại bỏ hoàn toàn việc trùng lặp khai báo.
5. **Động cơ OCR đa dạng (Engine Strategy Pattern)**: Chuyển đổi linh hoạt giữa **EasyOCR** (mô hình học sâu PyTorch, hỗ trợ tăng tốc GPU) và **Tesseract OCR** (động cơ OCR mã nguồn mở hiệu năng cao từ Google/HP).
6. **Trích xuất thông tin Hóa đơn (Heuristic Receipt Parsing)**: Tự động gom dòng chữ và lọc thông tin quan trọng như Tên cửa hàng, Email, Số điện thoại, Ngày tháng và Tổng tiền thanh toán.
7. **Trình tạo mẫu thử tự động (Sample Generator)**: Tự động sinh ảnh mẫu hóa đơn bị lệch góc (`skewed_receipt`) hoặc có bóng mờ loang lổ (`shadow_invoice`) để kiểm thử ngay lập tức.

---

## 🛠️ Cấu Trúc Kiến Trúc Dự Án

Mã nguồn được phân tách rõ ràng theo cấu trúc phân tầng:

```
ocr-playground/
├── backend/
│   ├── ocr_engines/            # Chức năng OCR được mô-đun hóa
│   │   ├── base.py             # Lớp trừu tượng BaseOCREngine
│   │   ├── easyocr_engine.py   # Triển khai EasyOCR & Cache logic
│   │   ├── tesseract_engine.py # Triển khai Tesseract OCR & Map ngôn ngữ
│   │   └── ocr_utils.py        # Thuật toán hợp nhất khung bao liền kề
│   ├── app.py                  # API router FastAPI & Điều phối
│   ├── schemas.py              # Các Request/Response model Pydantic
│   ├── image_filters.py        # Bộ lọc OpenCV (Grayscale, Threshold, Morphology)
│   ├── structured_parser.py    # Thuật toán Heuristic Parser tách hóa đơn
│   ├── requirements.txt        # Các thư viện Python cần thiết
│   └── test_backend.py         # Bộ kiểm thử tích hợp & thuật toán logic
├── frontend/
│   ├── src/
│   │   ├── components/         # Các component React tương tác
│   │   │   ├── BoundingBoxViewer.jsx # Vẽ bounding box đè lên ảnh
│   │   │   ├── ControlPanel.jsx      # Bảng trượt điều khiển OpenCV & OCR
│   │   │   ├── StructuredResult.jsx  # Hiển thị kết quả cấu trúc hóa đơn
│   │   │   └── LearnPanel.jsx        # Giáo trình trực quan lý thuyết xử lý ảnh
│   │   ├── App.jsx             # Điểm kết nối giao diện & luồng trạng thái
│   │   └── index.css           # CSS giao diện Glassmorphism và Dark Mode
├── setup.sh                    # Script cài đặt môi trường tự động
└── run.sh                      # Script khởi chạy song song FE & BE
```

---

## 🚀 Hướng Dẫn Cài Đặt & Khởi Chạy Nhanh

Bạn có thể chọn một trong hai cách dưới đây để chạy ứng dụng:

### Cách 1: Sử dụng Docker Compose (Khuyên dùng - Nhanh & Không cần cài thư viện)

Cách này sẽ tự động đóng gói toàn bộ môi trường Backend (FastAPI, OpenCV, Tesseract OCR, EasyOCR) và Frontend (Vite, React) vào các container độc lập.

1. **Khởi chạy ứng dụng**:
   Chạy lệnh sau tại thư mục gốc của dự án:
   ```bash
   docker compose up --build
   ```
   *Lệnh này sẽ tự động build các image cho Backend & Frontend, tải trước các mô hình EasyOCR (English & Vietnamese) và khởi chạy ứng dụng.*

2. **Truy cập ứng dụng**:
   - **Giao diện người dùng (Frontend)**: [http://localhost:5173](http://localhost:5173)
   - **Backend API**: [http://localhost:8000](http://localhost:8000)
   - Nhấn `Ctrl + C` để dừng cả hai container.

---

### Cách 2: Sử dụng Script cài đặt cục bộ (Local Setup)

Nếu bạn không muốn chạy bằng Docker, dự án cung cấp sẵn các shell script tự động cài đặt:

1. **Bước 1: Thiết lập môi trường tự động**:
   Mở terminal tại thư mục gốc của dự án và chạy lệnh:
   ```bash
   ./setup.sh
   ```
   *Script sẽ tự động kiểm tra Python 3, Node.js/npm, tạo môi trường ảo `.venv` cho Python, nâng cấp pip, cài đặt tất cả dependencies của cả Backend và Frontend.*

2. **Bước 2: Khởi chạy ứng dụng**:
   Chạy script khởi động:
   ```bash
   ./run.sh
   ```
   *Lệnh này sẽ khởi chạy cùng lúc server FastAPI (Cổng 8000) và Vite Dev Server (Cổng 5173). Logs của cả hai được hiển thị song song trên terminal của bạn. Để dừng cả hai server, bạn chỉ cần nhấn **`Ctrl + C`**.*

Sau khi khởi chạy thành công, truy cập giao diện tại: [http://localhost:5173](http://localhost:5173)

---

## 💡 Mở Rộng Động Cơ OCR Mới

Kiến trúc OCR của dự án áp dụng **Strategy Pattern**, cho phép bạn thêm một động cơ OCR mới cực kỳ dễ dàng mà không ảnh hưởng tới code hiện tại:
1. Tạo một lớp con kế thừa từ `BaseOCREngine` trong thư mục `backend/ocr_engines/` (ví dụ: `paddleocr_engine.py`):
   ```python
   from .base import BaseOCREngine
   import numpy as np

   class PaddleOCREngine(BaseOCREngine):
       def is_available(self) -> bool:
           # logic kiểm tra thư viện đã cài đặt chưa
           return True

       def run(self, img: np.ndarray, langs: list[str]) -> list[dict]:
           # Chạy mô hình và trả về danh sách các từ có định dạng:
           # [{"text": text, "confidence": conf, "box": {"x", "y", "w", "h"}}]
           return word_results
   ```
2. Đăng ký động cơ mới vào dictionary `ENGINES` trong file [`backend/ocr_engine.py`](file:///Users/testadmin/Desktop/Desktop-Mac/ocr-playground/backend/ocr_engine.py):
   ```python
   from ocr_engines.paddleocr_engine import PaddleOCREngine

   ENGINES = {
       "easyocr": EasyOCREngine(),
       "tesseract": TesseractEngine(),
       "paddleocr": PaddleOCREngine()  # Thêm dòng này!
   }
   ```
Toàn bộ logic tiền xử lý, thuật toán hợp nhất bounding box và giao diện frontend sẽ tự động tương thích 100%!
