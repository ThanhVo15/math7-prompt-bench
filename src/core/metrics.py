import re
from typing import List, Dict
from datetime import datetime, timezone

from src.core.tokenizer import Tokenizer
from src.models.schemas import PromptMetrics

class BasicMetrics:
    """Foundational metrics: token_count, MATTR (w=10), LIX (raw) + ease (compat)."""

    def __init__(self):
        self.sentence_pattern = re.compile(r"[.!?…]+", re.UNICODE)
        self.word_pattern = re.compile(r"\b\w+\b", re.UNICODE)

    def _mattr(self, tokens: List[str], w: int = 10) -> float:
        base = [t.lower() for t in tokens if t.isalpha()]
        if not base:
            base = [t.lower() for t in tokens if t.strip()]
        n = len(base)
        if n == 0:
            return 0.0
        if n <= w:
            return len(set(base)) / n
        uniq_ratios = []
        for i in range(n - w + 1):
            window = base[i:i + w]
            uniq_ratios.append(len(set(window)) / w)
        return sum(uniq_ratios) / len(uniq_ratios) if uniq_ratios else 0.0

    def _lix_raw(self, text: str) -> float:
        if not text.strip():
            return 0.0
        sentences_list = self.sentence_pattern.split(text)
        sentences_list = [s for s in sentences_list if s.strip()]
        n_sentences = max(1, len(sentences_list))
        words = self.word_pattern.findall(text)
        n_words = max(1, len(words))
        long_words = sum(1 for w in words if len(w) >= 7)
        lix = (n_words / n_sentences) + 100 * (long_words / n_words)
        return float(lix)

    def _reading_ease_from_lix(self, lix: float) -> float:
        # Chuẩn hoá 0–100 (để tương thích cũ). Bạn có thể bỏ qua trong phân tích mới.
        reading_ease = 100 - (lix - 20) * (100 / 40)
        return max(0.0, min(100.0, reading_ease))

    def compute(self, prompt_text: str, tokenizer: Tokenizer, run_id: str, w: int = 10) -> PromptMetrics:
        if not prompt_text.strip():
            return PromptMetrics(
                run_id=run_id,
                tokenizer=tokenizer.__class__.__name__,
                window_w=w,
                mattr=0.0,
                token_count=0,
                reading_ease=0.0,
                reading_lix=0.0,   # NEW
            )

        tokens = tokenizer.tokenize(prompt_text)
        lix = self._lix_raw(prompt_text)

        return PromptMetrics(
            run_id=run_id,
            tokenizer=tokenizer.__class__.__name__,
            window_w=w,
            mattr=self._mattr(tokens, w),
            token_count=len(tokens),
            reading_ease=self._reading_ease_from_lix(lix),  # giữ cho tương thích
            reading_lix=lix,                                 # NEW: natural LIX
        )