import logging
import os
import re

from jinja2 import BaseLoader
from jinja2.sandbox import SandboxedEnvironment

logger = logging.getLogger(__name__)

_SAFE_LANGUAGE_RE = re.compile(r"^[a-z0-9_+-]+$")

_LANGUAGE_ALIASES: dict[str, str] = {
    "javascript": "typescript",
    "jsx": "typescript",
    "tsx": "typescript",
    "js": "typescript",
    "ts": "typescript",
    "py": "python",
    "golang": "go",
    "kt": "java",
    "kotlin": "java",
    "scala": "java",
}


class PromptEngine:
    """Prompt 组装引擎：加载模板，Jinja2 渲染，动态组装"""

    def __init__(self) -> None:
        self._prompts_dir = os.path.join(os.path.dirname(__file__), "..", "prompts")
        self._env = SandboxedEnvironment(loader=BaseLoader(), autoescape=False)

    def build_review_prompt(
        self,
        project_type: str,
        primary_language: str,
        frameworks: list[str],
        files: list[dict],
        custom_instructions: str = "",
        total_files: int | None = None,
    ) -> dict[str, str]:
        system_prompt = self._load_system_prompt()
        language_guidance = self._load_language_specific_guidance(primary_language)
        user_prompt = self._render_user_prompt(
            project_type=project_type,
            primary_language=primary_language,
            frameworks=frameworks,
            files=files,
            custom_instructions=custom_instructions,
            total_files=total_files or len(files),
            language_guidance=language_guidance,
        )
        return {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
        }

    def _load_system_prompt(self) -> str:
        path = os.path.join(self._prompts_dir, "system_base.txt")
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _load_language_specific_guidance(self, primary_language: str) -> str:
        normalized = primary_language.lower().strip()
        normalized = _LANGUAGE_ALIASES.get(normalized, normalized)
        if not _SAFE_LANGUAGE_RE.match(normalized):
            logger.warning("Invalid language name rejected: '%s'", primary_language)
            return ""
        path = os.path.join(
            self._prompts_dir, "language_specific", f"{normalized}.txt"
        )
        if not os.path.isfile(path):
            logger.debug(
                "No language-specific guidance for '%s', skipping",
                primary_language,
            )
            return ""
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _render_user_prompt(
        self,
        project_type: str,
        primary_language: str,
        frameworks: list[str],
        files: list[dict],
        custom_instructions: str,
        total_files: int,
        language_guidance: str,
    ) -> str:
        template_str = self._load_template("user_review.txt")
        template = self._env.from_string(template_str)
        return template.render(
            project_type=project_type,
            primary_language=primary_language,
            frameworks=frameworks,
            files=files,
            custom_instructions=custom_instructions,
            total_files=total_files,
            language_guidance=language_guidance,
        )

    def _load_template(self, filename: str) -> str:
        path = os.path.join(self._prompts_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
