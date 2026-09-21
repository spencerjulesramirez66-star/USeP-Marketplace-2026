from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0004_listingimage'),
    ]

    operations = [
        migrations.AddField(
            model_name='listing',
            name='stock_quantity',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
