CHYPS_V_SUBSCALES = {
    "Brilho": {
        "label_en": "Brightness",
        "items": ["Q3", "Q7", "Q9", "Q14", "Q19"],
    },
    "Padrão": {
        "label_en": "Pattern",
        "items": ["Q1", "Q5", "Q12", "Q15", "Q20"],
    },
    "Estroboscópico": {
        "label_en": "Strobing",
        "items": ["Q2", "Q6", "Q10", "Q16", "Q18"],
    },
    "Ambiente Visual Intenso": {
        "label_en": "Intense Visual Environments",
        "items": ["Q4", "Q8", "Q11", "Q13", "Q17"],
    },
}

CHYPS_V_SCALE_ITEMS = [f"Q{i}" for i in range(1, 21)]

LIKERT_LABELS = {
    0: "Quase Nunca",
    1: "Ocasionalmente",
    2: "Frequentemente",
    3: "Quase Sempre",
}

LIKERT_WEIGHTS = {0, 1, 2, 3}

LIKERT_TEXT_TO_SCORE = {v.lower(): k for k, v in LIKERT_LABELS.items()}

GLOBAL_SCORE_RANGE = (0, 60)

DEMOGRAPHIC_FILTERS = {
    "diagnosis": {
        "label": "Diagnóstico prévio de transtorno",
        "pattern": "diagnóstico prévio",
        "type": "categorical",
    },
    "medication": {
        "label": "Faz uso de medicamento psiquiátrico?",
        "pattern": "uso de medicamento psiquiátrico",
        "type": "categorical",
    },
    "birth_year": {
        "label": "Ano de nascimento",
        "pattern": "data de nascimento",
        "type": "year",
    },
}

DEMOGRAPHIC_CAPTIONS = {
    "gender": "GENDER",
    "age": "AGE",
    "diagnosis": "DIAGNOSIS",
}
