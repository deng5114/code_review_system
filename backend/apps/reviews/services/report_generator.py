SEVERITY_LABELS = {
    "critical": "CRITICAL",
    "high": "HIGH",
    "medium": "MEDIUM",
    "low": "LOW",
}


class ReportGenerator:
    def generate_markdown(self, review_data: dict, issues: list) -> str:
        project_name = review_data.get("project_name", "Unknown")
        summary = review_data.get("summary", "")
        ai_model = review_data.get("ai_model", "")

        sections: list[str] = []
        sections.append(f"# Code Review Report — {project_name}\n")
        sections.append(f"**AI Model**: {ai_model}\n")

        if summary:
            sections.append(f"\n## Summary\n\n{summary}\n")

        if not issues:
            sections.append("\n**No issues found.** The code looks good!\n")
            return "\n".join(sections)

        stats = self._compute_stats(issues)
        sections.append(f"\n## Statistics\n")
        sections.append(f"- Total issues: {stats['total']}")
        sections.append(f"- Critical: {stats['critical_count']} | High: {stats['high_count']} | Medium: {stats['medium_count']} | Low: {stats['low_count']}\n")

        sections.append("\n## Issues\n")
        current_file = ""
        for issue in sorted(issues, key=lambda i: (i.file_path, i.start_line)):
            if issue.file_path != current_file:
                current_file = issue.file_path
                sections.append(f"\n### `{current_file}`\n")
            label = SEVERITY_LABELS.get(issue.severity, issue.severity.upper())
            sections.append(f"- **[{label}]** L{issue.start_line}-{issue.end_line}: {issue.title}")
            sections.append(f"  - {issue.description}")
            if issue.suggestion:
                sections.append(f"  - Suggestion: {issue.suggestion}")
            if issue.code_snippet:
                sections.append(f"  ```\n  {issue.code_snippet}\n  ```")
            if issue.fix_snippet:
                sections.append(f"  Fix:\n  ```\n  {issue.fix_snippet}\n  ```")
            sections.append("")

        return "\n".join(sections)

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
