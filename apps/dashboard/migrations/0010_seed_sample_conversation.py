from django.db import migrations


BUYER_EMAIL = 'test.buyer@usep.edu.ph'
SELLER_EMAIL = 'test.seller@usep.edu.ph'
LISTING_SLUG = 'test-seller-calculus-book'


def seed_sample_conversation(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    Listing = apps.get_model('dashboard', 'Listing')
    Conversation = apps.get_model('dashboard', 'Conversation')
    Message = apps.get_model('dashboard', 'Message')

    buyer = User.objects.filter(email=BUYER_EMAIL).first()
    seller = User.objects.filter(email=SELLER_EMAIL).first()
    listing = Listing.objects.filter(slug=LISTING_SLUG).first()

    if not buyer or not seller or not listing:
        return

    conversation, _ = Conversation.objects.get_or_create(
        buyer=buyer,
        seller=seller,
        listing=listing,
    )

    Message.objects.get_or_create(
        conversation=conversation,
        sender=buyer,
        body='Hi! Is the calculus textbook still available for pickup on campus?',
    )
    Message.objects.get_or_create(
        conversation=conversation,
        sender=seller,
        body='Yes, it is available. We can meet near the library this week.',
    )


def remove_sample_conversation(apps, schema_editor):
    Conversation = apps.get_model('dashboard', 'Conversation')
    Message = apps.get_model('dashboard', 'Message')

    conversation = Conversation.objects.filter(
        buyer__email=BUYER_EMAIL,
        seller__email=SELLER_EMAIL,
        listing__slug=LISTING_SLUG,
    ).first()
    if conversation:
        Message.objects.filter(conversation=conversation).delete()
        conversation.delete()


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0005_seller_profile_and_catalog_cleanup'),
        ('dashboard', '0009_remove_listing_stock_auto_sold'),
    ]

    operations = [
        migrations.RunPython(seed_sample_conversation, remove_sample_conversation),
    ]
