from rest_framework import serializers

from apps.feed.services.seen_service import MAX_SEEN_BATCH_ITEMS


class FeedSeenItemSerializer(serializers.Serializer):
    event_model = serializers.ChoiceField(choices=['item', 'deal'])
    resource_id = serializers.IntegerField(min_value=1)
    watched_ms = serializers.IntegerField(min_value=0)
    duration_ms = serializers.IntegerField(min_value=1, required=False, allow_null=True)


class FeedSeenBatchSerializer(serializers.Serializer):
    items = FeedSeenItemSerializer(many=True)

    def validate_items(self, value):
        n = len(value)
        if n < 1 or n > MAX_SEEN_BATCH_ITEMS:
            raise serializers.ValidationError(
                f'items must contain between 1 and {MAX_SEEN_BATCH_ITEMS} events.'
            )
        return value
