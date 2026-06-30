# Workspace Rules

## Quy trình Làm việc và Gỡ lỗi (Troubleshooting Workflow)

- **Không tự đoán mò (Do Not Guess):** Khi gặp bất kỳ lỗi hệ thống, lỗi từ sâu bên trong thư viện (ví dụ: lỗi C++, `NotImplementedError`, core dump), tuyệt đối không được tự ý sửa file, đoán bừa cấu hình hay yêu cầu hạ cấp thư viện khi chưa có cơ sở.
- **Luôn tra cứu trước (Consult Internet First):** Bắt buộc phải dùng công cụ `search_web` để tìm kiếm chính xác thông báo lỗi trên GitHub Issues, StackOverflow hoặc tài liệu chính thức. Phải tìm ra nguyên nhân gốc rễ và giải pháp đã được cộng đồng kiểm chứng.
- **Lập kế hoạch trước khi hành động (Plan Before Action):** Sau khi tra cứu ra nguyên nhân, phải giải thích rõ ràng lý do cho người dùng hiểu và đề xuất phương án giải quyết (Kế hoạch) để người dùng phê duyệt TRƯỚC KHI thực sự chạy lệnh sửa code hay đổi cấu hình hệ thống.
- **Không bảo thủ:** Nếu một cách sửa đã thử mà vẫn không chạy, phải lập tức dừng lại, tìm kiếm thêm thông tin trên mạng thay vì cố chấp thử đi thử lại một hướng đi sai hoặc đổ lỗi cho môi trường.
