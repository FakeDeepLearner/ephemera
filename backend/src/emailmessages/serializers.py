from rest_framework import serializers

from .models import EmailMessage, EmailMessageRecipient


class EmailMessageRecipientSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailMessageRecipient
        fields = ['recipient_id', 'destination_email',
                  'password_hash', 'password_created_at', 'revoked']


class EmailMessageSerializer(serializers.ModelSerializer):
    recipients = EmailMessageRecipientSerializer(many=True, read_only=True)

    class Meta:
        model = EmailMessage
        fields = ['message_id', 'title',
                 'created_at', 'recipients', 'revoked']
        ordering = ['-created_at']


class EmailMessageRecipientCreateSerializer(serializers.Serializer):
    destination_email = serializers.EmailField(allow_null = False, allow_blank = False)


class EmailMessageCreateSerializer(serializers.Serializer):
    title = serializers.CharField(allow_null = False, allow_blank = False)
    content = serializers.CharField(allow_null = False, allow_blank = False)
    expires_at = serializers.DateTimeField(allow_null = False)
    recipients = EmailMessageRecipientCreateSerializer(
        many = True,
        allow_empty = False,
    )

class PasswordInputSerializer(serializers.Serializer):
    password = serializers.CharField(allow_null = False, allow_blank = False)