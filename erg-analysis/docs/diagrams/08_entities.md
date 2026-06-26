# Entidades (ERD)

```mermaid
erDiagram
    PATIENTS {
        string patient_unique_id PK
        string patient_id_raw
        string patient_birthdate
        string testing_date
    }

    PATIENTS_ID_MAPPING {
        string patient_unique_id PK
        string id_prontuario
        string nome_paciente
        string data_nascimento
        string data_coleta
        string sexo
    }

    METADATA {
        string patient_unique_id FK
        string test_id
        string waveform_type
        string TestType
        string TestStepType
        string TestedEye
        string source_file
    }

    WAVEFORMS {
        string patient_unique_id FK
        string test_id
        string waveform_type
        string waveform_description
        float time_ms
        float voltage_uV
        float pupil_mm
        string source_file
    }

    WAVEFORM_TYPES {
        string waveform_type PK
    }

    PATIENT_FEATURES {
        string patient_unique_id PK
        string TestedEye
        string TestStepType
        float AWaveTime
        float AWaveAmplitude
        float BWaveTime
        float BWaveAmplitude
        float WaveformAmplitude
    }

    SPECTRAL_FEATURES {
        string patient_unique_id
        string test_id
        int waveform_type_id
        float fft_*
        float welch_*
        float dwt_*
    }

    QUESTIONNAIRE_SUBMISSIONS {
        string sub_id PK
        string raw_name
        string raw_dob
        string raw_sex
    }

    LINKAGE_RESULTS {
        string sub_id
        string patient_unique_id
        string status
        float score
        string reason
    }

    PATIENTS ||--o{ METADATA : has
    PATIENTS ||--o{ WAVEFORMS : has
    METADATA ||--o{ WAVEFORMS : groups
    WAVEFORM_TYPES ||--o{ WAVEFORMS : type
    PATIENTS ||--o{ PATIENT_FEATURES : features
    WAVEFORMS ||--o{ SPECTRAL_FEATURES : spectral
    QUESTIONNAIRE_SUBMISSIONS ||--o{ LINKAGE_RESULTS : link
    PATIENTS ||--o{ LINKAGE_RESULTS : matched
    PATIENTS ||--o{ PATIENTS_ID_MAPPING : mapping
```

## Observações
- patient_unique_id é a chave de integração entre patients, metadata e waveforms.
- test_id identifica exames dentro do mesmo paciente.
- voltage_uV e pupil_mm sao mutuamente exclusivos por waveform_type (eletrico vs pupilometria).
- SPECTRAL_FEATURES é derivado de WAVEFORMS + METADATA dims.
- LINKAGE_RESULTS relaciona questionário com pacientes ou registra falhas.
