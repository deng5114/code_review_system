from collections import Counter

SEVERITY_LABELS = {
    "critical": "关键",
    "high": "高级",
    "medium": "中级",
    "low": "低级",
}

SEVERITY_EMOJI = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🔵",
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


class ReportGenerator:
    def generate_markdown(self, review_data: dict, issues: list) -> str:
        project_name = review_data.get("project_name", "Unknown")
        summary = review_data.get("summary", "")
        ai_model = review_data.get("ai_model", "")

        lines: list[str] = []

        # Title
        lines.append(f"# 代码审查报告 — {project_name}\n")
        lines.append(f"> AI 模型: `{ai_model}`\n")

        # Summary
        if summary:
            lines.append("## AI 总体评估\n")
            lines.append(f"> {summary}\n")

        # Stats
        stats = self._compute_stats(issues)
        lines.append("## 问题概览\n")
        lines.append(f"| 指标 | 数量 |")
        lines.append(f"|:----:|:----:|")
        lines.append(f"| 问题总数 | **{stats['total']}** |")
        lines.append(
            f"| {SEVERITY_EMOJI['critical']} 关键 | **{stats['critical_count']}** |"
        )
        lines.append(
            f"| {SEVERITY_EMOJI['high']} 高级 | **{stats['high_count']}** |"
        )
        lines.append(
            f"| {SEVERITY_EMOJI['medium']} 中级 | **{stats['medium_count']}** |"
        )
        lines.append(
            f"| {SEVERITY_EMOJI['low']} 低级 | **{stats['low_count']}** |\n"
        )

        if not issues:
            lines.append("**未发现问题，代码质量良好！**\n")
            return "\n".join(lines)

        # Severity distribution bar (text-based)
        lines.append("### 严重性分布\n")
        total = max(stats["total"], 1)
        for sev in ["critical", "high", "medium", "low"]:
            count = stats[f"{sev}_count"]
            pct = count / total * 100
            bar_len = int(pct / 2)
            bar = "█" * bar_len + "░" * (50 - bar_len)
            lines.append(
                f"- {SEVERITY_EMOJI[sev]} **{SEVERITY_LABELS[sev]}**: "
                f"`{bar}` {count} ({pct:.0f}%)"
            )
        lines.append("")

        # Dimension distribution
        lines.append("### 维度分布\n")
        dim_counts: Counter = Counter()
        for issue in issues:
            dim_counts[issue.dimension] += 1
        dim_sorted = dim_counts.most_common()
        for dim, count in dim_sorted:
            label = DIMENSION_LABELS.get(dim, dim)
            pct = count / total * 100
            bar_len = int(pct / 2)
            bar = "▓" * bar_len + "░" * (50 - bar_len)
            lines.append(f"- **{label}**: `{bar}` {count} ({pct:.0f}%)")
        lines.append("")

        # File summary
        lines.append("## 文件问题分布\n")
        lines.append("| 文件路径 | 问题数 | 关键 | 高级 | 中级 | 低级 |")
        lines.append("|:---------|:------:|:----:|:----:|:----:|:----:|")
        file_counts: Counter = Counter()
        file_sev: dict[str, Counter] = {}
        for issue in issues:
            file_counts[issue.file_path] += 1
            if issue.file_path not in file_sev:
                file_sev[issue.file_path] = Counter()
            file_sev[issue.file_path][issue.severity] += 1
        for filepath, count in sorted(file_counts.items(), key=lambda x: -x[1]):
            sev = file_sev[filepath]
            lines.append(
                f"| `{filepath}` | **{count}** | "
                f"{sev.get('critical', 0)} | {sev.get('high', 0)} | "
                f"{sev.get('medium', 0)} | {sev.get('low', 0)} |"
            )
        lines.append("")

        # Issue details
        lines.append("## 问题详情\n")
        current_file = ""
        for issue in sorted(issues, key=lambda i: (i.file_path, i.start_line)):
            if issue.file_path != current_file:
                current_file = issue.file_path
                lines.append(f"### 📄 `{current_file}`\n")

            sev_emoji = SEVERITY_EMOJI.get(issue.severity, "")
            sev_label = SEVERITY_LABELS.get(issue.severity, issue.severity.upper())
            dim_label = DIMENSION_LABELS.get(issue.dimension, issue.dimension)
            confidence_pct = f"{issue.confidence:.0%}"

            lines.append(
                f"#### {sev_emoji} [{sev_label}] {issue.title}\n"
            )
            lines.append(f"- **位置**: L{issue.start_line}-{issue.end_line}")
            lines.append(f"- **维度**: {dim_label}")
            lines.append(f"- **置信度**: {confidence_pct}")
            lines.append(f"\n{issue.description}\n")

            if issue.suggestion:
                lines.append(f"> 💡 **建议**: {issue.suggestion}\n")

            if issue.code_snippet:
                lines.append("**问题代码**:")
                lines.append(f"```python\n{issue.code_snippet}\n```\n")

            if issue.fix_snippet:
                lines.append("**修复代码**:")
                lines.append(f"```python\n{issue.fix_snippet}\n```\n")

            lines.append("---\n")

        return "\n".join(lines)

    def generate_json(self, review_data: dict, issues: list) -> dict:
        stats = self._compute_stats(issues)
        return {
            "project_name": review_data.get("project_name", ""),
            "ai_model": review_data.get("ai_model", ""),
            "summary": review_data.get("summary", ""),
            "total_issues": len(issues),
            "issues": [
                {
                    "file_path": i.file_path,
                    "start_line": i.start_line,
                    "end_line": i.end_line,
                    "severity": i.severity,
                    "dimension": i.dimension,
                    "title": i.title,
                    "description": i.description,
                    "suggestion": i.suggestion,
                    "code_snippet": i.code_snippet,
                    "fix_snippet": i.fix_snippet,
                    "confidence": i.confidence,
                }
                for i in issues
            ],
            "stats": stats,
        }

    def _compute_stats(self, issues: list) -> dict:
        stats = {"total": len(issues), "critical_count": 0, "high_count": 0, "medium_count": 0, "low_count": 0}
        for issue in issues:
            key = f"{issue.severity}_count"
            if key in stats:
                stats[key] += 1
        return stats
