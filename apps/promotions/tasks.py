from celery import shared_task

from apps.promotions.services import expire_promotion_resources


@shared_task(name='apps.promotions.tasks.expire_promotions')
def expire_promotions():
    return expire_promotion_resources()
