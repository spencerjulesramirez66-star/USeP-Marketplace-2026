from django.urls import path

from . import views

app_name = 'messaging'

# Mount in the project urls.py, e.g.:
#   path('messages/', include('apps.messaging.urls'))
urlpatterns = [
    path('', views.conversation_list, name='conversation_list'),
    path('c/<int:conversation_id>/', views.conversation_detail, name='conversation'),
    path('listings/<slug:item_slug>/start/', views.start_conversation, name='start_conversation'),

    path('unread-count/', views.unread_message_count, name='unread_message_count'),
    path('sidebar-state/', views.sidebar_state, name='conversation_sidebar_state'),
    path('search/', views.conversation_search, name='conversation_search'),
    path('c/<int:conversation_id>/clear/', views.clear_conversation, name='clear_conversation'),

    path('c/<int:conversation_id>/changes/', views.new_messages, name='conversation_new_messages'),
    path('c/<int:conversation_id>/search/', views.message_search, name='conversation_message_search'),
    path('c/<int:conversation_id>/read/', views.mark_read, name='conversation_read'),
    path('c/<int:conversation_id>/typing/', views.typing, name='conversation_typing'),
    path('c/<int:conversation_id>/links/', views.conversation_links, name='conversation_links'),

    path('c/<int:conversation_id>/messages/<int:message_id>/edit/', views.edit_message, name='edit_message'),
    path('c/<int:conversation_id>/messages/<int:message_id>/delete/', views.delete_message, name='delete_message'),
    path(
        'c/<int:conversation_id>/messages/<int:message_id>/history/',
        views.message_history,
        name='message_history',
    ),

    path('link-preview/', views.link_preview, name='link_preview'),
]
