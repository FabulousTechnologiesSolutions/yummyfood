import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def backfill_target_type(apps, schema_editor):
    Rating = apps.get_model('engagement', 'Rating')
    Rating.objects.filter(target_type='').update(target_type='restaurant')


class Migration(migrations.Migration):

    dependencies = [
        ('engagement', '0003_contentreport_restaurant_scope'),
        ('restaurants', '0006_freeform_price_range'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Rename model RestaurantRating -> Rating
        migrations.RenameModel(
            old_name='RestaurantRating',
            new_name='Rating',
        ),
        # Remove old unique constraint
        migrations.RemoveConstraint(
            model_name='rating',
            name='unique_rating_user_restaurant',
        ),
        # Add target_type field (default restaurant for existing rows)
        migrations.AddField(
            model_name='rating',
            name='target_type',
            field=models.CharField(
                choices=[
                    ('item', 'Item'),
                    ('deal', 'Deal'),
                    ('restaurant', 'Restaurant'),
                ],
                default='restaurant',
                max_length=16,
            ),
            preserve_default=False,
        ),
        # Add menu_item FK
        migrations.AddField(
            model_name='rating',
            name='menu_item',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='ratings',
                to='restaurants.menuitem',
            ),
        ),
        # Add deal FK
        migrations.AddField(
            model_name='rating',
            name='deal',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='ratings',
                to='restaurants.deal',
            ),
        ),
        # Backfill existing rows
        migrations.RunPython(backfill_target_type, migrations.RunPython.noop),
        # Change related_name on user FK
        migrations.AlterField(
            model_name='rating',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='ratings',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        # Add index on (target_type, restaurant)
        migrations.AddIndex(
            model_name='rating',
            index=models.Index(
                fields=['target_type', 'restaurant'],
                name='rating_type_restaurant_idx',
            ),
        ),
        # Add type-matches-FK constraint
        migrations.AddConstraint(
            model_name='rating',
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(
                        ('deal__isnull', True),
                        ('menu_item__isnull', False),
                        ('target_type', 'item'),
                    ),
                    models.Q(
                        ('deal__isnull', False),
                        ('menu_item__isnull', True),
                        ('target_type', 'deal'),
                    ),
                    models.Q(
                        ('deal__isnull', True),
                        ('menu_item__isnull', True),
                        ('target_type', 'restaurant'),
                    ),
                    _connector='OR',
                ),
                name='rating_type_matches_fk',
            ),
        ),
        # Unique per item
        migrations.AddConstraint(
            model_name='rating',
            constraint=models.UniqueConstraint(
                condition=models.Q(('menu_item__isnull', False)),
                fields=('user', 'menu_item'),
                name='unique_rating_user_item',
            ),
        ),
        # Unique per deal
        migrations.AddConstraint(
            model_name='rating',
            constraint=models.UniqueConstraint(
                condition=models.Q(('deal__isnull', False)),
                fields=('user', 'deal'),
                name='unique_rating_user_deal',
            ),
        ),
        # Unique per restaurant (restaurant-scope only)
        migrations.AddConstraint(
            model_name='rating',
            constraint=models.UniqueConstraint(
                condition=models.Q(('target_type', 'restaurant')),
                fields=('user', 'restaurant'),
                name='unique_rating_user_restaurant',
            ),
        ),
    ]
