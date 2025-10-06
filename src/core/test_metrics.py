# -*- coding: utf-8 -*-
import re
from typing import Dict, List

# --- Lightweight lexicons (có thể mở rộng sau) ---
COGNITIVE_VERBS = {
    "analyze","compare","contrast","classify","organize","justify","evaluate","argue",
    "explain","hypothesize","design","decompose","critique","verify","validate","predict",
    "select","choose","synthesize","formulate"
}
ABSTRACT_TERMS = {
    "proportionality","equivalence","variability","probability","similarity","congruence",
    "distribution","relationship","rate","unit rate","ratio","coefficient","inequality",
    "expression","equation","sample","population","hypothesis","efficiency","strategy"
}
METACOGNITIVE_VERBS = {"justify","explain","compare","evaluate","critique","argue"}

STOPWORDS = {
    "the","a","an","and","or","of","to","in","on","for","with","by","from",
    "this","that","these","those","is","are","was","were","be","as","at","it",
    "you","your","i","we","they","he","she","their","our","his","her","them"
}

WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ']+")
NUM_RE  = re.compile(r"\b\d+(?:\.\d+)?\b")
SENT_SPLIT_RE = re.compile(r"[.!?…]+")

# câu phức: tách theo dấu phẩy/dấu chấm phẩy + liên từ phụ thuộc đơn giản
CLAUSE_BOUNDARY_RE = re.compile(
    r"(,|;|:|\bthat\b|\bwhich\b|\bbecause\b|\bif\b|\bwhen\b|\bwhile\b|\bwhereas\b|\balthough\b|\bsince\b)",
    re.IGNORECASE
)

def _lower_words(text: str) -> List[str]:
    return [w.lower() for w in WORD_RE.findall(text)]

def _numbers(text: str) -> List[str]:
    return NUM_RE.findall(text)

def _sentences(text: str) -> List[str]:
    parts = SENT_SPLIT_RE.split(text)
    return [p.strip() for p in parts if p.strip()]

def _lexical_density(tokens: List[str]) -> float:
    if not tokens:
        return 0.0
    content = [t for t in tokens if t not in STOPWORDS]
    return len(content) / len(tokens)

def _rate_in_lexicon(tokens: List[str], vocab: set) -> float:
    if not tokens:
        return 0.0
    cnt = sum(1 for t in tokens if t in vocab)
    return cnt / len(tokens)

def _clauses_per_sentence(text: str) -> float:
    sents = _sentences(text)
    if not sents:
        return 0.0
    counts = []
    for s in sents:
        # mỗi câu tối thiểu 1 mệnh đề
        n = 1 + len(CLAUSE_BOUNDARY_RE.findall(s))
        counts.append(n)
    return sum(counts) / len(counts)

def _count_step_markers(text: str) -> int:
    # dòng dạng "1. ", "2) ", "- ", "* ", hoặc "Step 1"
    pattern = re.compile(r"(?m)^\s*(?:\d+[\.\)]\s+|\-\s+|\*\s+|step\s*\d+)", re.IGNORECASE)
    m1 = len(pattern.findall(text))
    # từ thứ tự: First, Second, Third,...
    ords = len(re.findall(r"\b(first|second|third|fourth|fifth)\b", text, re.IGNORECASE))
    return m1 + ords

def _count_examples(text: str) -> int:
    return len(re.findall(r"\bexample\b|\be\.g\.\b|\bfor example\b", text, re.IGNORECASE))

def _count_formula_markers(text: str) -> int:
    # công thức: dấu toán học, "=","^","%", ký hiệu π, ≤, ≥
    return len(re.findall(r"[=^±%×÷+\-*/≤≥]", text)) + len(re.findall(r"\bpi\b|π", text, re.IGNORECASE))

def _count_hints(text: str) -> int:
    return len(re.findall(r"\bhint\b|\bremember\b|\bnote\b|\bdefinition\b|\brecall\b", text, re.IGNORECASE))

def compute_cdi(prompt_text: str) -> Dict:
    tokens = _lower_words(prompt_text)
    c_rate = _rate_in_lexicon(tokens, COGNITIVE_VERBS)          # tỉ lệ động từ nhận thức
    a_rate = _rate_in_lexicon(tokens, ABSTRACT_TERMS)           # tỉ lệ thuật ngữ trừu tượng
    ld     = _lexical_density(tokens)                           # mật độ từ nội dung
    cps    = _clauses_per_sentence(prompt_text)                 # mệnh đề / câu

    # composite không chuẩn hoá
    composite = 0.35 * c_rate + 0.30 * ld + 0.20 * cps + 0.15 * a_rate

    return {
        "rate_cognitive_verbs": c_rate,
        "lexical_density": ld,
        "clauses_per_sentence": cps,
        "rate_abstract_terms": a_rate,
        "cdi_composite": composite
    }

def compute_sss(prompt_text: str) -> Dict:
    n_examples = _count_examples(prompt_text)
    n_steps    = _count_step_markers(prompt_text)
    n_formula  = _count_formula_markers(prompt_text)
    n_hints    = _count_hints(prompt_text)

    sss_weighted = 3 * n_examples + 3 * n_steps + 2 * n_formula + 1 * n_hints

    return {
        "n_examples": n_examples,
        "n_step_markers": n_steps,
        "n_formula_markers": n_formula,
        "n_hints": n_hints,
        "sss_weighted": sss_weighted
    }

def compute_arq(prompt_text: str) -> Dict:
    tokens = _lower_words(prompt_text)
    abstract_cnt = sum(1 for t in tokens if t in ABSTRACT_TERMS)
    numbers_cnt  = len(_numbers(prompt_text))
    ratio        = abstract_cnt / (numbers_cnt + 1)

    meta_present = any(v in tokens for v in METACOGNITIVE_VERBS)
    meta_bonus   = 0.5 if meta_present else 0.0
    arq_score    = ratio + meta_bonus

    return {
        "abstract_terms": abstract_cnt,
        "numbers": numbers_cnt,
        "ratio": ratio,
        "meta_bonus": meta_bonus,
        "arq_score": arq_score
    }

def compute_advanced_metrics(prompt_text: str) -> Dict:
    return {
        "cdi": compute_cdi(prompt_text),
        "sss": compute_sss(prompt_text),
        "arq": compute_arq(prompt_text),
    }
