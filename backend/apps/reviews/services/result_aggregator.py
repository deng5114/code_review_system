from dataclasses import dataclass

from apps.ai.services.response_parser import ParsedIssue

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
DOWNGRADE_MAP = {"critical": "high", "high": "medium", "medium": "low", "low": "low"}


@dataclass(frozen=True)
class AggregatedResult:
    issues: list[ParsedIssue]
    stats: dict


class ResultAggregator:
    def __init__(self, confidence_threshold: float = 0.5) -> None:
        self._confidence_threshold = confidence_threshold

    def aggregate(self, issues: list[ParsedIssue]) -> AggregatedResult:
        deduplicated = self._deduplicate(issues)
        adjusted = self._adjust_confidence(deduplicated)
        stats = self._compute_stats(adjusted)
        return AggregatedResult(issues=adjusted, stats=stats)

    def _deduplicate(self, issues: list[ParsedIssue]) -> list[ParsedIssue]:
        if not issues:
            return []
        seen: dict[tuple, ParsedIssue] = {}
        for issue in issues:
            key = (issue.file_path, issue.title, issue.dimension)
            if key in seen:
                existing = seen[key]
                new_start = min(existing.start_line, issue.start_line)
                new_end = max(existing.end_line, issue.end_line)
                seen[key] = ParsedIssue(
                    file_path=issue.file_path,
                    start_line=new_start,
                    end_line=new_end,
                    severity=self._pick_higher_severity(existing.severity, issue.severity),
                    dimension=issue.dimension,
                    title=issue.title,
                    description=existing.description if len(existing.description) >= len(issue.description) else issue.description,
                    suggestion=existing.suggestion,
                    code_snippet=existing.code_snippet,
                    fix_snippet=existing.fix_snippet,
                    confidence=max(existing.confidence, issue.confidence),
                )
            else:
                seen[key] = issue
        return list(seen.values())

    def _adjust_confidence(self, issues: list[ParsedIssue]) -> list[ParsedIssue]:
        result = []
        for issue in issues:
            if issue.confidence < self._confidence_threshold:
                new_severity = DOWNGRADE_MAP.get(issue.severity, issue.severity)
                result.append(ParsedIssue(
                    file_path=issue.file_path,
                    start_line=issue.start_line,
                    end_line=issue.end_line,
                    severity=new_severity,
                    dimension=issue.dimension,
                    title=issue.title,
                    description=issue.description,
                    suggestion=issue.suggestion,
                    code_snippet=issue.code_snippet,
                    fix_snippet=issue.fix_snippet,
                    confidence=issue.confidence,
                ))
            else:
                result.append(issue)
        return result

    def _compute_stats(self, issues: list[ParsedIssue]) -> dict:
        stats: dict = {
            "total": len(issues),
            "critical_count": 0,
            "high_count": 0,
            "medium_count": 0,
            "low_count": 0,
            "by_dimension": {},
            "by_file": {},
        }
        for issue in issues:
            key = f"{issue.severity}_count"
            if key in stats:
                stats[key] += 1
            stats["by_dimension"][issue.dimension] = stats["by_dimension"].get(issue.dimension, 0) + 1
            stats["by_file"][issue.file_path] = stats["by_file"].get(issue.file_path, 0) + 1
        return stats

    def _pick_higher_severity(self, a: str, b: str) -> str:
        if SEVERITY_ORDER.get(a, 99) <= SEVERITY_ORDER.get(b, 99):
            return a
        return b
