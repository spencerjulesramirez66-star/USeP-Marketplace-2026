from django.contrib import admin

from apps.accounts.models import Roles

from .models import Category, Listing, ListingImage, ListingReview, ListingReviewPhoto, SavedItem


class AdministratorOnlyModelAdmin(admin.ModelAdmin):
    """Listing history is available only to the application's Admin role."""

    def has_module_permission(self, request):
        return request.user.is_active and request.user.role == Roles.ADMIN

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        return self.has_module_permission(request)

    def has_change_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_module_permission(request)


@admin.register(Listing)
class ListingAdmin(AdministratorOnlyModelAdmin):
    list_display = ('title', 'seller', 'status', 'lifecycle_state', 'recycled_at', 'archived_at')
    list_filter = ('lifecycle_state', 'status', 'category')
    search_fields = ('title', 'slug', 'seller__email')
    readonly_fields = ('created_at', 'updated_at', 'recycled_at', 'recycle_bin_expires_at', 'archived_at')


admin.site.register(Category, AdministratorOnlyModelAdmin)
admin.site.register(ListingImage, AdministratorOnlyModelAdmin)
admin.site.register(ListingReview, AdministratorOnlyModelAdmin)
admin.site.register(ListingReviewPhoto, AdministratorOnlyModelAdmin)
admin.site.register(SavedItem, AdministratorOnlyModelAdmin)
