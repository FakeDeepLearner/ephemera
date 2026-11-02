from django.urls import path

from .views import *

app_name = 'emailmessages'

urlpatterns = [
    path('list/', email_message_list, name='email-message-list'),
    path('create/', email_message_create, name='email-message-create'),
    path('recipients/<uuid:recipient_id>', email_message_view, name='email-recipient-view'),
    path('recipients/<uuid:recipient_id>/view/', email_message_view_with_password, name='email-message-view'),
    path('recipients/<uuid:recipient_id>/revoke/', email_recipient_revoke, name='email-recipient-revoke'),
    path('messages/<uuid:message_id>/revoke/', email_message_revoke, name='email-message-revoke'),
    path('recipients/<uuid:recipient_id>/statistics/', email_recipient_usage_statistics,
         name='email-recipient-usage-statistics'),
]
