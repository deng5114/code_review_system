from django.contrib import admin

from .models import AIConfig


@admin.register(AIConfig)
class AIConfigAdmin(admin.ModelAdmin):
    list_display = [
        "display_name",
        "provider",
        "model_name",
        "is_default",
        "is_active",
    ]
    list_filter = ["provider", "is_default", "is_active"]
    search_fields = ["display_name", "model_name"]
    readonly_fields = ["created_at", "updated_at", "masked_api_key_display"]
    exclude = ["_encrypted_api_key"]

    def masked_api_key_display(self, obj: AIConfig) -> str:
        return obj.masked_api_key

    masked_api_key_display.short_description = "API Key"
