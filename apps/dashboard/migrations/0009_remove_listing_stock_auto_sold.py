from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0008_inventory_and_transactions'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='listing',
            name='stock_auto_sold',
        ),
    ]
