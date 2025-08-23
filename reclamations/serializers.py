from rest_framework import serializers
from .models import Reclamation, User

class ReclamationSerializer(serializers.ModelSerializer):
    client_email = serializers.EmailField(source='client.email', read_only=True)
    specialist_email = serializers.EmailField(source='specialist.email', read_only=True, allow_null=True)
    attachment_url = serializers.SerializerMethodField()

    class Meta:
        model = Reclamation
        fields = [
            'id',
            'title',
            'description',
            'status',
            'priority',
            'created_at',
            'client_email',
            'specialist_email',
            'attachment_url'
        ]
        extra_kwargs = {
            'client': {'write_only': True},
            'specialist': {'write_only': True, 'required': False},
            'status': {'required': False}
        }

    def get_attachment_url(self, obj):
        if obj.attachment:
            return self.context['request'].build_absolute_uri(obj.attachment.url)
        return None