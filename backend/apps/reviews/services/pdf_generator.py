import io
import logging
import threading
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from apps.reviews.models import Review

logger = logging.getLogger(__name__)

_font_paths = [
    Path("C:/Windows/Fonts/msyh.ttc"),
    Path("C:/Windows/Fonts/simhei.ttf"),
    Path("C:/Windows/Fonts/simsun.ttc"),
]

_FONT_NAME = "ChineseFont"
_font_registered = False
_font_lock = threading.Lock()

MAX_ISSUES_IN_PDF = 500


def _register_font() -> None:
    global _font_registered
    with _font_lock:
        if _font_registered:
            return
        for path in _font_paths:
            if path.exists():
                try:
                    pdfmetrics.registerFont(TTFont(_FONT_NAME, str(path), subfontIndex=0))
                    _font_registered = True
                    return
                except Exception:
                    logger.warning("Failed to register font %s", path, exc_info=True)
        _font_registered = True


def _build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "CNTitle", parent=base["Title"], fontName=_FONT_NAME, fontSize=20, spaceAfter=12,
        ),
        "heading": ParagraphStyle(
            "CNHeading", parent=base["Heading2"], fontName=_FONT_NAME, fontSize=14, spaceAfter=8,
        ),
        "body": ParagraphStyle(
            "CNBody", parent=base["Normal"], fontName=_FONT_NAME, fontSize=10, leading=14,
        ),
        "code": ParagraphStyle(
            "CNCode", parent=base["Code"], fontName="Courier", fontSize=9, leading=12,
        ),
    }


SEVERITY_COLORS = {
    "critical": colors.red,
    "high": colors.orange,
    "medium": colors.gold,
    "low": colors.lightblue,
}


def _safe(text: str | None) -> str:
    return escape(str(text or ""))


def generate_review_pdf(review: Review) -> bytes:
    _register_font()
    styles = _build_styles()
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    elements: list = []

    elements.append(Paragraph(_safe(f"代码审查报告 — {review.project.name}"), styles["title"]))
    elements.append(Spacer(1, 8))

    meta_data = [
        ["AI 模型", _safe(review.ai_model)],
        ["审查状态", _safe(review.get_status_display())],
        ["创建时间", review.created_at.strftime("%Y-%m-%d %H:%M")],
        ["完成时间", review.completed_at.strftime("%Y-%m-%d %H:%M") if review.completed_at else "-"],
    ]
    meta_table = Table(meta_data, colWidths=[80, 300])
    meta_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), _FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 12))

    if review.summary:
        elements.append(Paragraph("审查摘要", styles["heading"]))
        elements.append(Paragraph(_safe(review.summary), styles["body"]))
        elements.append(Spacer(1, 12))

    elements.append(Paragraph("问题统计", styles["heading"]))
    stats_data = [
        ["严重", "高", "中", "低", "总计"],
        [str(review.critical_count), str(review.high_count), str(review.medium_count), str(review.low_count), str(review.total_issues)],
    ]
    stats_table = Table(stats_data, colWidths=[76, 76, 76, 76, 76])
    stats_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), _FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(stats_table)
    elements.append(Spacer(1, 16))

    issues = list(
        review.issues.all()
        .order_by("-severity", "file_path", "start_line")[:MAX_ISSUES_IN_PDF]
    )
    if issues:
        elements.append(Paragraph(
            _safe(f"问题详情（共 {min(review.total_issues, MAX_ISSUES_IN_PDF)} 个）"),
            styles["heading"],
        ))
        for i, issue in enumerate(issues, 1):
            title_text = _safe(f"{i}. [{issue.get_severity_display()}] {issue.title}")
            elements.append(Paragraph(title_text, styles["body"]))
            elements.append(Paragraph(
                f"<font color='grey'>文件: {_safe(issue.file_path)} | 行: {issue.start_line}-{issue.end_line} | 维度: {_safe(issue.get_dimension_display())}</font>",
                styles["body"],
            ))
            elements.append(Paragraph(f"描述: {_safe(issue.description)}", styles["body"]))
            if issue.suggestion:
                elements.append(Paragraph(f"建议: {_safe(issue.suggestion)}", styles["body"]))
            elements.append(Spacer(1, 8))

        if review.total_issues > MAX_ISSUES_IN_PDF:
            elements.append(Spacer(1, 8))
            elements.append(Paragraph(
                _safe(f"（仅展示前 {MAX_ISSUES_IN_PDF} 个问题，共 {review.total_issues} 个）"),
                styles["body"],
            ))

    try:
        doc.build(elements)
    except Exception:
        logger.error("PDF build failed for review %s", review.id, exc_info=True)
        raise

    return buffer.getvalue()
