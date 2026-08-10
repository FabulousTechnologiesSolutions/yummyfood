from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema

from apps.accounts.models import AppMode
from apps.accounts.permissions import IsAuthenticatedAndActive
from apps.accounts.serializers import (
    AddRestaurantSerializer,
    CustomerNotificationSerializer,
    CustomerPreferenceSerializer,
    GuestMigrateSerializer,
    LoginSerializer,
    LogoutSerializer,
    MeUpdateSerializer,
    PasswordForgotSerializer,
    PasswordResetSerializer,
    RefreshSerializer,
    RegisterSerializer,
    RestaurantBrandingSerializer,
    RestaurantNotificationSerializer,
    RestaurantPreferenceSerializer,
    RestaurantProfileUpdateSerializer,
    SwitchRestaurantSerializer,
)
from apps.accounts.services import (
    AuthService,
    PasswordService,
    PreferenceService,
    ProfileService,
)
from core.auth import issue_tokens_for_user
from core.exceptions import AppAPIException


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=RegisterSerializer)
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        result = AuthService().register(
            phone_number=data['phone_number'],
            password=data['password'],
            signup_intent=data['signup_intent'],
            restaurant_name=data.get('restaurant_name') or None,
            session_key=data.get('session_key') or None,
        )
        return Response(result, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=LoginSerializer)
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        result = AuthService().login(
            phone_number=data['phone_number'],
            password=data['password'],
            session_key=data.get('session_key') or None,
        )
        return Response(result)


class RefreshView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=RefreshSerializer)
    def post(self, request):
        serializer = RefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            refresh = RefreshToken(serializer.validated_data['refresh'])
            user_id = refresh.get('user_id')
            from apps.accounts.models import User

            user = User.objects.get(pk=user_id)
            # Preserve/re-issue with current DB active_mode
            tokens = issue_tokens_for_user(user)
            # Blacklist old refresh if rotation desired for refresh endpoint
            try:
                refresh.blacklist()
            except AttributeError:
                pass
            return Response(tokens)
        except (TokenError, Exception) as exc:
            raise AppAPIException(
                code='INVALID_TOKEN',
                message='Invalid or expired refresh token.',
                status_code=401,
            ) from exc


class LogoutView(APIView):
    permission_classes = [IsAuthenticatedAndActive]

    @extend_schema(request=LogoutSerializer)
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AuthService().logout(
            user=request.user,
            refresh_token=serializer.validated_data['refresh'],
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordForgotView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=PasswordForgotSerializer)
    def post(self, request):
        serializer = PasswordForgotSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = PasswordService().forgot(phone_number=serializer.validated_data['phone_number'])
        return Response(result)


class PasswordResetView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=PasswordResetSerializer)
    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        result = PasswordService().reset(
            phone_number=data['phone_number'],
            otp=data['otp'],
            new_password=data['new_password'],
            confirm_password=data['confirm_password'],
        )
        return Response(result)


class MeView(APIView):
    permission_classes = [IsAuthenticatedAndActive]

    def get(self, request):
        return Response(AuthService().me(request.user))

    @extend_schema(request=MeUpdateSerializer)
    def patch(self, request):
        # Mode-scoped: customer mode can only update personal fields (always personal here).
        # Restaurant listing fields are not on this endpoint.
        serializer = MeUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        avatar = request.FILES.get('avatar')
        result = AuthService().update_me(
            user=request.user,
            display_name=serializer.validated_data.get('display_name'),
            avatar=avatar,
        )
        return Response(result)

    def delete(self, request):
        AuthService().soft_delete(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class GuestMigrateView(APIView):
    permission_classes = [IsAuthenticatedAndActive]

    @extend_schema(request=GuestMigrateSerializer)
    def post(self, request):
        serializer = GuestMigrateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = AuthService().migrate_guest(
            user=request.user,
            session_key=serializer.validated_data['session_key'],
        )
        return Response(result)


class PreferencesView(APIView):
    permission_classes = [IsAuthenticatedAndActive]

    def get(self, request):
        return Response(PreferenceService().get_preferences(request.user))

    def patch(self, request):
        if request.user.active_mode == AppMode.RESTAURANT:
            serializer = RestaurantPreferenceSerializer(data=request.data, partial=True)
        else:
            serializer = CustomerPreferenceSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        result = PreferenceService().update_preferences(
            request.user, serializer.validated_data
        )
        return Response(result)


class NotificationsView(APIView):
    permission_classes = [IsAuthenticatedAndActive]

    def get(self, request):
        return Response(PreferenceService().get_notifications(request.user))

    def patch(self, request):
        if request.user.active_mode == AppMode.RESTAURANT:
            serializer = RestaurantNotificationSerializer(data=request.data, partial=True)
        else:
            serializer = CustomerNotificationSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        result = PreferenceService().update_notifications(
            request.user, serializer.validated_data
        )
        return Response(result)


class ProfilesView(APIView):
    permission_classes = [IsAuthenticatedAndActive]

    def get(self, request):
        return Response(ProfileService().list_profiles(request.user))


class AddCustomerProfileView(APIView):
    permission_classes = [IsAuthenticatedAndActive]

    def post(self, request):
        result = ProfileService().add_customer_profile(request.user)
        return Response(result, status=status.HTTP_201_CREATED)


class AddRestaurantView(APIView):
    permission_classes = [IsAuthenticatedAndActive]

    @extend_schema(request=AddRestaurantSerializer)
    def post(self, request):
        serializer = AddRestaurantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = ProfileService().add_restaurant(
            user=request.user,
            name=serializer.validated_data['name'],
        )
        return Response(result, status=status.HTTP_201_CREATED)


class MeRestaurantView(APIView):
    """GET/PATCH owned restaurant profile."""

    permission_classes = [IsAuthenticatedAndActive]

    def get(self, request):
        return Response(
            ProfileService().get_restaurant_profile(user=request.user, request=request)
        )

    @extend_schema(request=RestaurantProfileUpdateSerializer)
    def patch(self, request):
        serializer = RestaurantProfileUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        result = ProfileService().update_restaurant_profile(
            user=request.user,
            data=serializer.validated_data,
            request=request,
        )
        return Response(result)


class RestaurantBrandingView(APIView):
    """Add or replace restaurant cover / logo (multipart)."""

    permission_classes = [IsAuthenticatedAndActive]

    @extend_schema(request=RestaurantBrandingSerializer)
    def post(self, request):
        serializer = RestaurantBrandingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = ProfileService().update_restaurant_branding(
            user=request.user,
            branding_type=serializer.validated_data['type'],
            image=serializer.validated_data['image'],
            request=request,
        )
        return Response(result)


class ConsoleAccessView(APIView):
    permission_classes = [IsAuthenticatedAndActive]

    def get(self, request):
        return Response(ProfileService().console_access(request.user))


class SwitchToCustomerView(APIView):
    permission_classes = [IsAuthenticatedAndActive]

    def post(self, request):
        result = ProfileService().switch_to_customer(request.user)
        return Response(result)


class SwitchToRestaurantView(APIView):
    permission_classes = [IsAuthenticatedAndActive]

    @extend_schema(request=SwitchRestaurantSerializer)
    def post(self, request):
        serializer = SwitchRestaurantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = ProfileService().switch_to_restaurant(
            user=request.user,
            restaurant_name=serializer.validated_data.get('restaurant_name') or None,
        )
        return Response(result)
