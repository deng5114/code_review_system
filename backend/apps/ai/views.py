import ipaddress
import logging
from urllib.parse import urlparse

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.ai.models import AIConfig
from apps.ai.serializers import AIConfigSerializer, AITestConnectionSerializer
from apps.ai.services.llm_adapter import LLMAdapter, LLMCallError, LLMConfig

logger = logging.getLogger(__name__)

BLOCKED_HOSTS = frozenset({"localhost", "127.0.0.1", "0.0.0.0", "::1"})


def _is_safe_url(url: str) -> bool:
    if not url:
        return True
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    if hostname in BLOCKED_HOSTS:
        return False
    try:
        ip = ipaddress.ip_address(hostname)
        return not ip.is_private
    except ValueError:
        pass
    if hostname.endswith((".internal", ".local", ".localhost")):
        return False
    return True


class AIConfigViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]
    queryset = AIConfig.objects.all()
    serializer_class = AIConfigSerializer

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return Response({
                "success": True,
                "data": serializer.data,
                "pagination": {
                    "count": self.paginator.page.paginator.count,
                    "next": self.paginator.get_next_link(),
                    "previous": self.paginator.get_previous_link(),
                },
            })
        serializer = self.get_serializer(queryset, many=True)
        return Response({"success": True, "data": serializer.data})

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"success": True, "data": serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({"success": True, "data": serializer.data})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(
            {"success": True, "data": {"message": "配置已删除"}},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="test-connection")
    def test_connection(self, request):
        serializer = AITestConnectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if data.get("config_id"):
            try:
                config_obj = AIConfig.objects.get(id=data["config_id"], owner=request.user)
                llm_config = LLMConfig.from_ai_config(config_obj)
            except AIConfig.DoesNotExist:
                return Response(
                    {
                        "success": False,
                        "error": {"code": "NOT_FOUND", "message": "配置不存在"},
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            base_url = data.get("base_url", "")
            if not _is_safe_url(base_url):
                return Response(
                    {
                        "success": False,
                        "error": {"code": "BLOCKED_URL", "message": "不允许的 base_url"},
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            llm_config = LLMConfig(
                provider=data["provider"],
                model_name=data["model_name"],
                api_key=data["api_key"],
                base_url=base_url,
                extra_settings={},
            )

        adapter = LLMAdapter(max_retries=1, retry_delay=0.1)
        try:
            result = adapter.chat_completion(
                config=llm_config,
                messages=[{"role": "user", "content": "Hello, respond with 'ok'"}],
            )
            return Response(
                {
                    "success": True,
                    "data": {
                        "connected": True,
                        "response_preview": result.content[:200],
                        "tokens_used": result.total_tokens,
                    },
                }
            )
        except LLMCallError as e:
            return Response(
                {
                    "success": True,
                    "data": {
                        "connected": False,
                        "error": str(e),
                    },
                }
            )
        except Exception as e:
            logger.exception("Unexpected error during connection test")
            return Response(
                {
                    "success": False,
                    "error": {"code": "INTERNAL_ERROR", "message": "连接测试失败"},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
