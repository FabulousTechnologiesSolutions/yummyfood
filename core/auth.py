from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken


class CustomJWTAuthentication(JWTAuthentication):
    """SimpleJWT authentication (token may carry active_mode claim)."""


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Adds active_mode / phone claims to access token."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['active_mode'] = getattr(user, 'active_mode', 'customer') or 'customer'
        token['phone_number'] = getattr(user, 'phone_number', '') or ''
        return token


def issue_tokens_for_user(user):
    """Return access/refresh strings with custom claims."""
    refresh = RefreshToken.for_user(user)
    refresh['active_mode'] = getattr(user, 'active_mode', 'customer') or 'customer'
    refresh['phone_number'] = getattr(user, 'phone_number', '') or ''
    access = refresh.access_token
    access['active_mode'] = refresh['active_mode']
    access['phone_number'] = refresh['phone_number']
    return {
        'access': str(access),
        'refresh': str(refresh),
    }
