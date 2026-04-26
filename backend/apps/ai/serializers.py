from rest_framework import serializers

from apps.ai.models import AIConfig


class AIConfigSerializer(serializers.ModelSerializer):
    api_key = serializers.CharField(write_only=True, min_length=8)
    masked_api_key = serializers.CharField(read_only=True)

    class Meta:
        model = AIConfig
        fields = [
            "id", "provider", "display_name", "api_key",
            "masked_api_key", "model_name", "base_url",
            "is_default", "is_active", "priority", "fallback_enabled",
            "extra_settings", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "masked_api_key", "created_at", "updated_at"]

    def create(self, validated_data: dict) -> AIConfig:
        raw_key = validated_data.pop("api_key")
        instance = AIConfig(**validated_data)
        instance.api_key = raw_key
        instance.save()
        return instance

    def update(self, instance: AIConfig, validated_data: dict) -> AIConfig:
        raw_key = validated_data.pop("api_key", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if raw_key is not None:
            instance.api_key = raw_key
        instance.save()
        return instance


class AITestConnectionSerializer(serializers.Serializer):
    config_id = serializers.UUIDField(required=False)
    provider = serializers.CharField(required=False)
    model_name = serializers.CharField(required=False)
    api_key = serializers.CharField(required=False)
    base_url = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, data: dict) -> dict:
        if data.get("config_id"):
            return data
        required = {"provider", "model_name", "api_key"}
        missing = required - set(data.keys())
        if missing:
            raise serializers.ValidationError(
                f"必须提供 config_id 或 {', '.join(missing)}"
            )
        return data
