import django.db.models.deletion
from django.db import migrations, models


def backfill_report_restaurant(apps, schema_editor):
    ContentReport = apps.get_model('engagement', 'ContentReport')
    for report in ContentReport.objects.select_related('menu_item', 'deal').iterator():
        if report.menu_item_id:
            report.restaurant_id = report.menu_item.restaurant_id
        elif report.deal_id:
            report.restaurant_id = report.deal.restaurant_id
        else:
            continue
        report.save(update_fields=['restaurant_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('engagement', '0002_content_report_restaurant_rating'),
        ('restaurants', '0006_freeform_price_range'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='contentreport',
            name='report_exactly_one_target',
        ),
        migrations.RemoveConstraint(
            model_name='contentreport',
            name='report_type_matches_fk',
        ),
        migrations.AddField(
            model_name='contentreport',
            name='restaurant',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='content_reports',
                to='restaurants.restaurant',
            ),
        ),
        migrations.AlterField(
            model_name='contentreport',
            name='target_type',
            field=models.CharField(
                choices=[
                    ('item', 'Item'),
                    ('deal', 'Deal'),
                    ('restaurant', 'Restaurant'),
                ],
                max_length=16,
            ),
        ),
        migrations.RunPython(backfill_report_restaurant, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='contentreport',
            name='restaurant',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='content_reports',
                to='restaurants.restaurant',
            ),
        ),
        migrations.AddIndex(
            model_name='contentreport',
            index=models.Index(
                fields=['target_type', 'restaurant'],
                name='report_type_restaurant_idx',
            ),
        ),
        migrations.AddConstraint(
            model_name='contentreport',
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
                name='report_type_matches_fk',
            ),
        ),
        migrations.AddConstraint(
            model_name='contentreport',
            constraint=models.UniqueConstraint(
                condition=models.Q(('target_type', 'restaurant')),
                fields=('created_by', 'restaurant'),
                name='unique_report_user_restaurant',
            ),
        ),
    ]
