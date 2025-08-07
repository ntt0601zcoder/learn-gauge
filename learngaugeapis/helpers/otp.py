import logging
import random
from enum import Enum
from django.core.cache import cache

class OTPPurpose(Enum):
    Session = "session"

def generate_otp(length: int, purpose: OTPPurpose, email: str) -> str:
    try:
        cache.delete_many(cache.keys(f"{purpose}:account:{email}:otp:*"))

        otp = str(random.randint(10**length, 10**(length + 1) - 1))
        cache.set(f"{purpose}:account:{email}:otp:{otp}", email, 3600)

        return otp
    except Exception as e:
        logging.getLogger().exception("generate_otp exc=%s", str(e))

def verify_otp(purpose: OTPPurpose, email: str, otp: str) -> bool:
    return cache.get(f"{purpose}:account:{email}:otp:{otp}", None) is not None