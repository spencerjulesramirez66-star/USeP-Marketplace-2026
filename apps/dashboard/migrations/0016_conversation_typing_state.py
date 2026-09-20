from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('dashboard', '0015_message_attachment_collection')]

    operations = [
        migrations.CreateModel(
            name='ConversationTypingState',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('last_activity_at', models.DateTimeField(blank=True, null=True)),
                ('last_sequence', models.PositiveIntegerField(default=0)),
                ('conversation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='typing_states', to='dashboard.conversation')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conversation_typing_states', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name='conversationtypingstate',
            constraint=models.UniqueConstraint(fields=('conversation', 'user'), name='unique_conversation_typing_state'),
        ),
    ]
