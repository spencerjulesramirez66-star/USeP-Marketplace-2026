import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0006_message_attachment'),
    ]

    operations = [
        migrations.AddField(model_name='message', name='deleted_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='message', name='is_deleted', field=models.BooleanField(default=False)),
        migrations.AddField(
            model_name='message',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
