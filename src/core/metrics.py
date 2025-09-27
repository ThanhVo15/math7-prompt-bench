import re
from typing import List, Dict
from datetime import datetime, timezone

from src.core.tokenizer import Tokenizer
from src.models.schemas import PromptMetrics

class BasicMetrics:
    """Tính toán MATTR và Reading Ease cho prompt"""

    def __init__(self):
        self.sentence_pattern = re.compile(r"[.!?…]+", re.UNICODE)
        self.word_pattern = re.compile(r"\b\w+\b", re.UNICODE)

    def _mattr(self, tokens: List[str], w: int = 10) -> float:
        """Moving Average Type-Token Ratio (window_size=10), tính trên từ (letters-only)."""
        # Lọc chỉ giữ token là chữ (Unicode), bỏ số, dấu câu, ký hiệu
        base = [t.lower() for t in tokens if t.isalpha()]
        if not base:  # fallback: nếu không có từ, dùng tất cả token không rỗng
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

    def _reading_ease_lix(self, text: str) -> float:
        """LIX Readability Index, chuẩn hoá 0–100 (cao = dễ đọc)"""
        if not text.strip():
            return 0.0

        sentences_list = self.sentence_pattern.split(text)
        sentences_list = [s for s in sentences_list if s.strip()]
        n_sentences = max(1, len(sentences_list))

        words = self.word_pattern.findall(text)
        n_words = max(1, len(words))
        long_words = sum(1 for w in words if len(w) >= 7)

        lix = (n_words / n_sentences) + 100 * (long_words / n_words)
        reading_ease = 100 - (lix - 20) * (100 / 40)
        return max(0.0, min(100.0, reading_ease))

    def compute(self, prompt_text: str, tokenizer: Tokenizer, run_id: str, w: int = 10) -> PromptMetrics:
        """Compute all metrics and return a Pydantic object"""
        if not prompt_text.strip():
            return PromptMetrics(
                run_id=run_id,
                tokenizer=tokenizer.__class__.__name__,
                window_w=w,
                mattr=0.0,
                token_count=0,
                reading_ease=0.0
            )

        tokens = tokenizer.tokenize(prompt_text)

        return PromptMetrics(
            run_id=run_id,
            tokenizer=tokenizer.__class__.__name__,
            window_w=w,                           # ✅ align window=10 với Analyzer
            mattr=self._mattr(tokens, w),         # ✅ giá trị 0–1 (chuẩn MATTR)
            token_count=len(tokens),              # lưu ý: không phải LLM tokens
            reading_ease=self._reading_ease_lix(prompt_text),  # 0–100
        )
