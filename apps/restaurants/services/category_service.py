from django.db import transaction

from apps.restaurants.models import MenuCategory
from core.exceptions import AppAPIException


class CategoryService:
    def list(self):
        return list(MenuCategory.objects.all())

    def get(self, *, category_id) -> MenuCategory:
        try:
            return MenuCategory.objects.get(id=category_id)
        except MenuCategory.DoesNotExist:
            raise AppAPIException(
                code='CATEGORY_NOT_FOUND',
                message='Category not found.',
                status_code=404,
            )

    @transaction.atomic
    def create(self, *, data: dict) -> MenuCategory:
        slug = (data.get('slug') or '').strip().lower()
        if MenuCategory.objects.filter(slug=slug).exists():
            raise AppAPIException(
                code='CATEGORY_SLUG_EXISTS',
                message='A category with this slug already exists.',
                status_code=409,
            )
        return MenuCategory.objects.create(
            slug=slug,
            name=data['name'].strip(),
            icon=(data.get('icon') or '').strip(),
            position=data.get('position', 0),
            is_visible=data.get('is_visible', True),
        )

    @transaction.atomic
    def update(self, *, category_id, data: dict) -> MenuCategory:
        category = self.get(category_id=category_id)
        if 'name' in data:
            category.name = data['name'].strip()
        if 'icon' in data:
            category.icon = (data.get('icon') or '').strip()
        if 'position' in data and data['position'] is not None:
            category.position = data['position']
        if 'is_visible' in data and data['is_visible'] is not None:
            category.is_visible = data['is_visible']
        if 'slug' in data and data['slug']:
            slug = data['slug'].strip().lower()
            if MenuCategory.objects.filter(slug=slug).exclude(id=category.id).exists():
                raise AppAPIException(
                    code='CATEGORY_SLUG_EXISTS',
                    message='A category with this slug already exists.',
                    status_code=409,
                )
            category.slug = slug
        category.save()
        return category

    @transaction.atomic
    def delete(self, *, category_id) -> None:
        category = self.get(category_id=category_id)
        if category.menu_items.exists():
            raise AppAPIException(
                code='CATEGORY_IN_USE',
                message='Cannot delete a category that still has menu items.',
                status_code=400,
            )
        category.delete()

    @transaction.atomic
    def reorder(self, *, ordered_ids: list) -> list:
        categories = {
            c.id: c for c in MenuCategory.objects.filter(id__in=ordered_ids)
        }
        if len(categories) != len(ordered_ids):
            raise AppAPIException(
                code='CATEGORY_NOT_FOUND',
                message='One or more categories were not found.',
                status_code=404,
            )
        for position, cid in enumerate(ordered_ids):
            cat = categories[cid]
            cat.position = position
            cat.save(update_fields=['position'])
        return self.list()


def serialize_category(category: MenuCategory) -> dict:
    return {
        'id': category.id,
        'slug': category.slug,
        'name': category.name,
        'icon': category.icon,
        'position': category.position,
        'is_visible': category.is_visible,
    }
