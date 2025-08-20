MAX_TITLE_LEN = 80

MOTOR_DESCRIPTION_TMPL = """\
Motore {brand} {model} {compatible_years}
• Tipo: {engine_type}
• Cilindrata: {displacement}
• Alesaggio/Corsa: {bore_stroke}
• Rapporto di compressione: {compression_ratio}
• Potenza max: {max_power}
• Coppia max: {max_torque}
• Raffreddamento: {cooling}
• Alimentazione: {fuel_system}
• Avviamento: {starter}
• Cambio: {gearbox}
• Trasmissione finale: {final_drive}
• Olio consigliato: {recommended_oil}
• Capacità olio: {oil_capacity}
• Colore: {color}
• Anno: {year}
Compatibilità: {compatible_years}
MPN: {mpn}
"""

PART_DESCRIPTION_TMPL = """\
Ricambio {part_type} per {brand} {model} ({year})
• Colore: {color}
• Compatibilità: {compatible_years}
• MPN: {mpn}
Articolo usato originale, testato e funzionante salvo diversa indicazione. Segni d'uso come da foto.
"""

def _normalize_spaces(s: str) -> str:
    return " ".join(str(s).split())

def _cut_to(s: str, n: int) -> str:
    s = _normalize_spaces(s)
    return s if len(s) <= n else s[:n].rstrip()

def generate_motor_description(**kw) -> str: return MOTOR_DESCRIPTION_TMPL.format(**kw)
def generate_part_description(**kw) -> str:  return PART_DESCRIPTION_TMPL.format(**kw)

def generate_motor_title(brand: str, model: str, compatible_years: str | None):
    parts = ["Motore", brand, model]
    if compatible_years and compatible_years != "N/A":
        parts.append(compatible_years)
    parts.append("Usato Funzionante")
    return _cut_to(_normalize_spaces(" ".join(parts)), MAX_TITLE_LEN)

def generate_part_title(part_type_for_title: str, brand: str, model: str, compatible_years: str | None):
    tail_parts = [brand, model]
    if compatible_years and compatible_years != "N/A":
        tail_parts.append(compatible_years)
    tail_parts.append("Usato Originale")
    tail = _normalize_spaces(" ".join(tail_parts))
    leftover = max(10, MAX_TITLE_LEN - len(tail) - 1)
    head = _cut_to(part_type_for_title, leftover)
    return f"{head} {tail}"