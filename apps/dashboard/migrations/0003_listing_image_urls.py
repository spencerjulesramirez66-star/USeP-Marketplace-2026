from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0002_seed_categories'),
    ]

    operations = [
        migrations.AddField(
            model_name='listing',
            name='image_urls',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
