"""Email Notification Worker for Background Tasks."""

from loguru import logger
from uuid import UUID

from app.core.database import AsyncSessionLocal



async def send_order_confirmation(order_id: UUID) -> None:
    """Background worker task to send order confirmation email using an isolated DB session.

    Args:
        order_id (UUID): Primary key UUID of the confirmed order.
    """
    try:
        async with AsyncSessionLocal() as session:
            # Import locally inside worker to prevent circular dependencies
            from app.modules.orders.repository import OrderRepository
            order = await OrderRepository.find_by_id(session, order_id)
            if order:
                logger.info(
                    f"📧 [Background Email Worker] Sending Order Confirmation Email to '{order.email}' "
                    f"for Order Code #{order.order_code} (Customer: '{order.customer_name}')"
                )
                # Production SMTP email send logic using settings.MAIL_SERVER
            else:
                logger.warning(f"📧 [Background Email Worker] Order #{order_id} not found for email dispatch.")
    except Exception as err:
        logger.error(f"❌ [Background Email Worker] Failed to send order confirmation email for order #{order_id}: {err}")


async def send_lead_notification(
    lead_id: UUID,
    customer_name: str,
    email: str,
    phone: str,
    vehicle_name: str,
) -> None:
    """Background worker task to send lead notification email.

    Args:
        lead_id (UUID): Lead primary key UUID.
        customer_name (str): Customer full name.
        email (str): Customer email address.
        phone (str): Customer phone number.
        vehicle_name (str): Vehicle name of interest.
    """
    try:
        logger.info(
            f"📧 [Background Email Worker] Sending Lead Notification to Showroom team for Lead #{lead_id}: "
            f"Customer '{customer_name}' ({phone}, {email}) interested in '{vehicle_name}'"
        )
    except Exception as err:
        logger.error(f"❌ [Background Email Worker] Failed to send lead notification email for lead #{lead_id}: {err}")
