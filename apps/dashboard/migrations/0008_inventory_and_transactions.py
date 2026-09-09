from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0007_mark_seeded_sellers'),
    ]

    operations = [
        # This field existed in databases created by an earlier inventory
        # implementation.  It is kept in the migration state so 0009 can
        # remove it cleanly from databases where 0008 was already applied.
        migrations.AddField(
            model_name='listing',
            name='stock_auto_sold',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='listing',
            name='stock_quantity',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
