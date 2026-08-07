from django.conf import settings
from django.db import models


class PromotionRequestStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    LIVE = 'live', 'Live'
    CHANGES = 'changes', 'Changes'
    ENDED = 'ended', 'Ended'


class PromotionRequest(models.Model):
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='promotion_requests',
    )
    menu_item = models.ForeignKey(
        'restaurants.MenuItem',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='promotion_requests',
    )
    deal = models.ForeignKey(
        'restaurants.Deal',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='promotion_requests',
    )
    status = models.CharField(
        max_length=20,
        choices=PromotionRequestStatus.choices,
        default=PromotionRequestStatus.PENDING,
        db_index=True,
    )
    requested_start = models.DateTimeField()
    requested_end = models.DateTimeField()
    admin_note = models.TextField(blank=True, default='')
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_promotion_requests',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    goes_live_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(menu_item__isnull=False, deal__isnull=True)
                    | models.Q(menu_item__isnull=True, deal__isnull=False)
                ),
                name='promo_req_exactly_one_target',
            ),
        ]

    def __str__(self):
        return f'PromotionRequest<{self.id} {self.status}>'


class FeaturedCampaign(models.Model):
    menu_item = models.ForeignKey(
        'restaurants.MenuItem',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='featured_campaigns',
    )
    deal = models.ForeignKey(
        'restaurants.Deal',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='featured_campaigns',
    )
    promotion_request = models.ForeignKey(
        PromotionRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='campaigns',
    )
    started_at = models.DateTimeField()
    ends_at = models.DateTimeField()
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
        ordering = ['-started_at']
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(menu_item__isnull=False, deal__isnull=True)
                    | models.Q(menu_item__isnull=True, deal__isnull=False)
                ),
                name='feat_campaign_exactly_one_target',
            ),
            models.UniqueConstraint(
                fields=['menu_item', 'started_at'],
                condition=models.Q(menu_item__isnull=False),
                name='unique_feat_campaign_item_start',
            ),
            models.UniqueConstraint(
                fields=['deal', 'started_at'],
                condition=models.Q(deal__isnull=False),
                name='unique_feat_campaign_deal_start',
            ),
        ]
        indexes = [
            models.Index(
                fields=['started_at', 'ends_at'],
                name='feat_campaign_window_idx',
            ),
        ]

    def __str__(self):
        target = self.menu_item_id or self.deal_id
        return f'FeaturedCampaign<{target} {self.started_at:%Y-%m-%d}>'
