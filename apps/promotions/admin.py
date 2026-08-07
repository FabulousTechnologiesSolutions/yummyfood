from django.contrib import admin

from apps.promotions.models import FeaturedCampaign, PromotionRequest

admin.site.register(PromotionRequest)
admin.site.register(FeaturedCampaign)
