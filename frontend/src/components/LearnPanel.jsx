import React from 'react';
import { BookOpen, HelpCircle, Layers, Award } from 'lucide-react';

const LearnPanel = () => {
  return (
    <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      
      <div style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '0.75rem' }}>
        <h3 className="viewer-title" style={{ margin: 0 }}>
          <BookOpen size={18} style={{ color: '#06b6d4' }} />
          Giáo Trình Thực Chiến & Kiến Thức OCR
        </h3>
      </div>

      <div className="learn-grid">
        
        {/* Grayscale */}
        <div className="concept-card">
          <h3>
            <Layers size={16} />
            1. Ảnh Xám (Grayscale Conversion)
          </h3>
          <p style={{ marginTop: '0.5rem' }}>
            Tại sao phải chuyển ảnh màu (RGB) về ảnh xám (1 kênh màu)?
            Hầu hết các bộ lọc phát hiện biên (edges) và phân tách chữ đều sử dụng cường độ sáng (Luminance) thay vì màu sắc.
            Công thức toán học OpenCV sử dụng để chuyển đổi:
            <code style={{ display: 'block', margin: '0.5rem 0', padding: '0.5rem', background: 'rgba(0,0,0,0.2)', borderRadius: '4px' }}>
              Y = 0.299*R + 0.587*G + 0.114*B
            </code>
            Việc này làm giảm kích thước dữ liệu ảnh đi 3 lần, giúp tăng tốc độ xử lý của mô hình AI ở bước sau.
          </p>
        </div>

        {/* Binarization / Adaptive Threshold */}
        <div className="concept-card">
          <h3>
            <HelpCircle size={16} />
            2. Nhị phân hóa (Adaptive Thresholding)
          </h3>
          <p style={{ marginTop: '0.5rem' }}>
            Nhị phân hóa biến ảnh xám thành ảnh chỉ có 2 màu đen và trắng tuyệt đối.
            Trong thực tế, do bóng đổ hoặc ánh sáng không đều (gradient lighting), việc dùng một **ngưỡng tĩnh (Binary Threshold)** sẽ làm mất chữ.
            <br />
            **Adaptive Threshold** giải quyết bằng cách tính ngưỡng cho *từng pixel* dựa trên trung bình có trọng số (Gaussian) của vùng lân cận kích thước <code>Block Size</code>.
            Nếu pixel tối hơn trung bình trừ đi <code>C</code>, nó được gán là đen, ngược lại là trắng.
          </p>
        </div>

        {/* Deskewing */}
        <div className="concept-card">
          <h3>
            <Layers size={16} />
            3. Chống Xoay Nghiêng (Deskewing)
          </h3>
          <p style={{ marginTop: '0.5rem' }}>
            Khi người dùng chụp nghiêng hóa đơn, mô hình OCR sẽ đọc nhầm dòng chữ hoặc trích xuất sai cấu trúc.
            Thuật toán Deskewing của chúng ta sử dụng hàm <code>cv2.minAreaRect</code>:
            <br />
            1. Đảo màu ảnh (chữ trắng, nền đen).
            2. Tìm tất cả các tọa độ điểm ảnh trắng (pixel của chữ).
            3. Dựng một **Hình chữ nhật có góc xoay nhỏ nhất** bao quanh các điểm đó.
            4. Trích xuất góc nghiêng và áp dụng **Ma trận biến đổi Affine** để xoay ảnh thẳng lại 0 độ.
          </p>
        </div>

        {/* Morphology */}
        <div className="concept-card">
          <h3>
            <Layers size={16} />
            4. Hình Thái Học (Morphological Operations)
          </h3>
          <p style={{ marginTop: '0.5rem' }}>
            Các phép toán hình thái học sử dụng một ma trận trượt gọi là **Kernel** để biến đổi cấu trúc chữ:
            <br />
            - **Giãn nở (Dilation)**: Tăng kích thước nét chữ trắng. Phép toán này cực kỳ hữu ích để **kết nối các nét chữ bị đứt quãng** do in ấn kém hoặc quét thiếu sáng.
            <br />
            - **Xói mòn (Erosion)**: Thu nhỏ nét chữ trắng, giúp **tách các ký tự dính liền** ra xa nhau để mô hình dễ nhận diện riêng lẻ.
          </p>
        </div>

      </div>

      {/* AI vs Classic */}
      <div className="concept-card" style={{ borderLeft: '4px solid #a855f7', background: 'rgba(168, 85, 247, 0.01)', padding: '1.25rem' }}>
        <h3 style={{ color: '#a855f7' }}>
          <Award size={18} />
          So sánh Triết lý: EasyOCR vs Tesseract
        </h3>
        <p style={{ marginTop: '0.5rem', fontSize: '0.9rem', color: '#9ca3af' }}>
          - **Tesseract (Classic)**: Dựa nhiều vào khâu phân đoạn từ (segmentation) truyền thống. Nếu ảnh bị nhiễu hoặc binarization kém, Tesseract sẽ hỏng hoàn toàn. Tuy nhiên, nó chạy siêu nhanh trên CPU đơn nhân.
          <br /><br />
          - **EasyOCR (Deep Learning)**: Sử dụng mô hình **CRAFT (Character Region Awareness for Text Detection)** để phát hiện vùng chữ. CRAFT không chỉ tìm hộp chữ mà còn dự đoán "mức độ liên kết" giữa các ký tự, cho phép nó phát hiện chữ nằm nghiêng, chữ viết tay, hoặc chữ cong trên chai lọ một cách chuẩn xác, chạy tăng tốc cực đỉnh trên GPU/MPS của máy Mac.
        </p>
      </div>

    </div>
  );
};

export default LearnPanel;
