# RBAC Permission Matrix — Aduc Auto Backend

> **Mô hình Phân quyền**: Fine-grained RBAC (Role-Based Access Control)  
> **Định dạng Permission**: `resource:action` (ví dụ: `orders:update_status`, `catalog:create`)  
> **Cơ chế**: `users/service.py` cung cấp hàm `check_permission(user_id, "resource:action")` được inject vào FastAPI Router dưới dạng Dependency.

---

## 1. Ma Trận Quyền Hạn (Permission Matrix)

| Resource | Action | Permission Key | Admin | Sale Manager / Sale Staff | Customer | Guest (Public) |
|---|---|---|:---:|:---:|:---:|:---:|
| **catalog** | `read` | `catalog:read` | ✅ | ✅ | ✅ | ✅ |
| | `create` | `catalog:create` | ✅ | ❌ | ❌ | ❌ |
| | `update` | `catalog:update` | ✅ | ❌ | ❌ | ❌ |
| | `delete` | `catalog:delete` | ✅ | ❌ | ❌ | ❌ |
| **orders** | `read_own` | `orders:read_own` | ✅ | ✅ | ✅ (Chỉ đơn của mình) | ❌ |
| | `read_all` | `orders:read_all` | ✅ | ✅ (Theo Showroom) | ❌ | ❌ |
| | `create` | `orders:create` | ✅ | ✅ | ✅ | ❌ |
| | `update_status` | `orders:update_status` | ✅ | ✅ | ❌ | ❌ |
| | `cancel` | `orders:cancel` | ✅ | ❌ | ❌ | ❌ |
| **leads** | `read` | `leads:read` | ✅ | ✅ (Theo Showroom) | ❌ | ❌ |
| | `update` | `leads:update` | ✅ | ✅ (Theo Showroom) | ❌ | ❌ |
| **users** | `manage` | `users:manage` | ✅ | ❌ | ❌ | ❌ |
| **roles** | `manage` | `roles:manage` | ✅ | ❌ | ❌ | ❌ |
| **audit_logs**| `read` | `audit_logs:read` | ✅ | ❌ | ❌ | ❌ |

---

## 2. Quy Tắc Phạm Vi Dữ Liệu Theo Showroom / Department (Scope Rules)

- **Admin**: Có toàn quyền xem và thao tác trên mọi đơn hàng (`orders`) và yêu cầu tư vấn (`leads`) trên toàn hệ thống không phụ thuộc Showroom.
- **Sale Manager / Staff**:
  - Khi thực hiện `orders:read_all` hoặc `leads:read`, hệ thống tự động lọc các bản ghi thuộc Showroom (`department_id`) mà nhân viên đó đang được phân công (`user_departments`).
- **Customer**:
  - Chỉ có quyền truy vấn các đơn hàng mà `order.user_id == current_user.id`.

---

## 3. Ví Dụ Sử Dụng Trong Code Router (FastAPI Dependency)

```python
from app.core.dependencies import check_permission
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/admin/orders", tags=["Admin Orders"])

@router.patch("/{id}/status")
async def update_order_status(
    id: UUID,
    status: OrderStatusUpdateSchema,
    current_user = Depends(check_permission("orders", "update_status"))
):
    # Endpoint này chỉ cho phép User có permission "orders:update_status" truy cập
    pass
```
