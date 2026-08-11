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
