from rest_framework import serializers


class AdminPromotionApproveSerializer(serializers.Serializer):
    """New /api/admin/ live action — window dates are required."""

    starts_at = serializers.DateTimeField(required=False, allow_null=True)
    goes_live_at = serializers.DateTimeField(required=False, allow_null=True)
    ends_at = serializers.DateTimeField(required=False, allow_null=True)

    def validate(self, attrs):
        live = attrs.get('starts_at') or attrs.get('goes_live_at')
        if live is None:
            raise serializers.ValidationError(
                {'starts_at': 'This field is required (or goes_live_at).'}
            )
        if attrs.get('ends_at') is None:
            raise serializers.ValidationError({'ends_at': 'This field is required.'})
        attrs['goes_live_at'] = live
        return attrs


class AdminPromotionRejectSerializer(serializers.Serializer):
    admin_note = serializers.CharField(required=True, allow_blank=False, trim_whitespace=True)
