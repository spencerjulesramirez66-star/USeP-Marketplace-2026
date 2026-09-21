from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('dashboard', '0007_message_soft_delete'),
        ('accounts', '0001_initial'),
    ]
    operations = [
        migrations.AddField(model_name='message', name='edited_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='message', name='is_edited', field=models.BooleanField(default=False)),
        migrations.CreateModel(name='MessageRevision', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('body', models.TextField(max_length=2000)), ('edited_at', models.DateTimeField(auto_now_add=True)),
            ('editor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='message_revisions', to='accounts.user')),
            ('message', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='revisions', to='dashboard.message')),
        ], options={'ordering': ['edited_at', 'pk']}),
    ]
