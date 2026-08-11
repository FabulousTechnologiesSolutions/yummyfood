import uuid

from django.conf import settings
from django.db import models
from django.utils.text import slugify


class ClaimStatus(models.TextChoices):
    OWNED = 'owned', 'Owned'
    UNCLAIMED = 'unclaimed', 'Unclaimed'
    PENDING_CLAIM = 'pending_claim', 'Pending claim'


class Restaurant(models.Model):
    """Restaurant profile owned by a user."""

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='restaurant',
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    short_description = models.TextField(blank=True, default='')
    cuisines = models.JSONField(default=list, blank=True)
    price_range = models.CharField(max_length=64, blank=True, default='')
    logo = models.ImageField(upload_to='restaurants/logos/', blank=True, null=True)
    cover = models.ImageField(upload_to='restaurants/covers/', blank=True, null=True)
    primary_phone = models.CharField(max_length=20, blank=True, default='')
    whatsapp_number = models.CharField(max_length=20, blank=True, default='')
    use_different_whatsapp = models.BooleanField(default=False)
    secondary_phone = models.CharField(max_length=20, blank=True, default='')
    street_address = models.CharField(max_length=255, blank=True, default='')
    area = models.CharField(max_length=120, blank=True, default='')
    city = models.ForeignKey(
        'geo.City',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='restaurants',
    )
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    rating_avg = models.DecimalField(max_digits=2, decimal_places=1, default=0)
    rating_count = models.PositiveIntegerField(default=0)
    rating_histogram = models.JSONField(default=dict, blank=True)
    is_paused = models.BooleanField(default=False)
    is_permanently_closed = models.BooleanField(default=False)
    claim_status = models.CharField(
        max_length=20,
        choices=ClaimStatus.choices,
        default=ClaimStatus.OWNED,
    )
    setup_checklist = models.JSONField(default=dict, blank=True)
    promo_default_radius_km = models.PositiveSmallIntegerField(default=5)
    promo_default_duration_days = models.PositiveSmallIntegerField(default=3)
    notify_on_promo_approval = models.BooleanField(default=True)
    auto_request_promo_on_deal = models.BooleanField(default=False)
    products_created_this_month = models.PositiveIntegerField(default=0)
    products_quota_month = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def setup_completeness_pct(self) -> int:
        has_menu = self.menu_items.filter(status='published').exists()
        checks = {
            'restaurant_created': True,
            'profile': bool(self.short_description and self.cuisines and self.price_range),
            'logo_cover': bool(self.logo and self.cover),
            'contact': bool(self.primary_phone),
            'address': bool(self.street_address and self.city_id and self.lat is not None and self.lng is not None),
            'menu': has_menu,
        }
        total = len(checks)
        done = sum(1 for v in checks.values() if v)
        return int(round(100 * done / total)) if total else 0

    @staticmethod
    def make_unique_slug(name: str) -> str:
        base = slugify(name)[:100] or 'restaurant'
        candidate = base
        while Restaurant.objects.filter(slug=candidate).exists():
            candidate = f'{base}-{uuid.uuid4().hex[:6]}'
        return candidate
