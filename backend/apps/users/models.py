from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """自定义用户模型，支持后续扩展字段。"""

    class Meta(AbstractUser.Meta):
        db_table = "users_user"
        verbose_name = "用户"
        verbose_name_plural = "用户"
