from django.db import transaction
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.projects.models import Project
from apps.reviews.models import Review, ReviewIssue, ReviewStatus
from apps.reviews.serializers import (
    CreateReviewSerializer,
    ReviewIssueSerializer,
    ReviewSerializer,
)
from apps.reviews.services.report_generator import ReportGenerator
from apps.reviews.tasks import start_review_task


class ReviewViewSet(viewsets.GenericViewSet):
    queryset = Review.objects.select_related("project").all()
    serializer_class = ReviewSerializer

    def list(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        project_id = request.query_params.get("project_id")
        if project_id:
            queryset = queryset.filter(project_id=project_id)
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

    def retrieve(self, request, pk=None):
        review = self.get_object()
        serializer = self.get_serializer(review)
        return Response({"success": True, "data": serializer.data})

    def create(self, request):
        project_id = request.data.get("project_id")
        if not project_id:
            return Response(
                {"success": False, "error": {"code": "MISSING_PROJECT", "message": "project_id is required"}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response(
                {"success": False, "error": {"code": "NOT_FOUND", "message": "Project not found"}},
                status=status.HTTP_404_NOT_FOUND,
            )

        input_serializer = CreateReviewSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            review = Review.objects.create(
                project=project,
                status=ReviewStatus.PENDING,
                ai_model="",
                ai_provider="",
                custom_instructions=input_serializer.validated_data.get("custom_instructions", ""),
            )
            transaction.on_commit(lambda: start_review_task.delay(str(review.id)))

        output_serializer = self.get_serializer(review)
        return Response(
            {"success": True, "data": output_serializer.data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"])
    def issues(self, request, pk=None):
        review = self.get_object()
        queryset = review.issues.all()

        severity = request.query_params.get("severity")
        if severity:
            severities = [s.strip() for s in severity.split(",") if s.strip()]
            if severities:
                queryset = queryset.filter(severity__in=severities)
        dimension = request.query_params.get("dimension")
        if dimension:
            dimensions = [d.strip() for d in dimension.split(",") if d.strip()]
            if dimensions:
                queryset = queryset.filter(dimension__in=dimensions)
        file_path = request.query_params.get("file_path")
        if file_path:
            queryset = queryset.filter(file_path__icontains=file_path)
        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ReviewIssueSerializer(page, many=True)
            return Response({
                "success": True,
                "data": serializer.data,
                "pagination": {
                    "count": self.paginator.page.paginator.count,
                    "next": self.paginator.get_next_link(),
                    "previous": self.paginator.get_previous_link(),
                },
            })
        serializer = ReviewIssueSerializer(queryset, many=True)
        return Response({"success": True, "data": serializer.data})

    @action(detail=True, methods=["get"])
    def report(self, request, pk=None):
        review = self.get_object()
        fmt = request.query_params.get("output", "json")
        issues = list(review.issues.all())

        generator = ReportGenerator()
        review_data = {
            "project_name": review.project.name,
            "ai_model": review.ai_model,
            "summary": review.summary,
        }

        if fmt == "markdown":
            md = generator.generate_markdown(review_data, issues)
            return Response({"success": True, "data": {"format": "markdown", "content": md}})
        else:
            result = generator.generate_json(review_data, issues)
            return Response({"success": True, "data": result})
