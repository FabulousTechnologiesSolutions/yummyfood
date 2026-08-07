from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class ItemType(models.TextChoices):
    CHICKEN = 'Chicken', 'Chicken'
    BEEF = 'Beef', 'Beef'
    MUTTON = 'Mutton', 'Mutton'
    FISH = 'Fish', 'Fish'
    VEG = 'Veg', 'Veg'
    VEGETARIAN = 'Vegetarian', 'Vegetarian'
    EGG = 'Egg', 'Egg'
    MIXED = 'Mixed', 'Mixed'


class MenuItemStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    PUBLISHED = 'published', 'Published'
    HIDDEN = 'hidden', 'Hidden'


class MenuCategory(models.Model):
    """Global menu category shared across restaurants."""

    slug = models.SlugField(max_length=64, unique=True)
    name = models.CharField(max_length=120)
    icon = models.CharField(max_length=32, blank=True, default='')
    position = models.PositiveIntegerField(default=0)
    is_visible = models.BooleanField(default=True)

    class Meta:
        ordering = ['position', 'id']
        verbose_name_plural = 'menu categories'

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='menu_items',
    )
    categories = models.ManyToManyField(
        MenuCategory,
        blank=True,
        related_name='menu_items',
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, default='')
    subcategory = models.CharField(max_length=80, blank=True, default='')
    item_type = models.CharField(
        max_length=20,
        choices=ItemType.choices,
        blank=True,
        default='',
    )
    quantity_label = models.CharField(max_length=80, blank=True, default='')
    sku = models.CharField(max_length=40, blank=True, default='')
    is_available = models.BooleanField(default=True)
    is_popular = models.BooleanField(default=False)
    is_new = models.BooleanField(default=False)
    spicy_level = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(3)],
    )
    prep_time_min = models.PositiveSmallIntegerField(null=True, blank=True)
    calories = models.PositiveIntegerField(null=True, blank=True)
    emoji = models.CharField(max_length=16, blank=True, default='')
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20,
        choices=MenuItemStatus.choices,
        default=MenuItemStatus.PUBLISHED,
    )
    published_at = models.DateTimeField(null=True, blank=True)
    is_promoted = models.BooleanField(default=False)
    promoted_starts_at = models.DateTimeField(null=True, blank=True)
    promoted_ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(
                fields=['is_promoted', 'promoted_ends_at'],
                name='menuitem_promo_ends_idx',
            ),
        ]

    def __str__(self):
        return self.name


class MenuItemSize(models.Model):
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name='sizes',
    )
    label = models.CharField(max_length=40)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    offer_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['position', 'id']

    def __str__(self):
        return f'{self.label} @ {self.price}'

    @property
    def effective_price(self):
        if self.offer_price is not None:
            return self.offer_price
        return self.price
