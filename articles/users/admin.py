from django.contrib import admin
from .models import Profile, Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'recipient', 'created_at', 'read_at')
    list_filter = ('created_at',)
    search_fields = ('body', 'sender__username', 'recipient__username')


admin.site.register(Profile)
