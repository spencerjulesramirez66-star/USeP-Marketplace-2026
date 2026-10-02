import django.db.models.deletion

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_seed_test_users'),
    ]

    operations = [

        migrations.AddField(
            model_name='emailotp',
            name='purpose',
            field=models.CharField(
                choices=[
                    ('EMAIL_VERIFICATION', 'Email Verification'),
                    ('PASSWORD_RESET', 'Password Reset'),
                ],
                default='EMAIL_VERIFICATION',
                max_length=32,
            ),
        ),

        migrations.AlterField(
            model_name='studentprofile',
            name='major',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='students',
                to='accounts.major',
            ),
        ),

        migrations.AddField(
            model_name='studentprofile',
            name='program',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='enrolled_students',
                to='accounts.program',
            ),
        ),

        migrations.CreateModel(
            name='SellerProfile',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                (
                    'is_verified',
                    models.BooleanField(default=False),
                ),
                (
                    'created_at',
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    'user',
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='seller_profile',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]