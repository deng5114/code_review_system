import os

from jinja2 import BaseLoader, Environment


class PromptEngine:
    """Prompt 组装引擎：加载模板，Jinja2 渲染，动态组装"""

    def __init__(self) -> None:
        self._prompts_dir = os.path.join(os.path.dirname(__file__), "..", "prompts")
        self._env = Environment(loader=BaseLoader(), autoescape=False)

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
        user_prompt = self._render_user_prompt(
            project_type=project_type,
            primary_language=primary_language,
            frameworks=frameworks,
            files=files,
            custom_instructions=custom_instructions,
            total_files=total_files or len(files),
        )
        return {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
        }

    def _load_system_prompt(self) -> str:
        path = os.path.join(self._prompts_dir, "system_base.txt")
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
        )

    def _load_template(self, filename: str) -> str:
        path = os.path.join(self._prompts_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
