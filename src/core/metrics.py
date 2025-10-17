"""
BasicMetrics: các chỉ số nền tảng tính trực tiếp trên prompt (không phụ thuộc model):
- MATTR-10 (Covington & McFall, 2010)
- LIX (Björnsson, 1983) + Reading Ease giả lập trên thang 0..100
- Token count (dựa trên tokenizer bạn truyền vào)

Giữ nguyên interface cũ để tương thích phần còn lại của app:
    metrics = BasicMetrics()
    rec = metrics.compute(prompt_text, tokenizer, run_id=run_id)
"""

import re
from typing import List
from dataclasses import dataclass

from src.core.tokenizer import Tokenizer

_SENT_SPLIT_RE = re.compile(r"[.!?…]+")


@dataclass
class PromptMetrics:
    run_id: str
    tokenizer: str
    window_w: int
    mattr: float
    token_count: int
    reading_ease: float
    reading_lix: float | None = None


class BasicMetrics:
    """
    Foundational metrics: token_count, MATTR (w=10), LIX (raw) + ease (compat 0..100).
    """

    def __init__(self):
        self.sentence_pattern = _SENT_SPLIT_RE
        self.word_pattern = re.compile(r"\b\w+\b", re.UNICODE)

    def _mattr(self, tokens: List[str], w: int = 10) -> float:
        """
        MATTR theo Covington & McFall (2010): moving-average type–token ratio.
        - Chỉ lấy token alphabetic để gần với cách đo ngôn ngữ tự nhiên.
        """
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
        """
        LIX = (từ/câu) + 100 * (từ dài>=7 / tổng từ).
        """
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
        """
        Ánh xạ tuyến tính sang thang 0..100 (giống bản cũ để tương thích UI).
        Không phải chuẩn gốc của LIX, chỉ để hiển thị trực quan.
        """
        reading_ease = 100 - (lix - 20) * (100 / 40)  # 20→100 (dễ), 60→0 (khó)
        return max(0.0, min(100.0, reading_ease))

    def compute(self, prompt_text: str, tokenizer: Tokenizer, run_id: str, w: int = 10) -> PromptMetrics:
        """
        Trả về PromptMetrics (dataclass) phục vụ ghi sheet 'metrics_deterministic'.
        """
        if not prompt_text.strip():
            return PromptMetrics(
                run_id=run_id,
                tokenizer=tokenizer.__class__.__name__,
                window_w=w,
                mattr=0.0,
                token_count=0,
                reading_ease=0.0,
                reading_lix=0.0,
            )

        tokens = tokenizer.tokenize(prompt_text)
        lix = self._lix_raw(prompt_text)

        return PromptMetrics(
            run_id=run_id,
            tokenizer=tokenizer.__class__.__name__,
            window_w=w,
            mattr=self._mattr(tokens, w),
            token_count=len(tokens),
            reading_ease=self._reading_ease_from_lix(lix),
            reading_lix=lix,
        )
