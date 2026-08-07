import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import PasswordResetOTP, User
from apps.accounts.services.sms import get_sms_sender
from core.exceptions import AppAPIException
from core.utils import normalize_phone


class PasswordService:
    def __init__(self):
        self.sms = get_sms_sender()
        self.ttl_minutes = int(getattr(settings, 'OTP_TTL_MINUTES', 10))
        self.max_verify = int(getattr(settings, 'OTP_MAX_VERIFY_ATTEMPTS', 5))
        self.resend_cooldown_seconds = 60

    def _hash_otp(self, otp: str) -> str:
        return hashlib.sha256(otp.encode('utf-8')).hexdigest()

    @transaction.atomic
    def forgot(self, *, phone_number: str) -> dict:
        phone = normalize_phone(phone_number)
        # Always return generic success to avoid phone enumeration.
        generic = {
            'message': 'If an account exists for this phone, an OTP has been sent.',
        }
        try:
            user = User.objects.get(phone_number=phone, deleted_at__isnull=True, is_active=True)
        except User.DoesNotExist:
            return generic

        recent = (
            PasswordResetOTP.objects.filter(phone_number=phone, used_at__isnull=True)
            .order_by('-created_at')
            .first()
        )
        if recent and (timezone.now() - recent.created_at).total_seconds() < self.resend_cooldown_seconds:
            raise AppAPIException(
                code='OTP_COOLDOWN',
                message='Please wait before requesting another OTP.',
                status_code=429,
            )

        otp = f'{secrets.randbelow(1_000_000):06d}'
        PasswordResetOTP.objects.create(
            phone_number=phone,
            otp_hash=self._hash_otp(otp),
            expires_at=timezone.now() + timedelta(minutes=self.ttl_minutes),
        )
        self.sms.send(phone, f'Your FoodApp reset code is {otp}')
        # Attach otp in DEBUG for tests only via details? Prefer not to leak.
        # Tests will hash/create OTPs directly or monkeypatch sms.
        return generic

    @transaction.atomic
    def reset(
        self,
        *,
        phone_number: str,
        otp: str,
        new_password: str,
        confirm_password: str,
    ) -> dict:
        phone = normalize_phone(phone_number)
        if new_password != confirm_password:
            raise AppAPIException(
                code='PASSWORD_MISMATCH',
                message='Passwords do not match.',
                status_code=400,
            )
        if len(new_password) < 8:
            raise AppAPIException(
                code='INVALID_PASSWORD',
                message='Password must be at least 8 characters.',
                status_code=400,
            )

        record = (
            PasswordResetOTP.objects.filter(phone_number=phone, used_at__isnull=True)
            .order_by('-created_at')
            .first()
        )
        if record is None:
            raise AppAPIException(code='OTP_INVALID', message='Invalid OTP.', status_code=400)
        if record.expires_at < timezone.now():
            raise AppAPIException(code='OTP_EXPIRED', message='OTP has expired.', status_code=400)
        if record.attempts >= self.max_verify:
            raise AppAPIException(code='OTP_INVALID', message='Invalid OTP.', status_code=400)

        if record.otp_hash != self._hash_otp(otp):
            record.attempts += 1
            record.save(update_fields=['attempts'])
            raise AppAPIException(code='OTP_INVALID', message='Invalid OTP.', status_code=400)

        try:
            user = User.objects.get(phone_number=phone, deleted_at__isnull=True)
        except User.DoesNotExist:
            raise AppAPIException(code='OTP_INVALID', message='Invalid OTP.', status_code=400)

        user.set_password(new_password)
        user.save(update_fields=['password'])
        record.used_at = timezone.now()
        record.save(update_fields=['used_at'])
        return {'message': 'Password updated successfully.'}

    # Test helper
    def create_otp_for_tests(self, phone: str, otp: str = '123456') -> PasswordResetOTP:
        phone = normalize_phone(phone)
        return PasswordResetOTP.objects.create(
            phone_number=phone,
            otp_hash=self._hash_otp(otp),
            expires_at=timezone.now() + timedelta(minutes=self.ttl_minutes),
        )
