from rest_framework import serializers
from .models import EmailMessage, EmailMessageRecipient


class EmailMessageRecipientSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailMessageRecipient
        fields = ['recipient_id', 'destination_email',
                  'max_views', 'password_hash', 'password_created_at', 'revoked']

class EmailMessageSerializer(serializers.ModelSerializer):
    recipients = EmailMessageRecipientSerializer(many=True, read_only=True)
    class Meta:
        model = EmailMessage
        fields = ['message_id', 'title',
                 'created_at', 'recipients', 'revoked']
        ordering = ['-created_at']