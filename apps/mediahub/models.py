import uuid

from django.db import models


class MediaEntityType(models.TextChoices):
    MENU_ITEM = 'menu_item', 'Menu item'
    DEAL = 'deal', 'Deal'


class MediaType(models.TextChoices):
    IMAGE = 'image', 'Image'
    VIDEO = 'video', 'Video'


class MediaProcessingStatus(models.TextChoices):
    EMPTY = '', '—'
    PENDING = 'pending', 'Pending'
    PROCESSING = 'processing', 'Processing'
    READY = 'ready', 'Ready'
    FAILED = 'failed', 'Failed'


class ContentMedia(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='content_media',
    )
    entity_type = models.CharField(max_length=20, choices=MediaEntityType.choices)
    menu_item = models.ForeignKey(
        'restaurants.MenuItem',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='media',
    )
    deal = models.ForeignKey(
        'restaurants.Deal',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='media',
    )
    media_type = models.CharField(max_length=10, choices=MediaType.choices)
    file = models.FileField(upload_to='mediahub/', max_length=512, blank=True)
    order_index = models.PositiveIntegerField(default=0)
    is_cover = models.BooleanField(default=False)
    is_feed_video = models.BooleanField(default=True)
    processing_status = models.CharField(
        max_length=20,
        choices=MediaProcessingStatus.choices,
        blank=True,
        default=MediaProcessingStatus.EMPTY,
    )
    hls_master_key = models.CharField(max_length=512, blank=True, default='')
    hls_master_url = models.URLField(max_length=1024, blank=True, default='')
    thumbnail_key = models.CharField(max_length=512, blank=True, default='')
    thumbnail_url = models.URLField(max_length=1024, blank=True, default='')
    resolutions = models.JSONField(default=list, blank=True)
    duration = models.FloatField(null=True, blank=True)
    processing_error = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order_index', 'created_at']
        verbose_name_plural = 'content media'

    def __str__(self):
        return f'{self.media_type} {self.id}'

    @property
    def public_url(self) -> str:
        if self.file:
            try:
                return self.file.url
            except Exception:
                return self.file.name
        return ''
