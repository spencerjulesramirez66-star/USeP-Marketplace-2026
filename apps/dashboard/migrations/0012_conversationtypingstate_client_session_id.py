from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('dashboard', '0011_conversation_typing_state')]

    operations = [
        migrations.AddField(
            model_name='conversationtypingstate',
            name='client_session_id',
            field=models.CharField(blank=True, max_length=36, null=True),
        ),
    ]
