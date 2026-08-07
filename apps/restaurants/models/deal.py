from django.db import models


class DealStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    ACTIVE = 'active', 'Active'
    ENDED = 'ended', 'Ended'
    HIDDEN = 'hidden', 'Hidden'


class Deal(models.Model):
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='deals',
    )
    label = models.CharField(max_length=120)
    description = models.TextField(blank=True, default='')
    deal_price = models.DecimalField(max_digits=10, decimal_places=2)
    items_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    savings_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    savings_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    days_of_week = models.JSONField(default=list, blank=True)
    terms = models.TextField(blank=True, default='')
    status = models.CharField(
        max_length=20,
        choices=DealStatus.choices,
        default=DealStatus.ACTIVE,
    )
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
                name='deal_promo_ends_idx',
            ),
        ]

    def __str__(self):
        return self.label


class DealLine(models.Model):
    deal = models.ForeignKey(
        Deal,
        on_delete=models.CASCADE,
        related_name='lines',
    )
    menu_item = models.ForeignKey(
        'restaurants.MenuItem',
        on_delete=models.PROTECT,
        related_name='deal_lines',
    )
    size_label = models.CharField(max_length=40)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveSmallIntegerField(default=1)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['position', 'id']

    def __str__(self):
        return f'{self.menu_item_id} x{self.quantity}'
