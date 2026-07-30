"""VNPay Payment Gateway Integration (HMAC-SHA512 Signature Generation & Verification)."""

import hmac
import hashlib
from urllib.parse import urlencode, quote_plus
from typing import Dict, Any


def build_payment_url(
    vnpay_url: str,
    secret_key: str,
    tmn_code: str,
    order_code: str,
    amount: float,
    order_info: str,
    return_url: str,
    ip_address: str = "127.0.0.1",
    create_date_str: str = "",
) -> str:
    """Build signed VNPay Payment Redirect URL according to VNPay v2.1.0 specifications.

    Args:
        vnpay_url (str): Base VNPay gateway endpoint URL.
        secret_key (str): VNPay Hash Secret Key.
        tmn_code (str): VNPay Terminal / Merchant Code.
        order_code (str): Unique business order code reference.
        amount (float): Payment amount in VND (will be multiplied by 100).
        order_info (str): Transaction description info.
        return_url (str): Customer browser return redirect URL.
        ip_address (str): Customer client IP address.
        create_date_str (str): Date timestamp formatted as YYYYMMDDHHMMSS.

    Returns:
        str: Fully constructed and signed VNPay payment URL.
    """
    vnp_params: Dict[str, Any] = {
        "vnp_Version": "2.1.0",
        "vnp_Command": "pay",
        "vnp_TmnCode": tmn_code,
        "vnp_Amount": int(amount * 100),
        "vnp_CurrCode": "VND",
        "vnp_TxnRef": order_code,
        "vnp_OrderInfo": order_info,
        "vnp_OrderType": "other",
        "vnp_Locale": "vn",
        "vnp_ReturnUrl": return_url,
        "vnp_IpAddr": ip_address,
        "vnp_CreateDate": create_date_str,
    }

    # Sort parameters alphabetically by key
    sorted_params = sorted(vnp_params.items())

    # Build hash data string
    hash_data = "&".join(f"{k}={quote_plus(str(v))}" for k, v in sorted_params)

    # Compute HMAC-SHA512 signature
    signature = hmac.new(
        secret_key.encode("utf-8"),
        hash_data.encode("utf-8"),
        hashlib.sha512,
    ).hexdigest()

    # Build final query string
    query_string = urlencode(sorted_params) + f"&vnp_SecureHash={signature}"

    return f"{vnpay_url}?{query_string}"


def verify_signature(raw_payload: Dict[str, Any], secret_key: str) -> bool:
    """Verify VNPay IPN/Webhook HMAC-SHA512 checksum signature using constant-time comparison.

    Args:
        raw_payload (Dict[str, Any]): Dictionary of incoming query parameters or form payload.
        secret_key (str): Merchant secret hash key.

    Returns:
        bool: True if signature matches, False otherwise.
    """
    vnp_secure_hash = raw_payload.get("vnp_SecureHash") or raw_payload.get("vnp_secure_hash")
    if not vnp_secure_hash or not secret_key:
        return False

    # Extract all vnp_ params excluding hashes
    filtered_params = {
        k: v for k, v in raw_payload.items()
        if k.startswith("vnp_") and k not in ("vnp_SecureHash", "vnp_SecureHashType")
    }

    # Sort parameters by key
    sorted_params = sorted(filtered_params.items())

    # Build hash data string
    hash_data = "&".join(f"{k}={quote_plus(str(v))}" for k, v in sorted_params)

    # Compute expected HMAC-SHA512 hash
    calculated_hash = hmac.new(
        secret_key.encode("utf-8"),
        hash_data.encode("utf-8"),
        hashlib.sha512,
    ).hexdigest()

    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(calculated_hash.lower(), str(vnp_secure_hash).lower())
