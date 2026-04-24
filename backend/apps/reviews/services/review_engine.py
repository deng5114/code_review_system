import logging
from typing import Callable

from apps.ai.services.llm_adapter import LLMAdapter, LLMCallError, LLMConfig
from apps.ai.services.prompt_engine import PromptEngine
from apps.ai.services.response_parser import ResponseParser
from apps.reviews.services.chunk_manager import ChunkManager
from apps.reviews.services.result_aggregator import ResultAggregator

logger = logging.getLogger(__name__)


class ReviewEngine:
    def __init__(self, context_window: int = 128000) -> None:
        self._chunk_manager = ChunkManager(context_window=context_window)
        self._prompt_engine = PromptEngine()
        self._response_parser = ResponseParser()
        self._result_aggregator = ResultAggregator()

    def run_review(
        self,
        project_type: str,
        primary_language: str,
        frameworks: list[str],
        files: list[dict],
        ai_config: LLMConfig,
        custom_instructions: str = "",
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> dict:
        total_files = len(files)

        def _progress(pct: int, msg: str) -> None:
            if progress_callback:
                progress_callback(pct, msg)

        try:
            # Stage 1-2: Filter
            _progress(5, "Preparing files...")
            reviewable = [f for f in files if not f.get("is_vendor") and not f.get("is_generated")]
            if not reviewable:
                _progress(100, "No reviewable files")
                return {"status": "completed", "summary": "No reviewable files found.", "issues": [], "stats": {"total": 0, "critical_count": 0, "high_count": 0, "medium_count": 0, "low_count": 0}}

            # Stage 3-4: Chunk
            _progress(10, "Planning review strategy...")
            chunks = self._chunk_manager.plan_chunks(reviewable)
            total_chunks = len(chunks)

            # Stage 5-6: AI review each chunk
            adapter = LLMAdapter(max_retries=3)
            all_parsed_issues = []
            all_summaries = []

            for i, chunk in enumerate(chunks):
                chunk_progress = 15 + int((i / total_chunks) * 70)
                _progress(chunk_progress, f"Reviewing chunk {i + 1}/{total_chunks}...")

                prompt_result = self._prompt_engine.build_review_prompt(
                    project_type=project_type,
                    primary_language=primary_language,
                    frameworks=frameworks,
                    files=chunk.files,
                    custom_instructions=custom_instructions,
                    total_files=total_files,
                )

                llm_result = adapter.chat_completion(
                    config=ai_config,
                    messages=[
                        {"role": "system", "content": prompt_result["system_prompt"]},
                        {"role": "user", "content": prompt_result["user_prompt"]},
                    ],
                )

                parsed = self._response_parser.parse(llm_result.content)
                all_parsed_issues.extend(parsed.issues)
                if parsed.summary:
                    all_summaries.append(parsed.summary)

            # Stage 7: Aggregate
            _progress(90, "Aggregating results...")
            aggregated = self._result_aggregator.aggregate(all_parsed_issues)
            combined_summary = " ".join(all_summaries) if all_summaries else "Review completed."

            # Stage 8: Return results
            _progress(100, "Review completed")
            return {
                "status": "completed",
                "summary": combined_summary,
                "issues": [
                    {
                        "file_path": issue.file_path,
                        "start_line": issue.start_line,
                        "end_line": issue.end_line,
                        "severity": issue.severity,
                        "dimension": issue.dimension,
                        "title": issue.title,
                        "description": issue.description,
                        "suggestion": issue.suggestion,
                        "code_snippet": issue.code_snippet,
                        "fix_snippet": issue.fix_snippet,
                        "confidence": issue.confidence,
                    }
                    for issue in aggregated.issues
                ],
                "stats": aggregated.stats,
            }

        except LLMCallError as e:
            logger.error("Review failed: %s", e)
            _progress(0, "Review failed")
            return {"status": "failed", "error_message": str(e), "issues": [], "summary": "", "stats": {"total": 0, "critical_count": 0, "high_count": 0, "medium_count": 0, "low_count": 0}}
        except Exception as e:
            logger.exception("Unexpected review error")
            _progress(0, "Review failed")
            return {"status": "failed", "error_message": str(e), "issues": [], "summary": "", "stats": {"total": 0, "critical_count": 0, "high_count": 0, "medium_count": 0, "low_count": 0}}
