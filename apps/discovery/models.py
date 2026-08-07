from django.conf import settings
from django.db import models


class ExploreViewerState(models.Model):
    """Per-viewer rotation offsets for Explore (auth user XOR guest ip_hash)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='explore_viewer_state',
    )
    ip_hash = models.CharField(max_length=64, null=True, blank=True, unique=True)
    promoted_rotate_offset = models.PositiveIntegerField(default=0)
    organic_item_rotate_offset = models.PositiveIntegerField(default=0)
    organic_deal_rotate_offset = models.PositiveIntegerField(default=0)
    last_rotated_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(user__isnull=False, ip_hash__isnull=True)
                    | models.Q(user__isnull=True, ip_hash__isnull=False)
                ),
                name='explore_viewer_user_xor_ip',
            ),
        ]

    def __str__(self):
        if self.user_id:
            return f'ExploreViewerState<user={self.user_id}>'
        return f'ExploreViewerState<ip={self.ip_hash}>'


class ExploreImpression(models.Model):
    """Per-viewer serve history for rotation fairness (not used for ranking score)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='explore_impressions',
    )
    ip_hash = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    menu_item = models.ForeignKey(
        'restaurants.MenuItem',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='explore_impressions',
    )
    deal = models.ForeignKey(
        'restaurants.Deal',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='explore_impressions',
    )
    serve_count = models.PositiveIntegerField(default=0)
    first_served_at = models.DateTimeField(auto_now_add=True)
    last_served_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(user__isnull=False, ip_hash__isnull=True)
                    | models.Q(user__isnull=True, ip_hash__isnull=False)
                ),
                name='explore_impr_user_xor_ip',
            ),
            models.CheckConstraint(
                check=(
                    models.Q(menu_item__isnull=False, deal__isnull=True)
                    | models.Q(menu_item__isnull=True, deal__isnull=False)
                ),
                name='explore_impr_exactly_one_resource',
            ),
            models.UniqueConstraint(
                fields=['user', 'menu_item'],
                condition=models.Q(user__isnull=False, menu_item__isnull=False),
                name='unique_explore_impr_user_item',
            ),
            models.UniqueConstraint(
                fields=['user', 'deal'],
                condition=models.Q(user__isnull=False, deal__isnull=False),
                name='unique_explore_impr_user_deal',
            ),
            models.UniqueConstraint(
                fields=['ip_hash', 'menu_item'],
                condition=models.Q(ip_hash__isnull=False, menu_item__isnull=False),
                name='unique_explore_impr_ip_item',
            ),
            models.UniqueConstraint(
                fields=['ip_hash', 'deal'],
                condition=models.Q(ip_hash__isnull=False, deal__isnull=False),
                name='unique_explore_impr_ip_deal',
            ),
        ]

    def __str__(self):
        target = f'item={self.menu_item_id}' if self.menu_item_id else f'deal={self.deal_id}'
        return f'ExploreImpression<{target} serves={self.serve_count}>'
