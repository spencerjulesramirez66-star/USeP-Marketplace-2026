from . import selectors


def unread_messages(request):
    """Feeds the navbar badge on first paint. See views.unread_message_count
    for the endpoint that refreshes it without a reload."""
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {'unread_message_count': 0}
    return {'unread_message_count': selectors.unread_total(request.user)}
