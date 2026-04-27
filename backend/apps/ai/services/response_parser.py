import json
import re
from dataclasses import dataclass, field

VALID_SEVERITIES = {"critical", "high", "medium", "low"}
VALID_DIMENSIONS = {
    "security", "correctness", "performance",
    "maintainability", "type_safety", "completeness", "best_practices",
}
REQUIRED_ISSUE_FIELDS = {"file_path", "severity", "dimension", "title", "description"}


@dataclass(frozen=True)
class ParsedIssue:
    file_path: str
    start_line: int
    end_line: int
    severity: str
    dimension: str
    title: str
    description: str
    suggestion: str
    confidence: float
    code_snippet: str = ""
    fix_snippet: str = ""


@dataclass(frozen=True)
class ParsedReviewResponse:
    summary: str = ""
    issues: list[ParsedIssue] = field(default_factory=list)


class ResponseParser:
    """AI 响应解析器：多层容错 JSON 提取和验证"""

    def parse(self, raw_response: str | None) -> ParsedReviewResponse:
        if not raw_response:
            return ParsedReviewResponse()

        data = self._extract_json(raw_response)
        if data is None:
            return ParsedReviewResponse()

        return self._build_response(data)

    def _extract_json(self, text: str) -> dict | None:
        # 1. 直接解析
        data = self._try_parse_json(text)
        if data:
            return data

        # 2. 从 markdown 代码块提取
        data = self._extract_from_code_block(text)
        if data:
            return data

        # 3. 从文本中搜索 JSON 对象
        data = self._extract_embedded_json(text)
        if data:
            return data

        return None

    def _try_parse_json(self, text: str) -> dict | None:
        text = text.strip()
        if not text.startswith("{"):
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return self._try_parse_with_fixes(text)

    def _try_parse_with_fixes(self, text: str) -> dict | None:
        fixed = self._fix_json(text)
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            return None

    def _extract_from_code_block(self, text: str) -> dict | None:
        patterns = [
            r"```json\s*\n(.*?)\n```",
            r"```\s*\n(.*?)\n```",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                content = match.group(1).strip()
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    fixed = self._fix_json(content)
                    try:
                        return json.loads(fixed)
                    except json.JSONDecodeError:
                        continue
        return None

    def _extract_embedded_json(self, text: str) -> dict | None:
        # 找到第一个 { 和最后一个 }
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        candidate = text[start:end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            fixed = self._fix_json(candidate)
            try:
                return json.loads(fixed)
            except json.JSONDecodeError:
                return None

    def _fix_json(self, text: str) -> str:
        result = text
        # 修复单引号
        result = re.sub(r"'", '"', result)
        # 修复尾逗号
        result = re.sub(r",\s*([}\]])", r"\1", result)
        # 移除 JS 风格注释
        result = re.sub(r"//[^\n]*", "", result)
        # 修复未加引号的键
        result = re.sub(r"(?<!['\"])(\w+)\s*:", r'"\1":', result)
        return result

    def _build_response(self, data: dict) -> ParsedReviewResponse:
        summary = str(data.get("summary", ""))
        raw_issues = data.get("issues", [])

        if not isinstance(raw_issues, list):
            raw_issues = []

        issues: list[ParsedIssue] = []
        for raw in raw_issues:
            if not isinstance(raw, dict):
                continue
            if not REQUIRED_ISSUE_FIELDS.issubset(raw.keys()):
                continue
            issue = self._validate_issue(raw)
            if issue:
                issues.append(issue)

        return ParsedReviewResponse(summary=summary, issues=issues)

    def _validate_issue(self, raw: dict) -> ParsedIssue | None:
        try:
            severity = str(raw.get("severity", "")).lower().strip()
            if severity not in VALID_SEVERITIES:
                severity = "medium"

            dimension = str(raw.get("dimension", "")).lower().strip()
            if dimension not in VALID_DIMENSIONS:
                dimension = "best_practices"

            confidence = float(raw.get("confidence", 0.7))
            confidence = max(0.0, min(1.0, confidence))

            return ParsedIssue(
                file_path=str(raw.get("file_path", "")),
                start_line=int(raw.get("start_line", 0)),
                end_line=int(raw.get("end_line", 0)),
                severity=severity,
                dimension=dimension,
                title=str(raw.get("title", "")),
                description=str(raw.get("description", "")),
                suggestion=str(raw.get("suggestion", "")),
                confidence=confidence,
                code_snippet=str(raw.get("code_snippet", "")),
                fix_snippet=str(raw.get("fix_snippet", "")),
            )
        except (ValueError, TypeError):
            return None
