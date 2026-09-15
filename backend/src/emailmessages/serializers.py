from rest_framework import serializers
from .models import EmailMessage

class EmailMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailMessage
        fields = ['message_id', 'max_views', 'created_at', 'password_given_out_at', 'destination_email']