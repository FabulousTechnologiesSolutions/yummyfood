from rest_framework import serializers

from apps.engagement.models import SavedTargetType


class SaveCreateSerializer(serializers.Serializer):
    target_type = serializers.ChoiceField(choices=SavedTargetType.choices)
    menu_item_id = serializers.IntegerField(required=False, min_value=1)
    deal_id = serializers.IntegerField(required=False, min_value=1)

    def validate(self, attrs):
        target_type = attrs['target_type']
        menu_item_id = attrs.get('menu_item_id')
        deal_id = attrs.get('deal_id')
        if target_type == SavedTargetType.ITEM:
            if not menu_item_id:
                raise serializers.ValidationError(
                    {'menu_item_id': 'This field is required for target_type=item.'}
                )
            if deal_id:
                raise serializers.ValidationError(
                    {'deal_id': 'Do not send deal_id for target_type=item.'}
                )
        elif target_type == SavedTargetType.DEAL:
            if not deal_id:
                raise serializers.ValidationError(
                    {'deal_id': 'This field is required for target_type=deal.'}
                )
            if menu_item_id:
                raise serializers.ValidationError(
                    {'menu_item_id': 'Do not send menu_item_id for target_type=deal.'}
                )
        return attrs
