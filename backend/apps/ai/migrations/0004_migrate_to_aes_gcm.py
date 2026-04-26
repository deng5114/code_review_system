"""Migrate existing API keys from Django signing to AES-GCM encryption."""

import logging

from django.core import signing
from django.db import migrations

logger = logging.getLogger(__name__)


def _get_aes():
    """Lazy-load AESEncryption to avoid import issues at migration time."""
    from apps.common.services.crypto import AESEncryption

    aes = AESEncryption()
    if not aes.available:
        logger.warning(
            "AES_ENCRYPTION_KEY not configured, skipping AES-GCM migration"
        )
    return aes


def migrate_to_aes_gcm(apps, schema_editor):
    aes = _get_aes()
    if not aes.available:
        return

    AIConfig = apps.get_model("ai", "AIConfig")
    signer = signing.Signer()
    updated = 0

    for config in AIConfig.objects.all():
        # Historical model from apps.get_model has no property accessors,
        # so config.api_key reads the raw db column value directly.
        raw_value = config.api_key
        try:
            plaintext = signer.unsign(raw_value)
        except signing.BadSignature:
            logger.warning(
                "Skipping AIConfig %s: BadSignature (may already be AES-encrypted)",
                config.pk,
            )
            continue

        config.api_key = aes.encrypt(plaintext)
        # Bypass model save() validation to avoid issues with migration-time models
        AIConfig.objects.filter(pk=config.pk).update(
            api_key=config._encrypted_api_key
        )
        updated += 1

    logger.info("Migrated %d API keys to AES-GCM", updated)


def rollback_to_django_signing(apps, schema_editor):
    aes = _get_aes()
    if not aes.available:
        return

    from apps.common.services.crypto import AESEncryption as AESClass

    AIConfig = apps.get_model("ai", "AIConfig")
    signer = signing.Signer()
    reverted = 0

    for config in AIConfig.objects.all():
        # Historical model from apps.get_model has no property accessors,
        # so config.api_key reads the raw db column value directly.
        raw_value = config.api_key
        if not AESClass.is_aes_encrypted(raw_value):
            continue
        try:
            plaintext = aes.decrypt(raw_value)
        except Exception:
            logger.warning("Skipping AIConfig %s: AES decrypt failed", config.pk)
            continue

        signed_value = signer.sign(plaintext)
        AIConfig.objects.filter(pk=config.pk).update(api_key=signed_value)
        reverted += 1

    logger.info("Reverted %d API keys to Django signing", reverted)


class Migration(migrations.Migration):

    dependencies = [
        ("ai", "0003_add_priority_and_fallback_fields"),
    ]

    operations = [
        migrations.RunPython(
            migrate_to_aes_gcm,
            rollback_to_django_signing,
        ),
    ]
