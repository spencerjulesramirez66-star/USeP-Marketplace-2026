def review_notifications(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {}

    notifications = user.review_notifications.select_related(
        'reply__review__listing',
        'reply__author',
    )[:10]
    return {
        'review_notification_count': user.review_notifications.filter(is_read=False).count(),
        'review_notifications': notifications,
    }
