# Pipeline de Classificação ERG — Neurodivergência

## O que esse pipeline faz?

Usa os dados de exames ERG dos pacientes para prever se um paciente é neurodivergente ou não.
Compara dois modelos — **Decision Tree** e **Random Forest** — com seleção de hiperparâmetros
via nested cross-validation, e ao final compara os resultados com o baseline de Constable et al. (2025).

---

## Notebook

```
studies/neurodivergencia_classification/notebooks/
  neurodivergencia_classification_describre_final.ipynb  ← notebook de resultados finais
```

---

## Estrutura de arquivos de código

```
scripts/
  analysis/
    classification/
      __init__.py              — exports públicos do submódulo
      data_prep.py             — preparação de dados (Polars): filter, binarize, join, aggregate, split
      pipeline.py              — build_classification_pipeline, nested_cv_select_hyperparams,
                                  nested_cv_multiclass, nested_cv_multilabel
      evaluation.py            — log_class_balance, apply_smote_if_needed, evaluate_model,
                                  evaluate_binary_classifier, plot_confusion_matrix_from_counts
      feature_importance.py    — run_feature_importance (MDI + Permutation Importance)
      persistence.py           — save_training_dataset, save_model, save_predictions,
                                  save_feature_importance
  common/
    value_utils.py             — parse_bool_field, parse_label_from_values (Sim/Não → bool)
    logging_utils.py           — log em arquivo + console
```

---

## Dados de entrada

### `id_map_*.parquet` — mapeamento de pacientes
Fica em `output/data/anonymized/staging/`.

| Coluna | Tipo | O que é |
|---|---|---|
| `patient_unique_id_hashed` | String | Hash bcrypt — chave para join com features |
| `neurodivergencia` | String | "Sim", "Não tem", etc. — variável alvo |
| `laudo` | String | Diagnóstico clínico |

### `patients-features_*.parquet` — features dos exames ERG
Fica em `output/data/anonymized/datasets/`.

| Coluna | Tipo | O que é |
|---|---|---|
| `patient_unique_id` | String | Hash bcrypt do paciente |
| `TestedEye` | String | Olho testado (RightEye / LeftEye) |
| `TestStepType` | String | Tipo de protocolo do exame |
| `AWaveTime` | String→Float | Tempo da onda A (ms) |
| `AWaveAmplitude` | String→Float | Amplitude da onda A (µV) |
| `BWaveTime` | String→Float | Tempo da onda B (ms) |
| `BWaveAmplitude` | String→Float | Amplitude da onda B (µV) |
| `WaveformAmplitude` | String→Float | Amplitude geral da forma de onda |

O notebook também pode incorporar features adicionais dependendo da configuração:

| Coluna extra | Origem | O que é |
|---|---|---|
| `welch_peak_freq_hz` | `spectral/erg_spectral_features.parquet` | Frequência de pico Welch |
| `welch_total_energy` | idem | Energia total do espectro |
| `welch_spectral_centroid_hz` | idem | Centroide espectral |
| `ano_nascimento` | `id_map` | Ano de nascimento do paciente |
| `sexo` | `id_map` | Sexo do paciente |

> As colunas numéricas de ERG vêm como String no parquet — o pipeline as converte para Float64 antes do treino.

---

## Fluxo do notebook principal (7 passos)

| Passo | O que acontece | Função/módulo |
|---|---|---|
| 1 | Carrega id_map e features; filtra anotados; binariza label; join espectral + demográfico; agrega por paciente | `filter_annotated`, `binarize_column`, `join_label`, `aggregate_per_patient` |
| 2 | Auditoria do fluxo amostral (N total, rotulados, excluídos, distribuição de classes) | `log_class_balance` |
| 3 | Split 80/20 estratificado | `split_train_test` |
| 4 | Baselines com DummyClassifier (most_frequent, stratified, prior) | `evaluate_binary_classifier` |
| 5 | **Decision Tree** — nested CV → melhores hiperparâmetros → treino → avaliação → permutation test → bootstrap CI → salvar artefatos | `nested_cv_select_hyperparams`, `build_classification_pipeline`, `evaluate_binary_classifier`, `run_feature_importance`, `save_*` |
| 6 | **Random Forest** — mesmo fluxo do passo 5 | idem |
| 7 | Comparação final DT vs RF vs Constable et al. 2025 (balanced accuracy, IC 95%) | `pl.concat` + display |

---

## Pipeline sklearn

```
Dados brutos
    │
    ▼
ColumnTransformer
    ├── Colunas numéricas
    │     ├── SimpleImputer(strategy="median")
    │     └── StandardScaler()
    │
    └── Colunas categóricas
          ├── SimpleImputer(strategy="most_frequent")
          └── OneHotEncoder(handle_unknown="ignore")
    │
    ▼
Estimador (DecisionTreeClassifier ou RandomForestClassifier)
```

O estimador é passado pelo caller — `build_classification_pipeline` aceita qualquer estimador sklearn.

---

## Seleção de hiperparâmetros — Nested CV

Usa `nested_cv_select_hyperparams` com:
- **Outer loop:** `RepeatedStratifiedKFold(n_splits=5, n_repeats=20)` — 100 folds no total
- **Inner loop:** `StratifiedKFold(n_splits=5)` + `GridSearchCV(scoring="balanced_accuracy")`

O parâmetro vencedor é o que ganha mais folds externos.
O modelo final é treinado **depois** do nested CV com os melhores parâmetros no conjunto de treino completo.

---

## Validação estatística

Cada modelo passa por duas validações adicionais após o treino:

**Permutation Test** (`sklearn.model_selection.permutation_test_score`, n=1000):
- Embaralha os labels e roda cross-validation repetida para gerar distribuição nula
- O p-valor indica se o modelo aprendeu algo além do acaso

**Bootstrap CI** (n=5000, reamostragem com reposição):
- Estima intervalo de confiança 95% da balanced accuracy no conjunto de teste

---

## SMOTE

Aplicado automaticamente no treino quando a classe minoritária estiver abaixo de **30%**
(`_SMOTE_THRESHOLD = 0.30` em `evaluation.py`). Nunca aplicado no teste.

---

## Outputs gerados por run

Cada modelo gera artefatos em:

```
output/model-training/{model_name}/{target}/{YYYYMMDD}/{YYYYMMDD_HHMMSS}/
  training_data_{run_tag}.parquet
  test_data_{run_tag}.parquet
  model_{run_tag}.joblib
  predictions_{run_tag}.parquet
  feature_importance_{run_tag}.parquet
```

`model_name` é `"decision_tree"` ou `"random_forest"`. O `output_root` padrão do notebook é `output/model-training/`.

---

## Feature Importance — dois métodos

### MDI (Mean Decrease in Impurity)
- Calculado internamente pelo modelo durante o treino
- Rápido, mas pode superestimar features com alta cardinalidade
- Lido via `model.feature_importances_`

### Permutation Importance
- Embaralha cada feature no conjunto de **teste** e mede queda na balanced accuracy
- Mais confiável para avaliar importância real
- Calculado via `sklearn.inspection.permutation_importance`

**Regra prática:** se MDI e Permutation concordam, confie no resultado. Se discordam, confie no Permutation.

---

## Como recarregar um modelo salvo

```python
import joblib
import pandas as pd

pipeline = joblib.load("output/model-training/decision_tree/neurodivergencia_bin/<YYYYMMDD>/<run_tag>/model_<run_tag>.joblib")

novos_dados = pd.DataFrame({...})
predicoes = pipeline.predict(novos_dados)
```

O Pipeline já inclui o pré-processamento — não é necessário normalizar antes de prever.
