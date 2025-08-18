def generate_motor_description(**kwargs):
    with open("templates/motor_description.html", encoding="utf-8") as f:
        return f.read().format(**kwargs)

def generate_part_description(**kwargs):
    with open("templates/part_description.html", encoding="utf-8") as f:
        return f.read().format(**kwargs)

def generate_motor_title(brand, model, compatible_years):
    return f"Motore {brand} {model} {compatible_years} Usato Funzionante"

def generate_part_title(part_type, brand, model, compatible_years):
    return f"{part_type} {brand} {model} {compatible_years} Usato Originale"