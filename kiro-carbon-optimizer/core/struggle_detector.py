"""Detects AI struggle signals from prompt history, file request frequency, and edit patterns."""
import hashlib
import math
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List

from core.models import StruggleSignal, MCPSuggestion
from core.diff_tracker import DiffTracker
from core.mcp_suggester import MCPSuggester


class StruggleDetector:
    SIMILARITY_THRESHOLD = 0.80
    HIGH_FREQUENCY_THRESHOLD = 7
    HIGH_FREQUENCY_WINDOW_MINUTES = 10
    TOKEN_ESTIMATE_THRESHOLD = 1500
    REPEATED_CONTENT_THRESHOLD = 2
    REJECTION_THRESHOLD = 3

    def __init__(self):
        self._prompt_history: List[str] = []
        self._file_request_log: dict = defaultdict(list)  # file_path -> [datetime]
        self._content_hashes: dict = defaultdict(int)     # hash -> count
        self._rejection_counters: dict = defaultdict(int) # file_path -> count
        self._diff_tracker = DiffTracker()
        self._mcp_suggester = MCPSuggester()

    def on_prompt_submitted(self, prompt: str, file_refs: List[str]) -> List[StruggleSignal]:
        """Process a submitted prompt and return any triggered struggle signals."""
        signals = []
        self._prompt_history.append(prompt)

        # Signal 1: Repeated prompts (cosine similarity >= 0.80)
        if len(self._prompt_history) >= 2:
            similarity_signal = self._check_prompt_similarity(prompt)
            if similarity_signal:
                signals.append(similarity_signal)

        # Signal 2: High-frequency file requests
        now = datetime.now()
        for file_path in file_refs:
            self._file_request_log[file_path].append(now)
            freq_signal = self._check_file_frequency(file_path, now)
            if freq_signal:
                signals.append(freq_signal)

        # Signal 3: Oversized prompt
        token_estimate = math.ceil(len(prompt) / 4)
        if token_estimate > self.TOKEN_ESTIMATE_THRESHOLD:
            signals.append(StruggleSignal(
                signal_type="oversized_prompt",
                severity="medium",
                message=(
                    f"Prompt is very long (~{token_estimate} tokens). "
                    "Consider splitting the request or referencing files by path instead of pasting content."
                ),
                mcp_suggestion=None,
            ))

        # Signal 4: Repeated content pasting
        content_hash = hashlib.md5(prompt.encode()).hexdigest()
        self._content_hashes[content_hash] += 1
        if self._content_hashes[content_hash] >= self.REPEATED_CONTENT_THRESHOLD:
            signals.append(StruggleSignal(
                signal_type="repeated_content_pasting",
                severity="medium",
                message=(
                    "The same content has been pasted in multiple prompts. "
                    "Consider referencing the file by path instead."
                ),
                mcp_suggestion=None,
            ))

        # Attach MCP suggestions to signals that don't have one
        for signal in signals:
            if signal.mcp_suggestion is None:
                signal.mcp_suggestion = self._mcp_suggester.suggest(signal.signal_type)

        return signals

    def on_edit_generated(self, file_path: str, line_range: tuple) -> List[StruggleSignal]:
        """Record an AI-generated edit and return any triggered signals."""
        self._diff_tracker.record_edit(file_path, line_range)
        signals = []
        if self._diff_tracker.check_repeated_region(file_path, line_range):
            signal = StruggleSignal(
                signal_type="repeated_file_edits",
                severity="medium",
                message=(
                    "Repeated edits detected in the same code region. "
                    "The AI may lack context."
                ),
                mcp_suggestion=self._mcp_suggester.suggest("repeated_file_edits"),
            )
            signals.append(signal)
        return signals

    def on_edit_reverted(self, file_path: str) -> List[StruggleSignal]:
        """Record a revert event and return any triggered signals."""
        self._rejection_counters[file_path] += 1
        signals = []
        if self._rejection_counters[file_path] >= self.REJECTION_THRESHOLD:
            signal = StruggleSignal(
                signal_type="repeated_rejections",
                severity="high",
                message=(
                    f"Generated code for '{file_path}' has been rejected "
                    f"{self._rejection_counters[file_path]} times. "
                    "The AI may be missing important context."
                ),
                mcp_suggestion=self._mcp_suggester.suggest("repeated_file_edits"),
            )
            signals.append(signal)
        return signals

    def _check_prompt_similarity(self, new_prompt: str) -> StruggleSignal | None:
        """Check TF-IDF cosine similarity against prompt history."""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity

            # Compare new prompt against all previous prompts (excluding itself)
            previous = self._prompt_history[:-1]
            if not previous:
                return None

            vectorizer = TfidfVectorizer()
            all_prompts = previous + [new_prompt]
            tfidf_matrix = vectorizer.fit_transform(all_prompts)
            new_vec = tfidf_matrix[-1]
            prev_matrix = tfidf_matrix[:-1]
            similarities = cosine_similarity(new_vec, prev_matrix)[0]

            if any(sim >= self.SIMILARITY_THRESHOLD for sim in similarities):
                return StruggleSignal(
                    signal_type="repeated_prompt_loop",
                    severity="medium",
                    message=(
                        "You may be in an AI retry loop. "
                        "Consider adding structured context or using a relevant MCP server."
                    ),
                    mcp_suggestion=None,
                )
        except Exception:
            # sklearn not available or other error — skip silently
            pass
        return None

    def _check_file_frequency(self, file_path: str, now: datetime) -> StruggleSignal | None:
        """Check if file has been referenced >= 7 times in the last 10 minutes."""
        window_start = now - timedelta(minutes=self.HIGH_FREQUENCY_WINDOW_MINUTES)
        recent = [t for t in self._file_request_log[file_path] if t >= window_start]
        if len(recent) >= self.HIGH_FREQUENCY_THRESHOLD:
            return StruggleSignal(
                signal_type="high_frequency_retry",
                severity="medium",
                message=(
                    "You may be in an AI retry loop. "
                    "Consider adding structured context or using a relevant MCP server."
                ),
                mcp_suggestion=None,
            )
        return None
