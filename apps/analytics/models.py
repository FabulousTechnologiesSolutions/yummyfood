from django.conf import settings
from django.db import models


class ResourceAnalytics(models.Model):
    """Lifetime engagement per MenuItem/Deal (anon aggregate + optional per-user)."""

    menu_item = models.ForeignKey(
        'restaurants.MenuItem',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='analytics',
    )
    deal = models.ForeignKey(
        'restaurants.Deal',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='analytics',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='resource_analytics',
        help_text='Null = anonymous aggregate used for ranking.',
    )
    impression_count = models.PositiveIntegerField(default=0)
    detail_views = models.PositiveIntegerField(default=0)
    call_clicks = models.PositiveIntegerField(default=0)
    whatsapp_clicks = models.PositiveIntegerField(default=0)
    direction_clicks = models.PositiveIntegerField(default=0)
    share_count = models.PositiveIntegerField(default=0)
    save_count = models.PositiveIntegerField(default=0)
    follow_count = models.PositiveIntegerField(default=0)
    engagement_score = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'analytics_resource'
        indexes = [
            models.Index(fields=['menu_item', 'user'], name='analytics_item_user_idx'),
            models.Index(fields=['deal', 'user'], name='analytics_deal_user_idx'),
            models.Index(
                fields=['-engagement_score'],
                name='analytics_score_idx',
            ),
        ]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(menu_item__isnull=False, deal__isnull=True)
                    | models.Q(menu_item__isnull=True, deal__isnull=False)
                ),
                name='analytics_exactly_one_resource',
            ),
            models.UniqueConstraint(
                fields=['menu_item', 'user'],
                condition=models.Q(user__isnull=False, menu_item__isnull=False),
                name='unique_analytics_item_per_user',
            ),
            models.UniqueConstraint(
                fields=['deal', 'user'],
                condition=models.Q(user__isnull=False, deal__isnull=False),
                name='unique_analytics_deal_per_user',
            ),
            models.UniqueConstraint(
                fields=['menu_item'],
                condition=models.Q(user__isnull=True, menu_item__isnull=False),
                name='unique_analytics_anon_item',
            ),
            models.UniqueConstraint(
                fields=['deal'],
                condition=models.Q(user__isnull=True, deal__isnull=False),
                name='unique_analytics_anon_deal',
            ),
        ]

    def __str__(self):
        target = f'item={self.menu_item_id}' if self.menu_item_id else f'deal={self.deal_id}'
        user_label = self.user_id or 'anon'
        return f'ResourceAnalytics<{target} user={user_label}>'
