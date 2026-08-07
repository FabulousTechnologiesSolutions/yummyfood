import factory
from django.contrib.auth import get_user_model

from apps.accounts.models import (
    AppMode,
    CustomerNotificationSetting,
    CustomerPreference,
    CustomerProfile,
    GuestSession,
    RestaurantNotificationSetting,
    RestaurantPreference,
    SignupIntent,
)
from apps.accounts.services.seeding import seed_customer_side, seed_restaurant_side
from apps.restaurants.models import ClaimStatus, Restaurant
from core.auth import issue_tokens_for_user

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    phone_number = factory.Sequence(lambda n: f'+92300000{n:04d}')
    display_name = factory.Faker('name')
    signup_intent = SignupIntent.CUSTOMER
    active_mode = AppMode.CUSTOMER
    last_active_mode = AppMode.CUSTOMER

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        self.set_password(extracted or 'secret123')
        if create:
            self.save()


class CustomerProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CustomerProfile

    user = factory.SubFactory(UserFactory)

    @factory.post_generation
    def seed(self, create, extracted, **kwargs):
        if create:
            seed_customer_side(self)


class RestaurantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Restaurant

    owner = factory.SubFactory(
        UserFactory,
        signup_intent=SignupIntent.RESTAURANT,
        active_mode=AppMode.RESTAURANT,
        last_active_mode=AppMode.RESTAURANT,
    )
    name = factory.Sequence(lambda n: f'Restaurant {n}')
    slug = factory.Sequence(lambda n: f'restaurant-{n}')
    claim_status = ClaimStatus.OWNED

    @factory.post_generation
    def seed(self, create, extracted, **kwargs):
        if create:
            seed_restaurant_side(self)


def CustomerOnlyUserFactory(**kwargs):
    user = UserFactory(
        signup_intent=SignupIntent.CUSTOMER,
        active_mode=AppMode.CUSTOMER,
        last_active_mode=AppMode.CUSTOMER,
        **kwargs,
    )
    CustomerProfileFactory(user=user)
    return user


def RestaurantOnlyUserFactory(**kwargs):
    user = UserFactory(
        signup_intent=SignupIntent.RESTAURANT,
        active_mode=AppMode.RESTAURANT,
        last_active_mode=AppMode.RESTAURANT,
        **kwargs,
    )
    RestaurantFactory(owner=user)
    return user


def BothProfilesUserFactory(active_mode=AppMode.CUSTOMER, **kwargs):
    user = UserFactory(
        signup_intent=SignupIntent.CUSTOMER,
        active_mode=active_mode,
        last_active_mode=active_mode,
        **kwargs,
    )
    CustomerProfileFactory(user=user)
    RestaurantFactory(owner=user, name=f'{user.phone_number}-resto')
    return user


def AdminUserFactory(**kwargs):
    return UserFactory(is_staff=True, is_superuser=True, **kwargs)


class GuestSessionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GuestSession

    session_key = factory.Sequence(lambda n: f'guest-session-{n}')


def access_token_for(user, active_mode=None):
    if active_mode:
        user.active_mode = active_mode
        user.save(update_fields=['active_mode'])
    return issue_tokens_for_user(user)['access']
