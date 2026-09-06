from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0005_emailotp_purpose'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_seller',
            field=models.BooleanField(default=False),
        ),
    ]
