import time
import threading
from typing import Dict, Tuple
from app.config import settings


class DualKeyRateLimiter:
    """
    In-memory thread-safe rate limiter tracking failed login attempts
    across both Client IP and Phone Number keys to thwart brute-forcing.
    """
    def __init__(self):
        self._lock = threading.Lock()
        # key -> {"failures": int, "lockout_until": float, "last_attempt": float}
        self._entries: Dict[str, dict] = {}

    def _get_key(self, prefix: str, identifier: str) -> str:
        return f"{prefix}:{identifier.strip()}"

    def check_lockout(self, ip: str, phone: str) -> Tuple[bool, int]:
        """
        Check if either the IP or the phone number is currently locked out.
        Returns (is_locked: bool, remaining_seconds: int).
        """
        now = time.time()
        with self._lock:
            for key in [self._get_key("ip", ip), self._get_key("phone", phone)]:
                entry = self._entries.get(key)
                if entry and entry["lockout_until"] > now:
                    remaining = int(entry["lockout_until"] - now)
                    return True, remaining
        return False, 0

    def record_failure(self, ip: str, phone: str) -> Tuple[int, bool, int]:
        """
        Record a failed authentication attempt for both IP and phone.
        If failures reach threshold, locks out the identifier.
        Returns (current_max_failures: int, is_locked: bool, remaining_lockout_seconds: int).
        """
        now = time.time()
        max_failures = 0
        is_locked = False
        remaining = 0
        lockout_duration = settings.LOGIN_LOCKOUT_MINUTES * 60

        with self._lock:
            for key in [self._get_key("ip", ip), self._get_key("phone", phone)]:
                entry = self._entries.get(key)
                if not entry:
                    entry = {"failures": 1, "lockout_until": 0.0, "last_attempt": now}
                    self._entries[key] = entry
                else:
                    # If older than lockout duration and not locked, reset failures
                    if entry["lockout_until"] <= now and (now - entry["last_attempt"]) > lockout_duration:
                        entry["failures"] = 1
                    else:
                        entry["failures"] += 1
                    entry["last_attempt"] = now

                if entry["failures"] >= settings.LOGIN_MAX_FAILED_ATTEMPTS:
                    entry["lockout_until"] = now + lockout_duration
                    is_locked = True
                    remaining = int(lockout_duration)

                if entry["failures"] > max_failures:
                    max_failures = entry["failures"]

        return max_failures, is_locked, remaining

    def reset_failures(self, ip: str, phone: str) -> None:
        """
        Clear failure counts upon successful authentication.
        """
        with self._lock:
            self._entries.pop(self._get_key("ip", ip), None)
            self._entries.pop(self._get_key("phone", phone), None)


# Global singleton instance
login_rate_limiter = DualKeyRateLimiter()
