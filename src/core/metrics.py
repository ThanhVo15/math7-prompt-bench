# src/core/metrics_advanced.py

from __future__ import annotations
import re
import math
from typing import Dict, List, Tuple, Optional, Set

# ---------------- Lexicons (V2.1 – Expanded and Cleaned) ----------------
COGNITIVE_VERBS: Set[str] = {
    # Analyze / Understand / Apply
    "analyze", "analyze why", "analyze how", "break down", "diagnose",
    "classify", "categorize", "organize", "structure", "outline", "summarize", "synthesize",
    "explain", "explain why", "explain how", "illustrate", "demonstrate", "show that",
    "derive", "compute", "calculate", "solve", "determine", "evaluate", "estimate", "approximate",
    "simplify", "expand", "factor", "generalize", "specialize", "transform", "translate",
    "apply", "use", "implement", "simulate", "model", "design", "plan",
    # Compare / Critique / Argue
    "compare", "contrast", "differentiate", "distinguish", "relate", "map", "align",
    "justify", "defend", "argue", "debate", "critique", "assess", "appraise", "review",
    "validate", "verify", "check", "confirm", "prove", "disprove", "falsify", "refute",
    "predict", "hypothesize", "conjecture", "infer", "deduce", "induce",
    # Strategy & meta-actions
    "choose", "select", "prioritize", "optimize", "trade off", "reason", "reason about",
    "formulate", "reformulate", "compose", "decompose", "reconstruct", "reframe",
    "propose", "suggest", "identify", "pinpoint", "provide",
}

ABSTRACT_TERMS: Set[str] = {
    # General math/abstract
    "abstraction", "structure", "pattern", "rule", "property", "invariant", "constraint",
    "variable", "parameter", "constant", "function", "mapping", "relation", "set", "subset",
    "domain", "range", "input", "output", "model", "system", "theoretical", "assumption", "axiom",
    # Arithmetic/number
    "integer", "whole number", "natural number", "rational", "irrational", "real number",
    "prime", "composite", "factor", "multiple", "divisor", "gcd", "lcm", "remainder",
    "ratio", "unit rate", "rate", "proportion", "proportionality", "percentage", "percent",
    "fraction", "numerator", "denominator", "decimal", "place value",
    # Expressions & equations (EE)
    "term", "expression", "equation", "identity", "inequality", "formula", "coefficient",
    "variable term", "constant term", "like terms", "distribution", "distributive property",
    "commutative property", "associative property", "linear", "nonlinear", "quadratic",
    "polynomial", "exponent", "power", "base", "evaluate expression", "substitution",
    "solution set", "equivalent", "system of equations", "elimination", "substitution method",
    "graphical solution", "factorization",
    # Geometry (G)
    "point", "line", "ray", "segment", "angle", "right angle", "acute angle", "obtuse angle",
    "parallel", "perpendicular", "intersect", "triangle", "isosceles", "scalene", "equilateral",
    "quadrilateral", "rectangle", "square", "rhombus", "parallelogram", "trapezoid",
    "polygon", "circle", "arc", "chord", "tangent", "secant", "radius", "diameter", "circumference",
    "area", "perimeter", "surface area", "volume", "prism", "pyramid", "cylinder", "cone", "sphere",
    "similarity", "congruence", "scale factor", "dilation", "rotation", "reflection", "translation",
    # Ratios & Proportional Relationships (RP)
    "unit price", "constant of proportionality", "direct variation",
    "proportional relationship", "table of values", "double number line",
    # Coordinate / functions
    "coordinate plane", "axis", "x-axis", "y-axis", "origin", "ordered pair", "slope",
    "intercept", "slope-intercept form", "graph", "curve", "table", "sequence",
    "arithmetic sequence", "geometric sequence", "nth term", "recurrence",
    # Statistics & Probability (SP)
    "data set", "distribution", "sample", "population", "bias", "random", "experiment", "trial",
    "event", "outcome", "likelihood", "odds", "probability", "theoretical probability",
    "experimental probability", "independent events", "dependent events", "conditional probability",
    "relative frequency", "mean", "median", "mode", "range", "quartile", "interquartile range",
    "percentile", "variance", "standard deviation", "box plot", "histogram", "dot plot", "bar chart",
    "scatter plot", "correlation", "trend line", "regression", "residual",
    # Reasoning & new terms from analysis
    "equivalence", "implication", "contradiction", "counterexample", "generalization", "edge case",
    "efficiency", "strategy", "tradeoff", "optimal", "feasible", "constraint satisfaction",
    "reasoning", "approach", "method", "solution", "scenario", "concept", "principle",
    "applicability", "validity", "strengths", "weaknesses", "errors", "misunderstanding", "improvement",
}

METACOGNITIVE_VERBS: Set[str] = {
    "justify", "explain", "compare", "evaluate", "critique", "argue", "reflect", "assess",
    "self-check", "check your work", "verify reasoning", "validate reasoning",
    "explain reasoning", "explain decision", "explain choice", "explain steps",
    "review", "revise", "debug", "analyze error", "error analysis", "sanity check", "self-assess",
}

LOGIC_CONNECTORS: Set[str] = {
    "if", "then", "if and only if", "iff", "therefore", "hence", "thus", "so", "because", "since",
    "as a result", "consequently", "accordingly", "it follows that", "implies",
    "this implies", "we conclude", "we can conclude", "by contradiction", "by induction",
    "suppose", "assume", "given", "given that", "provided that", "unless", "otherwise", "in that case",
    "consider", "let", "let x be", "let n be", "for any", "for all", "there exists",
    "either", "or", "neither", "nor", "both", "case", "case 1", "case 2", "case analysis",
    "approximately", "about", "roughly", "at least", "at most", "no more than", "no less than",
    "however", "nevertheless", "nonetheless", "on the other hand", "in contrast", "meanwhile",
}

MODALS: Set[str] = {
    "can", "cannot", "can not", "could", "could not", "might", "may", "must", "must not",
    "should", "should not", "would", "would not", "will", "will not", "shall", "ought to",
    "likely", "unlikely", "possibly", "probably", "certainly", "surely",
}

STOPWORDS: Set[str] = {
    "a", "an", "the", "and", "but", "or", "nor", "so", "for", "yet", "about", "above", "after",
    "again", "against", "all", "am", "any", "are", "aren't", "as", "at", "be", "because",
    "been", "before", "being", "below", "between", "both", "by", "could", "couldn't", "did",
    "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during", "each", "few",
    "from", "further", "had", "hadn't", "has", "hasn't", "have", "haven't", "having", "he",
    "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself", "him", "himself",
    "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is",
    "isn't", "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my",
    "myself", "no", "not", "of", "off", "on", "once", "only", "other", "ought", "our",
    "ours", "ourselves", "out", "over", "own", "same", "she", "she'd", "she'll", "she's",
    "should", "shouldn't", "some", "such", "than", "that", "that's", "their", "theirs",
    "them", "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll",
    "they're", "they've", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't",
    "what", "what's", "when", "when's", "where", "where's", "which", "while", "who", "who's",
    "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll",
    "you're", "you've", "your", "yours", "yourself", "yourselves",
}

# --- Regex Patterns ---
WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ']+")
NUM_RE  = re.compile(r"\b\d+(?:\.\d+)?\b")
SENT_SPLIT_RE = re.compile(r"[.!?…]+")
CLAUSE_BOUNDARY_RE = re.compile(
    r"(,|;|:|\bthat\b|\bwhich\b|\bbecause\b|\bif\b|\bwhen\b|\bwhile\b|\bwhereas\b|\balthough\b|\bsince\b)",
    re.IGNORECASE
)
FORMULA_BASE = r"[=^±%×÷+*/≤≥]"
HYPHEN_BETWEEN = r"(?:(?<=\w)-(?=\w)|(?<=\d)-(?=\d))"
FORMULA_MARK_RE = re.compile(fr"(?:{FORMULA_BASE}|{HYPHEN_BETWEEN}|\bpi\b|π)", re.IGNORECASE)
EXAMPLE_RE = re.compile(r"\bexample\b|\be\.g\.\b|\bfor example\b", re.IGNORECASE)
HINT_RE = re.compile(r"\bhint\b|\bremember\b|\bnote\b|\bdefinition\b|\brecall\b", re.IGNORECASE)
STEP_LINE_RE = re.compile(r"(?m)^\s*(?:\d+[\.\)]\s+|\-\s+|\*\s+|step\s*\d+)", re.IGNORECASE)
STEP_INLINE_RE = re.compile(r"\b(first|second|third|fourth|fifth)\b", re.IGNORECASE)
STEP_PHRASE_RE = re.compile(r"\bstep[-\s]?by[-\s]?step\b", re.IGNORECASE)
SECTION_HEADER_RE = re.compile(r"(?m)^\s*(?:part|section|thread|student|approach)\s*[A-Z\d]+[:\.\)]", re.IGNORECASE)


# ---------------- Helpers ----------------
def _words(text: str) -> List[str]:
    return [w.lower() for w in WORD_RE.findall(text)]

def _numbers(text: str) -> List[str]:
    return NUM_RE.findall(text)

def _lexical_density(tokens: List[str]) -> float:
    if not tokens: return 0.0
    content_words = [t for t in tokens if t not in STOPWORDS]
    return len(content_words) / len(tokens) if tokens else 0.0

def _clauses_per_sentence(text: str) -> float:
    sents = [s.strip() for s in SENT_SPLIT_RE.split(text) if s.strip()]
    if not sents: return 0.0
    clause_counts = [1 + len(CLAUSE_BOUNDARY_RE.findall(s)) for s in sents]
    return sum(clause_counts) / len(sents)

def _count_terms_and_hits(text_lower: str, terms: Set[str]) -> Tuple[int, List[str]]:
    cnt = 0
    hits: List[str] = []
    for term in terms:
        if " " in term:
            k = text_lower.count(term)
            if k > 0:
                cnt += k
                hits.extend([term] * k)
        else:
            found = re.findall(rf"\b{re.escape(term)}\b", text_lower)
            if found:
                cnt += len(found)
                hits.extend(found)
    return cnt, hits

def _findall_hits(pattern: re.Pattern, text: str) -> List[str]:
    return [m.group(0) for m in pattern.finditer(text)]


# ---------------- CDI: Cognitive Demand Index (Hybrid) ----------------
def compute_cdi(prompt_text: str, ai_pattern_hits: Optional[Dict] = None) -> Dict:
    text = prompt_text or ""
    text_lower = text.lower()
    
    # --- Làm giàu văn bản với các từ khóa từ AI ---
    enriched_text = text_lower
    if ai_pattern_hits:
        ai_cognitive = ai_pattern_hits.get("cognitive_terms_ai", [])
        ai_abstract = ai_pattern_hits.get("abstract_terms_ai", [])
        # Nối các từ AI tìm thấy vào văn bản để đếm
        enriched_text += " " + " ".join(ai_cognitive) + " " + " ".join(ai_abstract)

    # Tính toán trên văn bản đã được làm giàu
    tokens = _words(enriched_text)
    n_tokens = max(1, len(tokens))

    c_terms_count, c_hits = _count_terms_and_hits(enriched_text, COGNITIVE_VERBS)
    a_terms_count, a_hits = _count_terms_and_hits(enriched_text, ABSTRACT_TERMS)

    # Các chỉ số khác vẫn tính trên văn bản gốc để giữ tính khách quan
    original_tokens = _words(text_lower)
    ld = _lexical_density(original_tokens)
    cps = _clauses_per_sentence(text)
    
    c_rate = c_terms_count / n_tokens
    a_rate = a_terms_count / n_tokens

    cdi_composite = math.sqrt(c_rate * a_rate) if c_rate > 0 and a_rate > 0 else 0.0

    return {
        "rate_cognitive_verbs": c_rate,
        "lexical_density": ld,
        "clauses_per_sentence": cps,
        "rate_abstract_terms": a_rate,
        "cdi_composite": cdi_composite,
        "hits": {"cognitive_terms": c_hits, "abstract_terms": a_hits},
    }


# ---------------- SSS: Structured Scaffolding Score (Rule-based) ----------------
def compute_sss(prompt_text: str) -> Dict:
    text = prompt_text or ""
    section_hits = _findall_hits(SECTION_HEADER_RE, text)
    ex_hits = _findall_hits(EXAMPLE_RE, text)
    step_hits = (
        _findall_hits(STEP_LINE_RE, text)
        + _findall_hits(STEP_INLINE_RE, text)
        + _findall_hits(STEP_PHRASE_RE, text)
        + section_hits
    )
    formula_hits = _findall_hits(FORMULA_MARK_RE, text)
    hint_hits = _findall_hits(HINT_RE, text)

    E, S, F, H = len(ex_hits), len(step_hits), len(formula_hits), len(hint_hits)
    sss_raw = E + S + F + H
    sss_log_weighted = math.log1p(E) + math.log1p(S) + math.log1p(F) + math.log1p(H)

    return {
        "n_examples": E, "n_step_markers": S, "n_formula_markers": F, "n_hints": H,
        "sss_weighted": sss_log_weighted, "sss_raw": sss_raw,
        "hits": {"examples": ex_hits, "step_markers": step_hits, "formula_markers": formula_hits, "hints": hint_hits},
    }


# ---------------- ARQ: Abstract Reasoning Quotient (Hybrid) ----------------
def compute_arq(prompt_text: str, ai_pattern_hits: Optional[Dict] = None) -> Dict:
    text = prompt_text or ""
    text_lower = text.lower()

    # --- Làm giàu văn bản với các từ khóa từ AI ---
    enriched_text = text_lower
    if ai_pattern_hits:
        ai_abstract = ai_pattern_hits.get("abstract_terms_ai", [])
        ai_meta = ai_pattern_hits.get("meta_terms_ai", [])
        # Gộp cả cognitive vào vì AI có thể phân loại nhầm "reasoning" vào đây
        ai_cognitive = ai_pattern_hits.get("cognitive_terms_ai", [])
        enriched_text += " " + " ".join(ai_abstract) + " " + " ".join(ai_meta) + " ".join(ai_cognitive)

    # Đếm lại thuật ngữ trên văn bản đã làm giàu
    a_terms_count, a_hits = _count_terms_and_hits(enriched_text, ABSTRACT_TERMS)
    meta_terms_count, meta_hits = _count_terms_and_hits(enriched_text, METACOGNITIVE_VERBS)

    # Các yếu tố khác vẫn đếm trên văn bản gốc
    numbers = _findall_hits(NUM_RE, text)
    formula_hits = _findall_hits(FORMULA_MARK_RE, text)
    logic_conn_count, logic_conn_hits = _count_terms_and_hits(text_lower, LOGIC_CONNECTORS)
    modal_count, modal_hits = _count_terms_and_hits(text_lower, MODALS)

    # Tính toán cuối cùng
    denom = len(numbers) + len(formula_hits) + 1
    ratio = a_terms_count / denom
    meta_gate_open = (meta_terms_count >= 1) or ((logic_conn_count + modal_count) >= 2)
    arq_score = ratio if meta_gate_open else 0.0
    meta_bonus = 1.0 if meta_gate_open else 0.0

    return {
        "abstract_terms": a_terms_count, "numbers": len(numbers), "ratio": ratio,
        "meta_bonus": meta_bonus, "arq_score": arq_score,
        "hits": {
            "abstract_terms": a_hits, "numbers": numbers, "formula_markers": formula_hits,
            "metacognitive": meta_hits, "logic_connectors": logic_conn_hits,
            "modals": modal_hits, "meta_gate": meta_gate_open,
        },
    }


# ---------------- Orchestrator (Hybrid) ----------------
def compute_advanced_metrics(prompt_text: str, ai_pattern_hits: Optional[Dict] = None) -> Dict:
    """
    Hàm điều phối chính, tính toán tất cả các chỉ số nâng cao.
    Nó sẽ truyền các pattern do AI phát hiện vào các hàm tính CDI và ARQ.
    """
    cdi = compute_cdi(prompt_text, ai_pattern_hits=ai_pattern_hits)
    # SSS vẫn dựa trên rule-based vì regex đã rất mạnh cho việc nhận diện cấu trúc.
    sss = compute_sss(prompt_text)
    arq = compute_arq(prompt_text, ai_pattern_hits=ai_pattern_hits)

    hits = {
        "c_terms": cdi["hits"]["cognitive_terms"],
        "a_terms": cdi["hits"]["abstract_terms"],
        "examples": sss["hits"]["examples"],
        "step_markers": sss["hits"]["step_markers"],
        "formula_marks": sss["hits"]["formula_markers"],
        "hints": sss["hits"]["hints"],
        "numbers": arq["hits"]["numbers"],
        "meta_terms": arq["hits"]["metacognitive"],
        "logic_connectors": arq["hits"]["logic_connectors"],
        "modals": arq["hits"]["modals"],
    }
    
    return {"cdi": cdi, "sss": sss, "arq": arq, "hits": hits}