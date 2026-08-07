import pytest
from rest_framework import status

from apps.accounts.models import AppMode
from apps.accounts.services.password_service import PasswordService


@pytest.mark.django_db
class TestPassword:
    def test_forgot_generic_for_unknown(self, api_client):
        res = api_client.post(
            '/api/auth/password/forgot/',
            {'phone_number': '+923009998877'},
            format='json',
        )
        assert res.status_code == 200

    def test_forgot_and_reset(self, api_client, customer_user):
        res = api_client.post(
            '/api/auth/password/forgot/',
            {'phone_number': customer_user.phone_number},
            format='json',
        )
        assert res.status_code == 200
        # Create known OTP via service helper (forgot sent random OTP to console)
        PasswordService().create_otp_for_tests(customer_user.phone_number, otp='654321')
        reset = api_client.post(
            '/api/auth/password/reset/',
            {
                'phone_number': customer_user.phone_number,
                'otp': '654321',
                'new_password': 'newsecret1',
                'confirm_password': 'newsecret1',
            },
            format='json',
        )
        assert reset.status_code == 200
        login = api_client.post(
            '/api/auth/login/',
            {'phone_number': customer_user.phone_number, 'password': 'newsecret1'},
            format='json',
        )
        assert login.status_code == 200

    def test_reset_mismatch(self, api_client, customer_user):
        PasswordService().create_otp_for_tests(customer_user.phone_number, otp='111111')
        res = api_client.post(
            '/api/auth/password/reset/',
            {
                'phone_number': customer_user.phone_number,
                'otp': '111111',
                'new_password': 'newsecret1',
                'confirm_password': 'othersecret',
            },
            format='json',
        )
        assert res.status_code == 400

    def test_reset_wrong_otp(self, api_client, customer_user):
        PasswordService().create_otp_for_tests(customer_user.phone_number, otp='111111')
        res = api_client.post(
            '/api/auth/password/reset/',
            {
                'phone_number': customer_user.phone_number,
                'otp': '000000',
                'new_password': 'newsecret1',
                'confirm_password': 'newsecret1',
            },
            format='json',
        )
        assert res.status_code == 400
