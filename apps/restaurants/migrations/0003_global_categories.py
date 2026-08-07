from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('restaurants', '0002_menu_deals_content_media'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='menucategory',
            options={
                'ordering': ['position', 'id'],
                'verbose_name_plural': 'menu categories',
            },
        ),
        migrations.RemoveConstraint(
            model_name='menucategory',
            name='uniq_restaurant_category_slug',
        ),
        migrations.RemoveField(
            model_name='menuitem',
            name='category',
        ),
        migrations.RemoveField(
            model_name='menuitem',
            name='cross_categories',
        ),
        migrations.RemoveField(
            model_name='menucategory',
            name='restaurant',
        ),
        migrations.AddField(
            model_name='menuitem',
            name='categories',
            field=models.ManyToManyField(
                blank=True,
                related_name='menu_items',
                to='restaurants.menucategory',
            ),
        ),
        migrations.AlterField(
            model_name='menucategory',
            name='slug',
            field=models.SlugField(max_length=64, unique=True),
        ),
    ]
