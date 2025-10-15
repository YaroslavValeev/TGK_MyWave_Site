"""Payment provider adapters and webhook signature verification helpers.

This module provides light-weight, dependency-free stubs and a generic
HMAC-based signature verifier. For each real provider integrate their
official SDK and implement the proper signature algorithm.

Environment variables to set for production:
 - YOOKASSA_SECRET
 - CLOUDPAYMENTS_SECRET

The verifier looks for common header names (X-Signature, X-CloudPayments-Signature,
Content-Hmac) and will validate HMAC-SHA256 over the raw request body.
"""
import os
import hmac
import hashlib
from typing import Optional
import base64


class BaseProvider:
    name = 'base'

    @classmethod
    def verify_signature(cls, headers: dict, body: bytes) -> bool:
        """Default: no signature required (sandbox)."""
        return True


class CloudPaymentsProvider(BaseProvider):
    name = 'cloudpayments'

    @classmethod
    def secret(cls) -> Optional[str]:
        return os.environ.get('CLOUDPAYMENTS_SECRET')

    @classmethod
    def verify_signature(cls, headers: dict, body: bytes) -> bool:
        secret = cls.secret()
        if not secret:
            # no secret configured -> treat as non-strict (dev)
            return True

        # Normalize headers: accept different header names
        lookup_keys = ['x-cloudpayments-signature', 'content-hmac', 'x-signature', 'x-cloudpayments-sign']
        sig = None
        for k in lookup_keys:
            for hk, hv in headers.items():
                if hk.lower() == k:
                    sig = hv
                    break
            if sig:
                break

        if not sig:
            return False

        # Common formats: hex digest, base64, or prefixed like 'sha256=...'
        sig = sig.strip()
        if sig.startswith('sha256='):
            sig = sig.split('=', 1)[1]

        # Compute expected HMAC-SHA256 hex and base64
        expected_hex = hmac.new(secret.encode('utf-8'), body, hashlib.sha256).hexdigest()
        try:
            expected_b64 = base64.b64encode(bytes.fromhex(expected_hex)).decode('ascii')
        except Exception:
            expected_b64 = ''

        # Accept either hex or base64 (case-insensitive for hex compare using lower())
        if hmac.compare_digest(expected_hex, sig.lower()):
            return True
        if expected_b64 and hmac.compare_digest(expected_b64, sig):
            return True
        return False


class YooKassaProvider(BaseProvider):
    name = 'yookassa'

    @classmethod
    def secret(cls) -> Optional[str]:
        return os.environ.get('YOOKASSA_SECRET')

    @classmethod
    def verify_signature(cls, headers: dict, body: bytes) -> bool:
        # YooKassa uses its own signature method; for now use HMAC fallback
        secret = cls.secret()
        if not secret:
            return True

        sig = headers.get('X-Signature') or headers.get('X-Yoo-Signature')
        if not sig:
            return False

        digest = hmac.new(secret.encode('utf-8'), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(digest, sig)


PROVIDERS = {
    'cloudpayments': CloudPaymentsProvider,
    'yookassa': YooKassaProvider,
    'sandbox': BaseProvider,
}


def get_provider(name: str):
    return PROVIDERS.get((name or '').lower(), BaseProvider)
