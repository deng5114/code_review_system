from django.core import signing
from django.core.exceptions import ValidationError
from django.db import models

from apps.common.models import TimestampMixin, UUIDMixin

# 使用 Django signing 进行可逆加密，基于 SECRET_KEY
_signer = signing.Signer()


class AIProvider(models.TextChoices):
    OPENAI = "openai", "OpenAI"
    ANTHROPIC = "anthropic", "Anthropic"
    GOOGLE = "google", "Google"
    DEEPSEEK = "deepseek", "DeepSeek"
    OLLAMA = "ollama", "Ollama"
    OPENROUTER = "openrouter", "OpenRouter"


class AIConfig(UUIDMixin, TimestampMixin):
    provider = models.CharField(
        max_length=50, choices=AIProvider.choices, verbose_name="提供商"
    )
    display_name = models.CharField(max_length=100, verbose_name="显示名称")
    _encrypted_api_key = models.CharField(
        max_length=500, db_column="api_key", verbose_name="API Key(加密)"
    )
    model_name = models.CharField(max_length=100, verbose_name="模型名称")
    base_url = models.CharField(
        max_length=500, blank=True, verbose_name="API 端点"
    )
    is_default = models.BooleanField(default=False, verbose_name="默认配置")
    is_active = models.BooleanField(default=True, verbose_name="启用")
    extra_settings = models.JSONField(default=dict, verbose_name="额外设置")

    class Meta:
        db_table = "ai_aiconfig"
        verbose_name = "AI 配置"
        verbose_name_plural = "AI 配置"
        ordering = ["-is_default", "created_at"]

    def __str__(self) -> str:
        return f"{self.display_name} ({self.model_name})"

    @property
    def api_key(self) -> str:
        """解密并返回 API Key"""
        try:
            return _signer.unsign(self._encrypted_api_key)
        except signing.BadSignature:
            return self._encrypted_api_key

    @api_key.setter
    def api_key(self, value: str) -> None:
        """加密并存储 API Key"""
        self._encrypted_api_key = _signer.sign(value)

    def clean(self) -> None:
        if self.is_default:
            exists = AIConfig.objects.filter(is_default=True).exclude(
                pk=self.pk
            )
            if exists.exists():
                raise ValidationError("只能有一个默认配置")
        if self.provider == AIProvider.OLLAMA and not self.base_url:
            raise ValidationError("Ollama 必须配置 base_url")

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def masked_api_key(self) -> str:
        raw = self.api_key
        if not raw or len(raw) < 8:
            return "****"
        return f"{'*' * (len(raw) - 4)}{raw[-4:]}"
