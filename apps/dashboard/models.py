from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Category(models.Model):
	name = models.CharField(max_length=100, unique=True)
	slug = models.SlugField(max_length=110, unique=True)

	class Meta:
		ordering = ['name']

	def __str__(self):
		return self.name


class Listing(models.Model):
	class Status(models.TextChoices):
		DRAFT = 'DRAFT', 'Draft'
		ACTIVE = 'ACTIVE', 'Active'
		RESERVED = 'RESERVED', 'Reserved'
		SOLD = 'SOLD', 'Sold'
		ARCHIVED = 'ARCHIVED', 'Archived'

	seller = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='listings',
	)
	category = models.ForeignKey(
		Category,
		on_delete=models.PROTECT,
		related_name='listings',
	)
	title = models.CharField(max_length=180)
	slug = models.SlugField(max_length=200, unique=True)
	description = models.TextField()
	price = models.DecimalField(
		max_digits=10,
		decimal_places=2,
		validators=[MinValueValidator(0)],
	)
	condition = models.CharField(max_length=80)
	location = models.CharField(max_length=180, blank=True)
	image = models.ImageField(upload_to='listings/', blank=True, null=True)
	image_urls = models.JSONField(default=list, blank=True)
	status = models.CharField(
		max_length=10,
		choices=Status.choices,
		default=Status.ACTIVE,
	)
	stock_quantity = models.PositiveIntegerField(default=0)
	views = models.PositiveIntegerField(default=0)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-created_at']
		indexes = [
			models.Index(fields=['status', 'created_at']),
			models.Index(fields=['seller', 'status']),
		]

	def __str__(self):
		return self.title

	def save(self, *args, **kwargs):
		if not self.slug:
			base_slug = slugify(self.title) or 'listing'
			candidate = base_slug
			counter = 2
			while Listing.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
				candidate = f'{base_slug}-{counter}'
				counter += 1
			self.slug = candidate
		super().save(*args, **kwargs)

	def get_absolute_url(self):
		return reverse('dashboard:buyer_detail', kwargs={'item_slug': self.slug})

	@property
	def price_label(self):
		return f'₱{self.price:,.0f}'

	@property
	def image_url(self):
		if self.image:
			return self.image.url
		return 'https://placehold.co/640x480?text=USeP+Marketplace'

	@property
	def is_service_listing(self):
		return self.category and self.category.slug.lower() == 'services'

	@property
	def seller_role(self):
		try:
			return self.seller.staff_profile.get_staff_type_display()
		except Exception:
			return 'Marketplace seller'

	@property
	def seller_name(self):
		return f'{self.seller.first_name} {self.seller.last_name}'.strip() or self.seller.email

	@property
	def seller_avatar_url(self):
		if self.seller.profile_picture:
			return self.seller.profile_picture.url
		return '/static/images/default-avatar.png'

	@property
	def gallery_urls(self):
		urls = []
		for url in [image.image.url for image in self.listing_images.all()] + (self.image_urls or []):
			if url and url not in urls:
				urls.append(url)
		if not urls and self.image:
			urls.append(self.image.url)
		return urls

	@property
	def gallery_image_ids(self):
		seen = set()
		image_ids = []
		for image in self.listing_images.all():
			if image.image.url in seen:
				continue
			seen.add(image.image.url)
			image_ids.append(str(image.id))
		return image_ids


class ListingImage(models.Model):
	listing = models.ForeignKey(
		Listing,
		on_delete=models.CASCADE,
		related_name='listing_images',
	)
	image = models.ImageField(upload_to='listings/gallery/')
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['created_at']


class SavedItem(models.Model):
	buyer = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='saved_items',
	)
	listing = models.ForeignKey(
		Listing,
		on_delete=models.CASCADE,
		related_name='saved_by',
	)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']
		constraints = [
			models.UniqueConstraint(
				fields=['buyer', 'listing'],
				name='unique_saved_listing_per_buyer',
			)
		]


class Conversation(models.Model):
	buyer = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='buyer_conversations',
	)
	seller = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='seller_conversations',
	)
	listing = models.ForeignKey(
		Listing,
		on_delete=models.CASCADE,
		related_name='conversations',
	)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-updated_at']
		constraints = [
			models.UniqueConstraint(
				fields=['buyer', 'seller', 'listing'],
				name='unique_conversation_per_listing',
			)
		]


class Message(models.Model):
	conversation = models.ForeignKey(
		Conversation,
		on_delete=models.CASCADE,
		related_name='messages',
	)
	sender = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='sent_marketplace_messages',
	)
	body = models.TextField(max_length=2000)
	created_at = models.DateTimeField(auto_now_add=True)
	is_read = models.BooleanField(default=False)

	class Meta:
		ordering = ['created_at']
