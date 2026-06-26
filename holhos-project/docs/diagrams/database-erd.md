# Database ERD (backend)

```mermaid
erDiagram
    USERS {
        int id PK
        string full_name
        GenderEnum gender
        date birth_date
        EducationLevelEnum education_level
        string email UK
        string phone
        string password_hash
    }

    QUESTIONNAIRES {
        int id PK
        string title
        text description
        QuestionOrderEnum question_order
        boolean is_active
        datetime created_at
        int creator_id FK
    }

    QUESTIONNAIRE_ITEMS {
        int id PK
        int questionnaire_id FK
        ItemTypeEnum item_type
        int item_id "Polymorphic: questions.id OR instructions.id"
        int sort_order
    }

    QUESTIONS {
        int id PK
        string caption UK
        string title
        text text
        QuestionTypeEnum question_type
        boolean is_required
        float weight
        datetime created_at
    }

    QUESTION_OPTIONS {
        int id PK
        int question_id FK
        text text
        int sort_order
        boolean is_correct
        float weight
    }

    QUESTIONNAIRE_SUBMISSIONS {
        int id PK
        int questionnaire_id FK
        float total_score
        datetime submitted_at
    }

    ANSWERS {
        int id PK
        int submission_id FK
        int question_id FK
        json selected_options
        text text_response
        float score
    }

    INSTRUCTIONS {
        int id PK
        text text
        datetime created_at
    }

    %% --- FK relationships (enforced by DB constraints) ---
    USERS ||--o{ QUESTIONNAIRES : "creator_id"
    QUESTIONNAIRES ||--o{ QUESTIONNAIRE_ITEMS : "questionnaire_id"
    QUESTIONNAIRES ||--o{ QUESTIONNAIRE_SUBMISSIONS : "questionnaire_id"

    QUESTIONNAIRE_SUBMISSIONS ||--o{ ANSWERS : "submission_id"
    QUESTIONS ||--o{ ANSWERS : "question_id"

    QUESTIONS ||--o{ QUESTION_OPTIONS : "question_id"

    %% --- Logical relationships (polymorphic, not a real FK) ---
    QUESTIONNAIRE_ITEMS }o--|| QUESTIONS : "item_id (when item_type in {question, term})"
    QUESTIONNAIRE_ITEMS }o--|| INSTRUCTIONS : "item_id (when item_type = instruction)"
```

Notes:
- `questionnaire_items.item_id` is polymorphic (points to `questions.id` or `instructions.id` depending on `item_type`).
- Some `term` items are stored as `Question` rows in your current DB (based on existing data), even though the enum allows `instruction`.
