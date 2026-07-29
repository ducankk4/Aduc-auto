# API Contract Specification — Aduc Auto Backend

> **Base URL**: `/api/v1`  
> **Format**: JSON  
> **Authentication**: Bearer JWT (Access Token in `Authorization` Header)

---

## 1. Response Format Chuẩn (Standard Response Schema)

Toàn bộ Endpoint trong hệ thống đều trả về theo chuẩn nhất quán:

### Response Thành Công (2xx)
```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "page": 1,
    "limit": 12,
    "total": 50
  }
}
```
*Lưu ý: `meta` chỉ xuất hiện ở các Endpoint dạng Danh sách / Phân trang.*

### Response Lỗi (4xx / 5xx)
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE_NAME",
    "message": "Mô tả chi tiết bằng tiếng Việt cho người dùng/FE"
  }
}
```

---

## 2. Danh Sách API Endpoints Chi Tiết

### 2.1 Public Endpoints (Khách hàng & SEO — Không cần JWT)

#### `GET /api/v1/catalog/vehicles`
- **Mục đích**: Lấy danh sách mẫu xe đang kinh doanh (hỗ trợ phân trang)
- **Query Params**: `page=1`, `limit=12`, `search=`
- **Response 200**:
```json
{
  "success": true,
  "data": [
    {
      "id": "c3b8a1e2-...",
      "name": "VinFast VF 8",
      "slug": "vinfast-vf-8",
      "base_price": 1090000000,
      "deposit_amount": 50000000,
      "thumbnail_url": "https://..."
    }
  ],
  "meta": { "page": 1, "limit": 12, "total": 2 }
}
```

#### `GET /api/v1/catalog/vehicles/{slug}`
- **Mục đích**: Lấy thông tin chi tiết mẫu xe kèm toàn bộ `variants` và `colors`
- **Response 200**:
```json
{
  "success": true,
  "data": {
    "id": "c3b8a1e2-...",
    "name": "VinFast VF 8",
    "slug": "vinfast-vf-8",
    "base_price": 1090000000,
    "variants": [
      {
        "id": "v1-uuid",
        "name": "Eco",
        "price": 1090000000,
        "deposit_amount": 50000000,
        "spec_summary": { "battery_kwh": 87.7, "range_km": 471 }
      }
    ],
    "colors": [
      {
        "id": "c1-uuid",
        "name": "Trắng Brahmaputra",
        "hex_code": "#FFFFFF",
        "image_url": "https://...",
        "price_extra": 0
      }
    ]
  }
}
```

#### `POST /api/v1/auth/register`
- **Request Body**:
```json
{
  "email": "khachhang@gmail.com",
  "password": "Password123!",
  "full_name": "Nguyễn Văn A",
  "phone": "0987654321"
}
```
- **Response 201**: Trả về `UserResponse` (KHÔNG bao gồm password_hash).

#### `POST /api/v1/auth/login`
- **Request Body**:
```json
{
  "email": "khachhang@gmail.com",
  "password": "Password123!"
}
```
- **Response 200**:
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "d7a8b9c...",
    "token_type": "bearer",
    "expires_in": 14400
  }
}
```

#### `POST /api/v1/auth/refresh`
- **Request Body**: `{"refresh_token": "d7a8b9c..."}`
- **Response 200**: Trả `access_token` mới.

#### `POST /api/v1/leads`
- **Mục đích**: Khách hàng để lại thông tin tư vấn / Đăng ký lái thử
- **Rate Limit**: 10 requests/phút/IP
- **Request Body**:
```json
{
  "vehicle_id": "c3b8a1e2-...",
  "customer_name": "Nguyễn Văn A",
  "phone": "0987654321",
  "email": "khachhang@gmail.com",
  "showroom_pref": "VinFast Thảo Điền - TP.HCM"
}
```

#### `POST /api/v1/payments/webhook`
- **Mục đích**: Nhận IPN Callback từ VNPay Sandbox (Public Endpoint)
- **Lưu ý Quan trọng**: 
  1. Kiểm tra Chữ ký HMAC Signature trước. Nếu sai -> Log warning và trả `HTTP 200` (không trả 400).
  2. Idempotency Check: nếu `vnp_TransactionNo` đã được ghi nhận `success` trước đó -> Early Return HTTP 200 thành công ngay lập tức.
- **Response 200**: `{"RspCode": "00", "Message": "Confirm Success"}`

---

### 2.2 Customer Endpoints (Yêu cầu Authorization Header `Bearer <token>`)

#### `GET /api/v1/auth/me`
- **Response 200**: Chi tiết Profile người dùng đang đăng nhập.

#### `POST /api/v1/orders`
- **Mục đích**: Tạo mới đơn đặt cọc xe (Trạng thái khởi tạo: `pending`)
- **Request Body**:
```json
{
  "variant_id": "v1-uuid",
  "color_id": "c1-uuid",
  "customer_name": "Nguyễn Văn A",
  "phone": "0987654321",
  "email": "khachhang@gmail.com",
  "id_card": "012345678901"
}
```
- **Response 201**: Trả về `OrderResponse` kèm mã đơn `order_code`.

#### `GET /api/v1/orders/{order_code}`
- **Mục đích**: Tra cứu thông tin đơn cọc theo mã (Khách hàng chỉ xem được đơn của mình).

#### `POST /api/v1/payments/{order_id}/init`
- **Mục đích**: Khởi tạo URL chuyển hướng sang Cổng thanh toán VNPay Sandbox
- **Response 200**:
```json
{
  "success": true,
  "data": {
    "order_code": "ORD-20260729-A1B2C3",
    "payment_url": "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html?vnp_Amount=..."
  }
}
```

---

### 2.3 Admin Endpoints (Yêu cầu JWT + Permission tương ứng)

| Method | Path | Required Permission | Mô tả |
|---|---|---|---|
| `GET` | `/api/v1/admin/orders` | `orders:read` | Lấy danh sách đơn cọc (Filter status, date) |
| `PATCH` | `/api/v1/admin/orders/{id}/status` | `orders:update_status` | Cập nhật trạng thái đơn (Duyệt cọc, hủy cọc) |
| `POST` | `/api/v1/admin/catalog/vehicles` | `catalog:create` | Thêm mới mẫu xe |
| `PUT` | `/api/v1/admin/catalog/vehicles/{id}` | `catalog:update` | Cập nhật mẫu xe |
| `DELETE` | `/api/v1/admin/catalog/vehicles/{id}` | `catalog:delete` | Ẩn mẫu xe (`is_active = false`) |
| `GET` | `/api/v1/admin/leads` | `leads:read` | Xem danh sách Lead đăng ký tư vấn |
| `PATCH` | `/api/v1/admin/leads/{id}/status` | `leads:update` | Đánh dấu Lead (`contacted`, `test_driven`) |
| `GET` | `/api/v1/admin/users` | `users:manage` | Danh sách tài khoản hệ thống |
| `GET` | `/api/v1/admin/users/departments` | `users:manage` | Danh sách Showroom/Phòng ban |
| `GET/POST`| `/api/v1/admin/users/roles` | `roles:manage` | Quản lý Vai trò & Phân quyền |
| `GET` | `/api/v1/admin/audit-logs` | `audit_logs:read` | Tra cứu Nhật ký thao tác hệ thống |
| `GET` | `/api/v1/admin/menus` | Auto theo Role JWT | Lấy danh sách Menu UI động cho FE Sidebar |
