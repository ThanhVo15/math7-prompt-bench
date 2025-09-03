import re
from typing import List, Dict, Optional
from datetime import datetime
from src.contracts.contracts import MetricsService, Tokenizer
from src.domain.entities import PromptMetrics

class BasicMetrics(MetricsService):
    """Tính toán MATTR và Reading Ease cho prompt theo chuẩn academic"""
    
    def __init__(self):
        # Precompile regex patterns for performance
        self.sentence_pattern = re.compile(r"[.!?…]+", re.UNICODE)
        self.word_pattern = re.compile(r"\w+", re.UNICODE)
    
    def _mattr(self, tokens: List[str], w: int = 25) -> float:
        """
        Moving Average Type-Token Ratio (Covington & McFall, 2010)
        Returns: 0.0-1.0 (higher = more lexical diversity)
        """
        n = len(tokens)
        if n == 0:
            return 0.0
        if n <= w:
            # Simple TTR for short texts
            return len(set(tokens)) / n
            
        # Sliding window MATTR for longer texts
        uniq_ratios = []
        freq = {}
        
        # Initialize first window
        for t in tokens[:w]:
            freq[t] = freq.get(t, 0) + 1
        uniq_ratios.append(len(freq) / w)
        
        # Slide window through remaining tokens
        for i in range(w, n):
            # Remove leftmost token
            left = tokens[i - w]
            freq[left] -= 1
            if freq[left] == 0:
                del freq[left]
            
            # Add rightmost token    
            right = tokens[i]
            freq[right] = freq.get(right, 0) + 1
            uniq_ratios.append(len(freq) / w)
            
        return sum(uniq_ratios) / len(uniq_ratios)
    
    def _reading_ease_lix(self, text: str) -> float:
        """
        LIX Readability Index (Björnsson, 1968)
        Returns: 0-100 (100 = easiest to read)
        """
        if not text.strip():
            return 0.0
            
        # Count sentences and words using precompiled patterns
        sentences = max(1, len(self.sentence_pattern.findall(text)))
        words = self.word_pattern.findall(text)
        n_words = max(1, len(words))
        
        # Count long words (≥7 characters - European standard)
        long_words = sum(1 for w in words if len(w) >= 7)
        
        # LIX formula: average sentence length + percentage of long words
        lix = (n_words / sentences) + 100 * (long_words / n_words)
        
        # Normalize LIX (20-60) to Reading Ease scale (100-0)
        # LIX 20 = very easy → RE 100
        # LIX 60 = very hard → RE 0
        reading_ease = 100 - (lix - 20) * (100 / 40)
        return max(0.0, min(100.0, reading_ease))
    
    def _get_text_stats(self, text: str) -> Dict[str, int]:
        """Helper method to get basic text statistics"""
        sentences = len(self.sentence_pattern.findall(text))
        words = self.word_pattern.findall(text)
        long_words = sum(1 for w in words if len(w) >= 7)
        
        return {
            "sentences": max(1, sentences),
            "words": max(1, len(words)),
            "long_words": long_words,
            "avg_word_length": sum(len(w) for w in words) / max(1, len(words))
        }
    
    def compute(self, prompt_text: str, tokenizer: Tokenizer, w: int = 25) -> PromptMetrics:
        """
        Compute all metrics for a prompt text
        
        Args:
            prompt_text: The text to analyze
            tokenizer: Tokenizer implementation to use
            w: Window size for MATTR calculation (default: 25)
        
        Returns:
            PromptMetrics object with all computed values
        """
        if not prompt_text.strip():
            # Return empty metrics for empty text
            return PromptMetrics(
                prompt_id="empty",
                tokenizer=tokenizer.__class__.__name__,
                window_w=w,
                mattr=0.0,
                token_count=0,
                reading_ease=0.0,
                computed_at=datetime.utcnow()
            )
        
        # Tokenize once and reuse
        tokens = tokenizer.tokenize(prompt_text)
        
        return PromptMetrics(
            prompt_id="template",  # Will be set when saving
            tokenizer=tokenizer.__class__.__name__,
            window_w=w,
            mattr=self._mattr(tokens, w),
            token_count=len(tokens),  # Use tokenized length for consistency
            reading_ease=self._reading_ease_lix(prompt_text),
            computed_at=datetime.utcnow()
        )
    
    def compute_detailed(self, prompt_text: str, tokenizer: Tokenizer, w: int = 25) -> Dict:
        """
        Compute metrics with additional details for debugging/analysis
        """
        basic_metrics = self.compute(prompt_text, tokenizer, w)
        text_stats = self._get_text_stats(prompt_text)
        tokens = tokenizer.tokenize(prompt_text)
        
        return {
            "metrics": basic_metrics,
            "text_stats": text_stats,
            "token_preview": tokens[:10],  # First 10 tokens for inspection
            "unique_tokens": len(set(tokens)),
            "vocabulary_richness": len(set(tokens)) / max(1, len(tokens))
        }