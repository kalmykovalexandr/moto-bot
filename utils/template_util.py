MAX_TITLE_LEN = 80

def generate_motor_description(**kwargs):
    with open("templates/motor_description.html", encoding="utf-8") as f:
        return f.read().format(**kwargs)

def generate_part_description(**kwargs):
    with open("templates/part_description.html", encoding="utf-8") as f:
        return f.read().format(**kwargs)

def generate_motor_title(brand, model, compatible_years):
    parts = ["Motore", brand, model]
    if compatible_years and compatible_years != "N/A":
        parts.append(compatible_years)
    parts.append("Usato Funzionante")
    title = _normalize_spaces(" ".join(parts))
    return _cut_to(title, MAX_TITLE_LEN)

def generate_part_title(part_type_for_title, brand, model, compatible_years):
    tail_parts = [brand, model]
    if compatible_years and compatible_years != "N/A":
        tail_parts.append(compatible_years)
    tail_parts.append("Usato Originale")
    tail = _normalize_spaces(" ".join(tail_parts))

    leftover = MAX_TITLE_LEN - len(tail) - 1
    leftover = max(10, leftover)

    head = _cut_to(part_type_for_title, leftover)
    return f"{head} {tail}"

def _normalize_spaces(s: str) -> str:
    return " ".join(str(s).split())

def _cut_to(s: str, n: int) -> str:
    s = _normalize_spaces(s)
    return s if len(s) <= n else s[:n].rstrip()