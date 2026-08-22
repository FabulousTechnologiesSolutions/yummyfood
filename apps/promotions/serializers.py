from rest_framework import serializers


class PromotionRequestCreateSerializer(serializers.Serializer):
    event_model = serializers.ChoiceField(choices=['item', 'deal'])
    resource_id = serializers.IntegerField(min_value=1)
    requested_start = serializers.DateTimeField()
    requested_end = serializers.DateTimeField()


class PromotionRejectSerializer(serializers.Serializer):
    admin_note = serializers.CharField(required=False, allow_blank=True, default='')


class PromotionApproveSerializer(serializers.Serializer):
    """Legacy /api/admin-api/ approve — window optional; falls back to requested_*."""

    starts_at = serializers.DateTimeField(required=False, allow_null=True)
    goes_live_at = serializers.DateTimeField(required=False, allow_null=True)
    ends_at = serializers.DateTimeField(required=False, allow_null=True)

    def validate(self, attrs):
        live = attrs.get('starts_at') or attrs.get('goes_live_at')
        attrs['goes_live_at'] = live
        return attrs
