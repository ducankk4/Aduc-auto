# Product Requirements Document (PRD) — Car Deposit Platform (MVP)

> **Dự án**: Website Đặt Cọc Xe Ô Tô Trực Tuyến (Production-grade MVP)  
> **Tài liệu**: PRD - Giai đoạn 0 (Discovery & Business Requirement)  
> **Ngày tạo**: 28/07/2026  

---

## 1. Tổng Quan & Mục Tiêu (Overview & Vision)
Xây dựng nền tảng web thương mại điện tử chuyên biệt cho phép khách hàng tìm hiểu, chọn cấu hình (phiên bản, màu sắc, phụ kiện) và **đặt cọc xe ô tô trực tuyến** một cách nhanh chóng, minh bạch. Hệ thống tích hợp sẵn luồng thanh toán qua cổng điện tử, gửi xác nhận qua email và quản trị đơn hàng cho nhân viên bán hàng/admin.

### Mục tiêu MVP:
- **Tập trung chất lượng Production-grade**: Đầy đủ Auth, Payment Sandbox, Admin CMS, Email Service, Dockerized.
- **Phạm vi gọn nhẹ**: 1-2 dòng xe mẫu, mỗi dòng 2-3 phiên bản & màu sắc, 1 cổng thanh toán (VNPay/MoMo Sandbox).

---

## 2. Đối Tượng Sử Dụng (User Personas)

1. **Khách hàng cuối (Public User / Customer)**:
   - Khách xem thông tin xe, so sánh phiên bản, chọn màu sắc 3D/hình ảnh.
   - Tạo đơn đặt cọc, thanh toán giữ chỗ trực tuyến.
   - Tra cứu/Theo dõi trạng thái đơn hàng qua email & tài khoản.
   - Để lại thông tin yêu cầu tư vấn / đăng ký lái thử (Lead).

2. **Quản trị viên / Nhân viên Sale (Admin / Manager)**:
   - Quản lý catalog xe (thêm/sửa xe, phiên bản, giá cọc, màu sắc, tồn kho).
   - Xem và cập nhật trạng thái đơn đặt cọc (`pending` → `paid` → `confirmed` → `cancelled`).
   - Quản lý danh sách Lead tư vấn để liên hệ CSKH.

3. **Hệ thống AI Chatbot Agent (Tích hợp ở Giai đoạn 9)**:
   - Đọc dữ liệu xe/tồn kho/giá từ DB catalog để tư vấn cho khách.
   - Thu thập thông tin lead/đặt lịch lái thử tự động qua hội thoại chat.

---

## 3. Danh Sách Use Cases (User Stories)

### A. Luồng Khách Hàng (Customer Experience)
- **US-01 (Xem Catalog Xe)**: Khách hàng truy cập Landing Page có thể xem danh sách xe, thông số kỹ thuật cốt lõi, giá niêm yết và số tiền cần cọc trước.
- **US-02 (Cấu Hình & Chọn Xe)**: Khách chọn một mẫu xe -> chuyển sang giao diện chọn phiên bản (Base/Plus/Premium) và đổi màu sắc ngoại thất để xem phối cảnh tương ứng.
- **US-03 (Đặt Cọc)**: Khách điền thông tin cá nhân (Họ tên, SĐT, Email, CCCD) -> chọn phương thức thanh toán -> tạo đơn đặt cọc.
- **US-04 (Thanh Toán Trực Tuyến)**: Khách được chuyển sang cổng thanh toán (VNPay/MoMo Sandbox) để hoàn tất cọc -> quay về trang kết quả xác nhận.
- **US-05 (Nhận Email Xác Nhận)**: Sau khi cọc thành công, hệ thống gửi email xác nhận kèm Mã đơn hàng & thông tin hợp đồng đặt cọc giữ chỗ.
- **US-06 (Đăng Ký Tư Vấn / Lái Thử)**: Khách không muốn cọc ngay có thể để lại SĐT + Tên + Showroom gần nhất để nhận tư vấn.

### B. Luồng Quản Trị (Admin Dashboard)
- **US-07 (Đăng Nhập Admin)**: Admin đăng nhập bằng tài khoản được cấp (JWT Auth, Role `admin`).
- **US-08 (Quản Lý Catalog)**: Admin cập nhật giá cọc, thông số xe, hình ảnh màu sắc, bật/tắt hiển thị xe.
- **US-09 (Quản Lý Đơn Hàng)**: Admin duyệt đơn cọc, xác nhận đã nhận xe/bàn giao hoặc xử lý hoàn tiền nếu huỷ đơn.
- **US-10 (Quản Lý Lead)**: Admin xem danh sách khách đăng ký tư vấn, đánh dấu trạng thái "Đã liên hệ" / "Chăm sóc sau".

---

## 4. Phạm Vi MVP (Scope & Out of Scope)

### In-Scope (Làm trong MVP)
- [x] Landing page SEO-friendly (Next.js App Router).
- [x] Chọn cấu hình phiên bản & màu sắc xe.
- [x] Tạo đơn & thanh toán cọc qua Cổng thanh toán Sandbox (VNPay/MoMo).
- [x] Xử lý Webhook thanh toán an toàn (Verify signature, Idempotency).
- [x] Hệ thống tài khoản JWT (Customer & Admin).
- [x] Dashboard Admin quản lý Orders, Vehicles, Leads.
- [x] Gửi Email xác nhận cọc qua SMTP.
- [x] Tuân thủ cơ bản quy định Bảo vệ dữ liệu cá nhân (Checkbox Consent).

### Out-of-Scope (Không làm ở MVP)
- [ ] Multi-dealer / Multi-showroom (chọn đại lý phân phối phức tạp).
- [ ] Tích hợp làm hồ sơ vay ngân hàng / trả góp chi tiết.
- [ ] Tính năng so sánh 3D WebGL render nặng (dùng bộ ảnh tĩnh theo màu).
- [ ] Multi-language (chỉ hỗ trợ Tiếng Việt).

---

## 5. Yêu Cầu Phi Chức Năng (Non-Functional Requirements)

1. **Hiệu năng & SEO**:
   - Landing Page dùng SSR/SSG (Next.js) đạt điểm Lighthouse SEO > 90.
   - Thời gian phản hồi API backend < 200ms cho các tác vụ xem catalog.
2. **Bảo mật (Security & Compliance)**:
   - Không lưu trữ thông tin thẻ ngân hàng/tài khoản thanh toán trên hệ thống.
   - Áp dụng Rate limiting cho các public endpoints (tạo đơn, gửi lead form) tránh DDoS/spam.
   - Mã hoá mật khẩu bằng `bcrypt`/`argon2`.
   - Có chính sách thu thập PII rõ ràng (tuân thủ Nghị định 13/2023/NĐ-CP).
3. **Độ Tin Cậy & Tính Toàn Vẹn Dữ Liệu**:
   - Webhook thanh toán phải xử lý **Idempotent** (đảm bảo cổng gọi 2 lần trùng lặp không bị nhân đôi giao dịch).
   - Đơn hàng có State Machine chuẩn (`pending` -> `paid` -> `confirmed` / `cancelled`).
4. **Khả năng mở rộng**:
   - Cấu trúc Backend phân lớp rõ ràng (Layered Architecture: `api` -> `services` -> `repositories` -> `models`) sẵn sàng mở rộng module AI Agent về sau.
