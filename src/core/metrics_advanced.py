import re
from typing import Dict, List

# ==============================================================================
# PHẦN 1: CÁC BỘ TỪ KHÓA ĐƠN GIẢN (CÓ THỂ MỞ RỘNG)
# ==============================================================================
# Nhóm 1: Các từ khóa yêu cầu tư duy bậc cao (Expanded)
COGNITIVE_KEYWORDS = {
    'analyze', 'compare', 'contrast', 'classify', 'organize', 'justify', 'evaluate',
    'critique', 'why is', 'how does', 'hypothesize', 'design', 'synthesize', 'differentiate',
    'deduce', 'infer', 'interpret', 'construct', 'devise', 'defend', 'validate',
    'what is the difference', 'explain the reason', 'argue for', 'argue against'
}

# Nhóm 2: Các thuật ngữ trừu tượng chính (Expanded for 7th Grade Math)
ABSTRACT_KEYWORDS = {
    'relationship', 'proportional', 'ratio', 'rate', 'probability', 'equation',
    'expression', 'variable', 'inequality', 'similarity', 'congruence', 'efficiency',
    'strategy', 'sample', 'population', 'integer', 'decimal', 'fraction', 'percentage',
    'circumference', 'diameter', 'radius', 'volume', 'surface area', 'mean', 'median',
    'mode', 'range', 'outcome', 'data set', 'distribution'
}

# Nhóm 3: Các từ khóa hỗ trợ, tạo cấu trúc (Expanded)
SCAFFOLDING_KEYWORDS = {
    'step-by-step', 'step 1', 'step 2', 'first', 'second', 'third', 'fourth', 'finally',
    'example', 'e.g.', 'for instance', 'let\'s say', 'given that', 'assuming',
    'hint', 'note', 'remember', 'formula', 'definition', 'recall', 'in conclusion'
}

# (Các bộ từ điển cũ vẫn được giữ lại để tương thích nếu cần)
COGNITIVE_VERBS = COGNITIVE_KEYWORDS.union({'explain', 'verify', 'predict', 'select', 'choose', 'formulate', 'decompose'})
ABSTRACT_TERMS = ABSTRACT_KEYWORDS.union({'proportionality', 'equivalence', 'variability', 'coefficient', 'hypothesis'})
METACOGNITIVE_VERBS = {"justify", "explain", "compare", "evaluate", "critique", "argue"}
STOPWORDS = {"the","a","an","and","or","of","to","in","on","for","with","by","from","this","that","these","those","is","are","was","were","be","as","at","it","you","your","i","we","they","he","she","their","our","his","her","them"}



# (Các bộ từ điển cũ vẫn được giữ lại để tương thích nếu cần)
COGNITIVE_VERBS = COGNITIVE_KEYWORDS.union({'explain', 'verify', 'validate', 'predict', 'select', 'choose', 'formulate', 'decompose'})
ABSTRACT_TERMS = ABSTRACT_KEYWORDS.union({'proportionality', 'equivalence', 'variability', 'distribution', 'coefficient', 'hypothesis'})
METACOGNITIVE_VERBS = {"justify", "explain", "compare", "evaluate", "critique", "argue"}
STOPWORDS = {"the","a","an","and","or","of","to","in","on","for","with","by","from","this","that","these","those","is","are","was","were","be","as","at","it","you","your","i","we","they","he","she","their","our","his","her","them"}


# ==============================================================================
# PHẦN 2: LOGIC CỐT LÕI MỚI - ĐẾM VÀ CHUẨN HÓA
# ==============================================================================

def _compute_normalized_rates(prompt_text: str) -> Dict:
    lower_prompt = prompt_text.lower()
    tokens = [w.lower() for w in re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ']+", prompt_text)]
    total_words = len(tokens)

    if total_words == 0:
        return {
            "cognitive_rate": 0.0,
            "abstract_rate": 0.0,
            "scaffolding_rate": 0.0,
            "total_words": 0
        }

    # Đếm số lượng từ khóa trong mỗi nhóm
    cognitive_count = sum(1 for keyword in COGNITIVE_KEYWORDS if keyword in lower_prompt)
    abstract_count = sum(1 for keyword in ABSTRACT_KEYWORDS if keyword in lower_prompt)
    scaffolding_count = sum(1 for keyword in SCAFFOLDING_KEYWORDS if keyword in lower_prompt)

    # Chuẩn hóa bằng cách chia cho tổng số từ
    return {
        "cognitive_rate": cognitive_count / total_words,
        "abstract_rate": abstract_count / total_words,
        "scaffolding_rate": scaffolding_count / total_words,
        "total_words": total_words
    }

# --- Các hàm helper cũ vẫn được giữ lại ---
def _lower_words(text: str) -> List[str]:
    return [w.lower() for w in re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ']+", text)]

def _numbers(text: str) -> List[str]:
    return re.findall(r"\b\d+(?:\.\d+)?\b", text)

def _lexical_density(tokens: List[str]) -> float:
    if not tokens: return 0.0
    content = [t for t in tokens if t not in STOPWORDS]
    return len(content) / len(tokens)

def _clauses_per_sentence(text: str) -> float:
    sents = [p.strip() for p in re.split(r"[.!?…]+", text) if p.strip()]
    if not sents: return 0.0
    clause_re = re.compile(r"(,|;|:|\bthat\b|\bwhich\b|\bbecause\b|\bif\b|\bwhen\b|\bwhile\b|\bwhereas\b|\balthough\b|\bsince\b)", re.IGNORECASE)
    counts = [1 + len(clause_re.findall(s)) for s in sents]
    return sum(counts) / len(sents)

def compute_cdi(prompt_text: str) -> Dict:
    """
    SỬA LẠI: Dùng logic đếm đơn giản, không trọng số.
    'cdi_composite' giờ là tổng của 2 tỷ lệ chính.
    """
    tokens = _lower_words(prompt_text)
    rates = _compute_normalized_rates(prompt_text)

    simple_composite = rates["cognitive_rate"] + rates["abstract_rate"]

    return {
        "rate_cognitive_verbs": rates["cognitive_rate"],  # Trả về cognitive_rate mới
        "lexical_density": _lexical_density(tokens),       # Vẫn giữ lại vì hữu ích
        "clauses_per_sentence": _clauses_per_sentence(prompt_text), # Vẫn giữ lại
        "rate_abstract_terms": rates["abstract_rate"],     # Trả về abstract_rate mới
        "cdi_composite": simple_composite                  # Điểm tổng hợp mới, đơn giản
    }

def compute_sss(prompt_text: str) -> Dict:
    """
    SỬA LẠI: Dùng logic đếm đơn giản.
    'sss_weighted' bị loại bỏ, thay bằng 'scaffolding_rate' rõ ràng.
    """
    rates = _compute_normalized_rates(prompt_text)

    n_examples = len(re.findall(r"\bexample\b|\be\.g\.\b|\bfor example\b", prompt_text, re.IGNORECASE))
    n_steps = len(re.findall(r"(?m)^\s*(?:\d+[\.\)]\s+|\-\s+|\*\s+|step\s*\d+)", prompt_text, re.IGNORECASE)) \
            + len(re.findall(r"\b(first|second|third|fourth|fifth)\b", prompt_text, re.IGNORECASE))
    n_formula = len(re.findall(r"[=^±%×÷+\-*/≤≥]", prompt_text)) + len(re.findall(r"\bpi\b|π", prompt_text, re.IGNORECASE))
    n_hints = len(re.findall(r"\bhint\b|\bremember\b|\bnote\b|\bdefinition\b|\brecall\b", prompt_text, re.IGNORECASE))


    return {
        "n_examples": n_examples,
        "n_step_markers": n_steps,
        "n_formula_markers": n_formula,
        "n_hints": n_hints,
        "scaffolding_rate": rates["scaffolding_rate"] 
    }

def compute_arq(prompt_text: str) -> Dict:
    """
    SỬA LẠI: Dùng logic đếm đơn giản.
    'arq_score' giờ là cognitive_rate.
    """
    tokens = _lower_words(prompt_text)
    rates = _compute_normalized_rates(prompt_text)

    meta_present = any(v in tokens for v in METACOGNITIVE_VERBS)

    # Hoàn toàn loại bỏ công thức ratio + bonus cũ
    return {
        # Vẫn trả về các key cũ để tương thích
        "abstract_terms": int(rates["abstract_rate"] * rates["total_words"]),
        "numbers": len(_numbers(prompt_text)),
        # Các key mới, rõ ràng hơn
        "meta_present": meta_present,
        "arq_score_simple": rates["cognitive_rate"] # Đây là chỉ số chính mới
    }

def compute_advanced_metrics(prompt_text: str) -> Dict:
    """
    Hàm này không cần thay đổi gì cả, vì các hàm con nó gọi
    vẫn giữ nguyên tên và cấu trúc trả về.
    """
    return {
        "cdi": compute_cdi(prompt_text),
        "sss": compute_sss(prompt_text),
        "arq": compute_arq(prompt_text),
    }