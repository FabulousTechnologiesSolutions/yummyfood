from django.conf import settings
from django.db import models


class SavedTargetType(models.TextChoices):
    ITEM = 'item', 'Item'
    DEAL = 'deal', 'Deal'


class SavedItem(models.Model):
    """Customer-saved menu item or deal."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saved_items',
    )
    target_type = models.CharField(max_length=10, choices=SavedTargetType.choices)
    menu_item = models.ForeignKey(
        'restaurants.MenuItem',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='saved_by',
    )
    deal = models.ForeignKey(
        'restaurants.Deal',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='saved_by',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at'], name='saved_user_created_idx'),
            models.Index(fields=['user', 'target_type'], name='saved_user_type_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(menu_item__isnull=False, deal__isnull=True)
                    | models.Q(menu_item__isnull=True, deal__isnull=False)
                ),
                name='saved_exactly_one_target',
            ),
            models.CheckConstraint(
                check=(
                    (
                        models.Q(target_type=SavedTargetType.ITEM, menu_item__isnull=False)
                        | models.Q(target_type=SavedTargetType.DEAL, deal__isnull=False)
                    )
                ),
                name='saved_type_matches_fk',
            ),
            models.UniqueConstraint(
                fields=['user', 'menu_item'],
                condition=models.Q(menu_item__isnull=False),
                name='unique_saved_user_item',
            ),
            models.UniqueConstraint(
                fields=['user', 'deal'],
                condition=models.Q(deal__isnull=False),
                name='unique_saved_user_deal',
            ),
        ]

    def __str__(self):
        if self.menu_item_id:
            return f'SavedItem<user={self.user_id} item={self.menu_item_id}>'
        return f'SavedItem<user={self.user_id} deal={self.deal_id}>'


class ReportTargetType(models.TextChoices):
    ITEM = 'item', 'Item'
    DEAL = 'deal', 'Deal'
    RESTAURANT = 'restaurant', 'Restaurant'


class ReportReason(models.TextChoices):
    MISLEADING_PRICE = 'misleading_price', 'Misleading price'
    PHOTO_MISMATCH = 'photo_mismatch', 'Photo not the real dish'
    UNAVAILABLE = 'unavailable', 'Unavailable'
    OTHER = 'other', 'Other'


class ReportStatus(models.TextChoices):
    OPEN = 'open', 'Open'
    ACTIONED = 'actioned', 'Actioned'
    DISMISSED = 'dismissed', 'Dismissed'


class ContentReport(models.Model):
    """Customer report of a menu item, deal, or entire restaurant."""

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='content_reports',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    target_type = models.CharField(max_length=16, choices=ReportTargetType.choices)
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='content_reports',
    )
    menu_item = models.ForeignKey(
        'restaurants.MenuItem',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='content_reports',
    )
    deal = models.ForeignKey(
        'restaurants.Deal',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='content_reports',
    )
    reason = models.CharField(max_length=40, choices=ReportReason.choices)
    description = models.TextField(blank=True, default='')
    status = models.CharField(
        max_length=16,
        choices=ReportStatus.choices,
        default=ReportStatus.OPEN,
        db_index=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_content_reports',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    admin_note = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at'], name='report_status_created_idx'),
            models.Index(
                fields=['target_type', 'restaurant'],
                name='report_type_restaurant_idx',
            ),
        ]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(
                        target_type=ReportTargetType.ITEM,
                        menu_item__isnull=False,
                        deal__isnull=True,
                    )
                    | models.Q(
                        target_type=ReportTargetType.DEAL,
                        menu_item__isnull=True,
                        deal__isnull=False,
                    )
                    | models.Q(
                        target_type=ReportTargetType.RESTAURANT,
                        menu_item__isnull=True,
                        deal__isnull=True,
                    )
                ),
                name='report_type_matches_fk',
            ),
            models.UniqueConstraint(
                fields=['created_by', 'menu_item'],
                condition=models.Q(menu_item__isnull=False),
                name='unique_report_user_item',
            ),
            models.UniqueConstraint(
                fields=['created_by', 'deal'],
                condition=models.Q(deal__isnull=False),
                name='unique_report_user_deal',
            ),
            models.UniqueConstraint(
                fields=['created_by', 'restaurant'],
                condition=models.Q(target_type=ReportTargetType.RESTAURANT),
                name='unique_report_user_restaurant',
            ),
        ]

    def __str__(self):
        if self.menu_item_id:
            target = f'item={self.menu_item_id}'
        elif self.deal_id:
            target = f'deal={self.deal_id}'
        else:
            target = f'restaurant={self.restaurant_id}'
        return f'ContentReport<{self.id} {target} {self.status}>'


class RatingTargetType(models.TextChoices):
    ITEM = 'item', 'Item'
    DEAL = 'deal', 'Deal'
    RESTAURANT = 'restaurant', 'Restaurant'


class Rating(models.Model):
    """Customer rating for a menu item, deal, or entire restaurant."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ratings',
    )
    target_type = models.CharField(max_length=16, choices=RatingTargetType.choices)
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='ratings',
    )
    menu_item = models.ForeignKey(
        'restaurants.MenuItem',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='ratings',
    )
    deal = models.ForeignKey(
        'restaurants.Deal',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='ratings',
    )
    stars = models.PositiveSmallIntegerField()
    description = models.TextField(blank=True, default='')
    rated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-rated_at']
        indexes = [
            models.Index(
                fields=['target_type', 'restaurant'],
                name='rating_type_restaurant_idx',
            ),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(stars__gte=1, stars__lte=5),
                name='rating_stars_1_to_5',
            ),
            models.CheckConstraint(
                check=(
                    models.Q(
                        target_type=RatingTargetType.ITEM,
                        menu_item__isnull=False,
                        deal__isnull=True,
                    )
                    | models.Q(
                        target_type=RatingTargetType.DEAL,
                        menu_item__isnull=True,
                        deal__isnull=False,
                    )
                    | models.Q(
                        target_type=RatingTargetType.RESTAURANT,
                        menu_item__isnull=True,
                        deal__isnull=True,
                    )
                ),
                name='rating_type_matches_fk',
            ),
            models.UniqueConstraint(
                fields=['user', 'menu_item'],
                condition=models.Q(menu_item__isnull=False),
                name='unique_rating_user_item',
            ),
            models.UniqueConstraint(
                fields=['user', 'deal'],
                condition=models.Q(deal__isnull=False),
                name='unique_rating_user_deal',
            ),
            models.UniqueConstraint(
                fields=['user', 'restaurant'],
                condition=models.Q(target_type=RatingTargetType.RESTAURANT),
                name='unique_rating_user_restaurant',
            ),
        ]

    def __str__(self):
        if self.menu_item_id:
            target = f'item={self.menu_item_id}'
        elif self.deal_id:
            target = f'deal={self.deal_id}'
        else:
            target = f'restaurant={self.restaurant_id}'
        return f'Rating<user={self.user_id} {target} stars={self.stars}>'


# Backward-compatible alias
RestaurantRating = Rating
