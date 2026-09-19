def unread_messages(request):
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {'unread_message_count': 0}
    from .views import _unread_message_count
    return {
        'unread_message_count': _unread_message_count(request.user),
    }
