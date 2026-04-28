import io
import logging
import threading
from collections import Counter
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from apps.reviews.models import Review, ReviewIssue

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

SEVERITY_COLORS = {
    "critical": colors.HexColor("#cf1322"),
    "high": colors.HexColor("#d46b08"),
    "medium": colors.HexColor("#d4b106"),
    "low": colors.HexColor("#0958d9"),
}

SEVERITY_BG = {
    "critical": colors.HexColor("#fff1f0"),
    "high": colors.HexColor("#fff7e6"),
    "medium": colors.HexColor("#fffbe6"),
    "low": colors.HexColor("#e6f4ff"),
}

SEVERITY_LABELS = {
    "critical": "关键",
    "high": "高",
    "medium": "中",
    "low": "低",
}

DIMENSION_LABELS = {
    "security": "安全性",
    "correctness": "正确性",
    "performance": "性能",
    "maintainability": "可维护性",
    "type_safety": "类型安全",
    "completeness": "完整性",
    "best_practices": "最佳实践",
}


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
            "CNTitle", parent=base["Title"], fontName=_FONT_NAME, fontSize=22,
            spaceAfter=6, textColor=colors.HexColor("#1a1a1a"),
        ),
        "subtitle": ParagraphStyle(
            "CNSubtitle", parent=base["Normal"], fontName=_FONT_NAME, fontSize=10,
            spaceAfter=12, textColor=colors.grey,
        ),
        "heading": ParagraphStyle(
            "CNHeading", parent=base["Heading2"], fontName=_FONT_NAME, fontSize=14,
            spaceAfter=8, spaceBefore=12, textColor=colors.HexColor("#1890ff"),
        ),
        "body": ParagraphStyle(
            "CNBody", parent=base["Normal"], fontName=_FONT_NAME, fontSize=10, leading=14,
        ),
        "body_bold": ParagraphStyle(
            "CNBodyBold", parent=base["Normal"], fontName=_FONT_NAME, fontSize=10,
            leading=14, fontWeight="bold",
        ),
        "small": ParagraphStyle(
            "CNSmall", parent=base["Normal"], fontName=_FONT_NAME, fontSize=8, leading=11,
            textColor=colors.grey,
        ),
        "code": ParagraphStyle(
            "CNCode", parent=base["Code"], fontName="Courier", fontSize=8, leading=11,
            backColor=colors.HexColor("#f5f5f5"), leftIndent=8, rightIndent=8,
            spaceBefore=4, spaceAfter=4,
        ),
        "footer": ParagraphStyle(
            "CNFooter", parent=base["Normal"], fontName=_FONT_NAME, fontSize=8,
            textColor=colors.grey, alignment=1,
        ),
    }


def _safe(text: str | None) -> str:
    return escape(str(text or ""))


def _build_severity_chart(review: Review) -> Table:
    sev_keys = ["critical", "high", "medium", "low"]
    counts = [review.critical_count, review.high_count, review.medium_count, review.low_count]
    max_count = max(counts) if max(counts) > 0 else 1

    bar_max_width = 160
    rows = []
    for key, count in zip(sev_keys, counts):
        label = SEVERITY_LABELS[key]
        color = SEVERITY_COLORS[key]
        bar_width = int((count / max_count) * bar_max_width) if max_count > 0 else 0
        bar_color_hex = color.hexval()[2:]

        rows.append([
            Paragraph(f'<font color="{color.hexval()[2:]}">{label}</font>', _build_styles()["body_bold"]),
            _make_bar_cell(bar_width, color),
            Paragraph(str(count), _build_styles()["body_bold"]),
        ])

    table = Table(rows, colWidths=[50, 180, 40])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), _FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (2, 0), (2, -1), 8),
    ]))
    return table


def _make_bar_cell(width: int, color: colors.Color) -> Table:
    if width <= 0:
        inner = Table([[""]], colWidths=[1], rowHeights=[14])
        inner.setStyle(TableStyle([
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        return inner

    inner = Table([[""]], colWidths=[width], rowHeights=[14])
    inner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), color),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("ROUNDEDCORNERS", [3, 3, 3, 3]),
    ]))
    return inner


def _build_dimension_chart(issues: list[ReviewIssue]) -> Table:
    dim_counts: Counter = Counter()
    for issue in issues:
        dim_counts[issue.dimension] += 1

    dim_keys = ["security", "correctness", "performance", "maintainability",
                "type_safety", "completeness", "best_practices"]
    max_count = max((dim_counts.get(k, 0) for k in dim_keys), default=1) or 1

    bar_max_width = 140
    rows = []
    for key in dim_keys:
        count = dim_counts.get(key, 0)
        label = DIMENSION_LABELS.get(key, key)
        bar_width = int((count / max_count) * bar_max_width)

        rows.append([
            Paragraph(label, _build_styles()["body"]),
            _make_bar_cell(bar_width, colors.HexColor("#1890ff")),
            Paragraph(str(count), _build_styles()["body_bold"]),
        ])

    table = Table(rows, colWidths=[70, 160, 40])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), _FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (2, 0), (2, -1), 8),
    ]))
    return table


def _build_stats_cards(review: Review) -> Table:
    card_data = [
        ("问题总数", str(review.total_issues), colors.HexColor("#1890ff")),
        ("关键", str(review.critical_count), SEVERITY_COLORS["critical"]),
        ("高级", str(review.high_count), SEVERITY_COLORS["high"]),
        ("中级", str(review.medium_count), SEVERITY_COLORS["medium"]),
        ("低级", str(review.low_count), SEVERITY_COLORS["low"]),
    ]

    col_width = 90
    rows = []
    value_row = []
    label_row = []
    for label, value, color in card_data:
        value_row.append(Paragraph(
            f'<font size="18" color="{color.hexval()[2:]}">{value}</font>',
            ParagraphStyle("card_value", alignment=1, spaceBefore=8, spaceAfter=0),
        ))
        label_row.append(Paragraph(
            f'<font size="8" color="#999999">{label}</font>',
            ParagraphStyle("card_label", alignment=1, spaceBefore=0, spaceAfter=8),
        ))

    table = Table([value_row, label_row], colWidths=[col_width] * 5)
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), _FONT_NAME),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fafafa")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e8e8e8")),
        ("LINEAFTER", (0, 0), (3, -1), 0.5, colors.HexColor("#e8e8e8")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def _build_file_summary(issues: list[ReviewIssue]) -> Table:
    file_counts: Counter = Counter()
    file_severity: dict[str, Counter] = {}
    for issue in issues:
        file_counts[issue.file_path] += 1
        if issue.file_path not in file_severity:
            file_severity[issue.file_path] = Counter()
        file_severity[issue.file_path][issue.severity] += 1

    sorted_files = sorted(file_counts.items(), key=lambda x: -x[1])

    header = [
        Paragraph("<b>文件路径</b>", _build_styles()["body"]),
        Paragraph("<b>问题数</b>", _build_styles()["body"]),
        Paragraph("<b>严重</b>", _build_styles()["body"]),
        Paragraph("<b>高级</b>", _build_styles()["body"]),
        Paragraph("<b>中级</b>", _build_styles()["body"]),
        Paragraph("<b>低级</b>", _build_styles()["body"]),
    ]
    rows = [header]
    for filepath, count in sorted_files:
        sev = file_severity[filepath]
        rows.append([
            Paragraph(_safe(filepath), _build_styles()["body"]),
            Paragraph(str(count), _build_styles()["body_bold"]),
            Paragraph(str(sev.get("critical", 0)), _build_styles()["body"]),
            Paragraph(str(sev.get("high", 0)), _build_styles()["body"]),
            Paragraph(str(sev.get("medium", 0)), _build_styles()["body"]),
            Paragraph(str(sev.get("low", 0)), _build_styles()["body"]),
        ])

    table = Table(rows, colWidths=[240, 50, 40, 40, 40, 40])
    style_cmds = [
        ("FONTNAME", (0, 0), (-1, -1), _FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1890ff")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e8e8e8")),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for i in range(1, len(rows)):
        if i % 2 == 0:
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#fafafa")))
    table.setStyle(TableStyle(style_cmds))
    return table


def _build_issue_block(issue: ReviewIssue, index: int) -> list:
    styles = _build_styles()
    elements: list = []
    sev_color = SEVERITY_COLORS.get(issue.severity, colors.black)
    sev_bg = SEVERITY_BG.get(issue.severity, colors.white)
    sev_hex = sev_color.hexval()[2:]
    sev_label = SEVERITY_LABELS.get(issue.severity, issue.severity)
    dim_label = DIMENSION_LABELS.get(issue.dimension, issue.dimension)

    header_row = [
        Paragraph(
            f'<font color="{sev_hex}"><b>[{sev_label}]</b></font> {_safe(issue.title)}',
            styles["body_bold"],
        ),
    ]
    header_table = Table([header_row], colWidths=[460])
    header_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), _FONT_NAME),
        ("BACKGROUND", (0, 0), (-1, -1), sev_bg),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(header_table)

    meta_text = (
        f'<font color="#999999">'
        f'文件: {_safe(issue.file_path)} | 行: {issue.start_line}-{issue.end_line} | '
        f'维度: {_safe(dim_label)} | 置信度: {issue.confidence:.0%}'
        f'</font>'
    )
    elements.append(Paragraph(meta_text, styles["small"]))

    elements.append(Paragraph(_safe(issue.description), styles["body"]))

    if issue.suggestion:
        elements.append(Paragraph(
            f'<font color="#52c41a"><b>建议:</b></font> {_safe(issue.suggestion)}',
            styles["body"],
        ))

    if issue.code_snippet:
        code_lines = issue.code_snippet.strip()[:500]
        elements.append(Paragraph(
            f'<b>问题代码:</b>',
            styles["small"],
        ))
        elements.append(Paragraph(_safe(code_lines), styles["code"]))

    if issue.fix_snippet:
        fix_lines = issue.fix_snippet.strip()[:500]
        elements.append(Paragraph(
            f'<b>修复代码:</b>',
            styles["small"],
        ))
        elements.append(Paragraph(_safe(fix_lines), styles["code"]))

    elements.append(Spacer(1, 8))
    return elements


def generate_review_pdf(review: Review) -> bytes:
    _register_font()
    styles = _build_styles()
    buffer = io.BytesIO()

    page_w, page_h = A4
    margin = 20 * mm

    def _header_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(_FONT_NAME, 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(margin, page_h - 12 * mm, f"代码审查报告 — {review.project.name}")
        canvas.drawRightString(page_w - margin, page_h - 12 * mm,
                               review.completed_at.strftime("%Y-%m-%d") if review.completed_at else "")
        canvas.drawCentredString(page_w / 2, 10 * mm, f"— {doc.page} —")
        canvas.setStrokeColor(colors.HexColor("#e8e8e8"))
        canvas.line(margin, page_h - 14 * mm, page_w - margin, page_h - 14 * mm)
        canvas.line(margin, 14 * mm, page_w - margin, 14 * mm)
        canvas.restoreState()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    elements: list = []

    # --- Title Section ---
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(_safe(f"代码审查报告"), styles["title"]))
    elements.append(Paragraph(
        _safe(review.project.name),
        ParagraphStyle("project_name", fontName=_FONT_NAME, fontSize=14, textColor=colors.grey, spaceAfter=12),
    ))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1890ff")))
    elements.append(Spacer(1, 8))

    # --- Meta Info ---
    meta_data = [
        ["AI 模型", _safe(review.ai_model or "-")],
        ["审查状态", _safe(review.get_status_display())],
        ["创建时间", review.created_at.strftime("%Y-%m-%d %H:%M")],
        ["完成时间", review.completed_at.strftime("%Y-%m-%d %H:%M") if review.completed_at else "-"],
    ]
    meta_table = Table(meta_data, colWidths=[80, 380])
    meta_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), _FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#999999")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.HexColor("#f0f0f0")),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 16))

    # --- Summary ---
    if review.summary:
        elements.append(Paragraph("AI 总体评估", styles["heading"]))
        summary_table = Table(
            [[Paragraph(_safe(review.summary), styles["body"])]],
            colWidths=[460],
        )
        summary_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), _FONT_NAME),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f6ffed")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#b7eb8f")),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 16))

    # --- Stats Cards ---
    elements.append(Paragraph("问题概览", styles["heading"]))
    elements.append(_build_stats_cards(review))
    elements.append(Spacer(1, 16))

    # --- Charts (side by side) ---
    issues = list(
        review.issues.all()
        .order_by("-severity", "file_path", "start_line")[:MAX_ISSUES_IN_PDF]
    )

    left_chart = _build_severity_chart(review)
    right_chart = _build_dimension_chart(issues)

    left_col = []
    left_col.append(Paragraph("<b>严重性分布</b>", styles["body_bold"]))
    left_col.append(Spacer(1, 4))
    left_col.append(left_chart)

    right_col = []
    right_col.append(Paragraph("<b>维度分布</b>", styles["body_bold"]))
    right_col.append(Spacer(1, 4))
    right_col.append(right_chart)

    chart_table = Table(
        [[left_col, right_col]],
        colWidths=[230, 230],
    )
    chart_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
        ("RIGHTPADDING", (-1, 0), (-1, 0), 0),
    ]))
    elements.append(chart_table)
    elements.append(Spacer(1, 16))

    # --- File Summary ---
    if issues:
        elements.append(Paragraph("文件问题分布", styles["heading"]))
        elements.append(_build_file_summary(issues))
        elements.append(Spacer(1, 16))

    # --- Issue Details ---
    if issues:
        elements.append(PageBreak())
        elements.append(Paragraph(
            _safe(f"问题详情（共 {min(review.total_issues, MAX_ISSUES_IN_PDF)} 个）"),
            styles["heading"],
        ))
        for i, issue in enumerate(issues, 1):
            elements.extend(_build_issue_block(issue, i))

        if review.total_issues > MAX_ISSUES_IN_PDF:
            elements.append(Spacer(1, 12))
            elements.append(Paragraph(
                _safe(f"仅展示前 {MAX_ISSUES_IN_PDF} 个问题，共 {review.total_issues} 个"),
                styles["small"],
            ))

    try:
        doc.build(elements, onFirstPage=_header_footer, onLaterPages=_header_footer)
    except Exception:
        logger.error("PDF build failed for review %s", review.id, exc_info=True)
        raise

    return buffer.getvalue()
