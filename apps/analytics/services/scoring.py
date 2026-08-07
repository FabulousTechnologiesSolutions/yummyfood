from django.conf import settings


def recalculate_score(counters: dict) -> float:
    weights = getattr(settings, 'EXPLORE_ENGAGEMENT_WEIGHTS', {})
    mapping = {
        'impression': counters.get('impression_count', 0),
        'detail_view': counters.get('detail_views', 0),
        'call': counters.get('call_clicks', 0),
        'whatsapp': counters.get('whatsapp_clicks', 0),
        'share': counters.get('share_count', 0),
        'save': counters.get('save_count', 0),
        'follow': counters.get('follow_count', 0),
        'direction': counters.get('direction_clicks', 0),
    }
    return float(sum(mapping[k] * float(weights.get(k, 0)) for k in mapping))


def score_from_analytics_obj(obj) -> float:
    return recalculate_score(
        {
            'impression_count': obj.impression_count,
            'detail_views': obj.detail_views,
            'call_clicks': obj.call_clicks,
            'whatsapp_clicks': obj.whatsapp_clicks,
            'share_count': obj.share_count,
            'save_count': obj.save_count,
            'follow_count': obj.follow_count,
            'direction_clicks': obj.direction_clicks,
        }
    )
