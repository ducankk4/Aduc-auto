"""Database Table Initialization and VinFast Real Data Seeding Script."""

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

# Ensure UTF-8 output encoding for Windows terminal
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add backend/src to PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from sqlalchemy import select
from app.core.database import engine, AsyncSessionLocal, Base
from app.core.security import hash_password
from app.modules.users.model import (
    UserModel,
    RoleModel,
    PermissionModel,
    DepartmentModel,
)
from app.modules.users.constants import DefaultRole
from app.modules.catalog.model import VehicleModel, VariantModel, ColorModel, OptionModel
from app.modules.leads.model import LeadModel
from app.modules.orders.model import OrderModel, OrderStatusHistory
from app.modules.payments.model import PaymentModel
from app.core.audit import AuditLogModel


async def init_and_seed_db():
    """Create database tables and populate realistic VinFast VF 8 seed data."""
    print("[INIT] Initializing database tables...")
    async with engine.begin() as conn:
        # Create all tables defined in ORM Models
        await conn.run_sync(Base.metadata.create_all)
    print("[SUCCESS] Tables created successfully.")

    async with AsyncSessionLocal() as session:
        # 1. Seed Permissions
        print("[SEED] Seeding initial permissions...")
        permissions_data = [
            ("users", "read"),
            ("users", "write"),
            ("users", "delete"),
            ("roles", "manage"),
            ("leads", "read"),
            ("leads", "write"),
            ("orders", "read"),
            ("orders", "write"),
            ("orders", "update_status"),
            ("catalog", "read"),
            ("catalog", "write"),
        ]

        permission_objs = {}
        for resource, action in permissions_data:
            stmt = select(PermissionModel).where(
                PermissionModel.resource == resource,
                PermissionModel.action == action,
            )
            result = await session.execute(stmt)
            perm = result.scalar_one_or_none()
            if not perm:
                perm = PermissionModel(resource=resource, action=action)
                session.add(perm)
                await session.flush()
            permission_objs[f"{resource}:{action}"] = perm

        # 2. Seed Roles
        print("[SEED] Seeding default roles...")
        roles_config = {
            DefaultRole.ADMIN: ("System Administrator", list(permission_objs.values())),
            DefaultRole.SALE: ("Sales Representative", [
                permission_objs["leads:read"],
                permission_objs["leads:write"],
                permission_objs["orders:read"],
                permission_objs["orders:write"],
                permission_objs["orders:update_status"],
                permission_objs["catalog:read"],
            ]),
            DefaultRole.CUSTOMER: ("Customer / Buyer", [
                permission_objs["catalog:read"],
                permission_objs["orders:read"],
                permission_objs["orders:write"],
            ]),
        }

        role_objs = {}
        for role_name, (desc, perms) in roles_config.items():
            stmt = select(RoleModel).where(RoleModel.name == role_name)
            result = await session.execute(stmt)
            role = result.scalar_one_or_none()
            if not role:
                role = RoleModel(name=role_name, description=desc, permissions=perms)
                session.add(role)
                await session.flush()
            else:
                role.permissions = perms
            role_objs[role_name] = role

        # 3. Seed Departments
        print("[SEED] Seeding departments...")
        depts_data = ["Ban Giám Đốc VinFast", "Showroom Kinh Doanh VinFast", "Trung Tâm Dịch Vụ & Bảo Hành"]
        dept_objs = {}
        for dept_name in depts_data:
            stmt = select(DepartmentModel).where(DepartmentModel.name == dept_name)
            result = await session.execute(stmt)
            dept = result.scalar_one_or_none()
            if not dept:
                dept = DepartmentModel(name=dept_name)
                session.add(dept)
                await session.flush()
            dept_objs[dept_name] = dept

        # 4. Seed User Accounts
        print("[SEED] Seeding user accounts...")

        # Admin Account
        stmt = select(UserModel).where(UserModel.email == "admin@aduc-auto.com")
        result = await session.execute(stmt)
        if not result.scalar_one_or_none():
            admin_user = UserModel(
                email="admin@aduc-auto.com",
                username="admin_vinfast",
                password_hash=hash_password("Admin@123456"),
                full_name="Quản Trị Viên VinFast Auto",
                phone="0901234567",
                is_active=True,
                role_id=role_objs[DefaultRole.ADMIN].id,
                department_id=dept_objs["Ban Giám Đốc VinFast"].id,
            )
            session.add(admin_user)

        # Sale Account
        stmt = select(UserModel).where(UserModel.email == "sale@aduc-auto.com")
        result = await session.execute(stmt)
        if not result.scalar_one_or_none():
            sale_user = UserModel(
                email="sale@aduc-auto.com",
                username="sale_vinfast",
                password_hash=hash_password("Sale@123456"),
                full_name="Nguyễn Văn Sale VinFast",
                phone="0987654321",
                is_active=True,
                role_id=role_objs[DefaultRole.SALE].id,
                department_id=dept_objs["Showroom Kinh Doanh VinFast"].id,
            )
            session.add(sale_user)

        # 5. Seed Real VinFast VF 8 Catalog Data
        print("[SEED] Seeding VinFast VF 8 Vehicle, Variants, Colors & Options...")
        stmt = select(VehicleModel).where(VehicleModel.slug == "vinfast-vf-8-all-new")
        result = await session.execute(stmt)
        vf8_vehicle = result.scalar_one_or_none()

        if not vf8_vehicle:
            vf8_vehicle = VehicleModel(
                name="VinFast VF 8 All-New",
                slug="vinfast-vf-8-all-new",
                category="suv",
                description=(
                    "Mẫu xe SUV điện thông minh phân khúc D đẳng cấp toàn cầu của VinFast. "
                    "Thiết kế bởi Studio danh tiếng Pininfarina (Ý), trang bị động cơ điện 2 cầu AWD, "
                    "hệ thống hỗ trợ lái nâng cao ADAS Level 2 và gói dịch vụ thông minh VF Smart Services."
                ),
                base_price=Decimal("1090000000.00"),
                is_active=True,
            )

            # Variants (VF 8 Eco & VF 8 Plus)
            vf8_vehicle.variants.extend([
                VariantModel(
                    name="VinFast VF 8 Eco (Thuê pin)",
                    sku="VF8-ECO-BATTERY-RENTAL",
                    price=Decimal("1090000000.00"),
                    specs={
                        "power": "349 hp (260 kW)",
                        "torque": "500 Nm",
                        "drivetrain": "AWD (2 cầu toàn thời gian)",
                        "range_wltp": "471 km / lần sạc",
                        "acceleration_0_100": "5.5 giây",
                        "screen": "15.6 inch Touchscreen",
                        "adas": "Level 2 (Hỗ trợ di chuyển khi ùn tắc, Hỗ trợ lái trên đường cao tốc)",
                        "battery_option": "Gói thuê pin linh hoạt/cố định",
                    },
                ),
                VariantModel(
                    name="VinFast VF 8 Eco (Mua kèm pin)",
                    sku="VF8-ECO-BATTERY-INCLUDED",
                    price=Decimal("1290000000.00"),
                    specs={
                        "power": "349 hp (260 kW)",
                        "torque": "500 Nm",
                        "drivetrain": "AWD (2 cầu toàn thời gian)",
                        "range_wltp": "471 km / lần sạc",
                        "acceleration_0_100": "5.5 giây",
                        "screen": "15.6 inch Touchscreen",
                        "adas": "Level 2",
                        "battery_option": "Sở hữu pin CATL / LFP cao cấp",
                    },
                ),
                VariantModel(
                    name="VinFast VF 8 Plus (Thuê pin)",
                    sku="VF8-PLUS-BATTERY-RENTAL",
                    price=Decimal("1270000000.00"),
                    specs={
                        "power": "402 hp (300 kW)",
                        "torque": "620 Nm",
                        "drivetrain": "AWD (2 cầu toàn thời gian)",
                        "range_wltp": "447 km / lần sạc",
                        "acceleration_0_100": "5.5 giây",
                        "screen": "15.6 inch Touchscreen",
                        "sunroof": "Cửa sổ trời toàn cảnh Panorama",
                        "seats": "Da Nappa cao cấp sưởi & thông gió",
                        "battery_option": "Gói thuê pin linh hoạt/cố định",
                    },
                ),
                VariantModel(
                    name="VinFast VF 8 Plus (Mua kèm pin)",
                    sku="VF8-PLUS-BATTERY-INCLUDED",
                    price=Decimal("1470000000.00"),
                    specs={
                        "power": "402 hp (300 kW)",
                        "torque": "620 Nm",
                        "drivetrain": "AWD (2 cầu toàn thời gian)",
                        "range_wltp": "447 km / lần sạc",
                        "acceleration_0_100": "5.5 giây",
                        "sunroof": "Cửa sổ trời toàn cảnh Panorama",
                        "seats": "Da Nappa cao cấp sưởi & thông gió",
                        "battery_option": "Sở hữu pin CATL / LFP cao cấp",
                    },
                ),
            ])

            # Exterior Colors
            vf8_vehicle.colors.extend([
                ColorModel(name="Trắng Brahminy White", color_code="#FFFFFF", price_extra=Decimal("0.00")),
                ColorModel(name="Đen Jet Black", color_code="#0A0A0A", price_extra=Decimal("0.00")),
                ColorModel(name="Bạc Desat Silver", color_code="#C0C0C0", price_extra=Decimal("0.00")),
                ColorModel(name="Đỏ Crimson Red", color_code="#B22222", price_extra=Decimal("0.00")),
                ColorModel(name="Xanh VinFast Blue", color_code="#1E3A8A", price_extra=Decimal("0.00")),
                ColorModel(name="Xám Neptune Grey", color_code="#4A5568", price_extra=Decimal("0.00")),
                ColorModel(name="Cam Sunset Orange", color_code="#DD6B20", price_extra=Decimal("0.00")),
            ])

            # Optional Accessories
            vf8_vehicle.options.extend([
                OptionModel(
                    name="Bộ sạc di động VinFast Portable Charger (3.5 kW)",
                    price=Decimal("6000000.00"),
                ),
                OptionModel(
                    name="Bộ sạc treo tường thông minh VinFast Home Charger (7.4 kW)",
                    price=Decimal("12000000.00"),
                ),
            ])

            session.add(vf8_vehicle)

        await session.commit()
        print("[SUCCESS] VinFast VF 8 database seeded successfully!")


if __name__ == "__main__":
    asyncio.run(init_and_seed_db())
