from django.urls import path

from . import views, schedule

app_name = 'messaging'

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
    path('c/<int:conversation_id>/shared/', views.conversation_shared, name='conversation_shared'), 
    
    path('c/<int:conversation_id>/messages/<int:message_id>/edit/', views.edit_message, name='edit_message'),
    path('c/<int:conversation_id>/messages/<int:message_id>/delete/', views.delete_message, name='delete_message'),
    path(
        'c/<int:conversation_id>/messages/<int:message_id>/history/',
        views.message_history,
        name='message_history',
    ),

    path('link-preview/', views.link_preview, name='link_preview'),

     path(
        'conversations/<int:conversation_id>/purchase-request/',
        views.send_purchase_request,
        name='send_purchase_request',
    ),
    path(
        'purchase-requests/<int:purchase_id>/verify/',
        views.purchase_verification,
        name='purchase_verification',
    ),
    path(
        'purchase-requests/<int:purchase_id>/respond/',
        views.respond_purchase_request,
        name='purchase_respond',
    ),
    path('schedule/', schedule.schedule_page, name='schedule'),
    path('schedule/events/', schedule.schedule_events, name='schedule_events'),
    path('schedule/<int:purchase_id>/propose/', schedule.schedule_propose, name='schedule_propose'),
    path('schedule/<int:purchase_id>/accept/', schedule.schedule_accept, name='schedule_accept'),
    path('schedule/<int:purchase_id>/deliver/', schedule.schedule_deliver, name='schedule_deliver'),
    path('schedule/<int:purchase_id>/confirm/', schedule.schedule_confirm, name='schedule_confirm'),
]
