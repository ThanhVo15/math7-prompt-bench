import re, uuid

def clean_problem_text(t: str) -> str:
    t = (t or "").strip()
    if (t.startswith('"""') and t.endswith('"""')) or (t.startswith("'''") and t.endswith("'''")):
        t = t[3:-3].strip()
    if (t.startswith('"') and t.endswith('"')) or (t.startswith("'") and t.endswith("'")):
        t = t[1:-1].strip()
    return t

def normalize_for_id(t: str) -> str:
    t = clean_problem_text(t).lower()
    t = re.sub(r"\s+", " ", t).strip()
    return t

def generate_problem_id(problem_text: str) -> str:
    base = normalize_for_id(problem_text)
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"promptoptima:problem:{base}"))
