# Documentação de Funções

## scripts/common/path_utils.py

### resolve_base_dir()
Arquivo: scripts/common/path_utils.py
Linha: 6
Objetivo: Resolver base para Path absoluto.
Parâmetros:
- base: str
Tipos:
- base: str
Valores esperados:
- Path existente ou nao (não valida existência)
Retorno:
- Path absoluto
Tipo de retorno:
- pathlib.Path
Exceções possíveis:
- N/A
Dependências:
- pathlib.Path
Complexidade aproximada:
- O(1)

### resolve_input_path()
Arquivo: scripts/common/path_utils.py
Linha: 10
Objetivo: Resolver path de entrada com opcao de validar existencia.
Parâmetros:
- base_dir: Path
- raw_path: str
- must_exist: bool
Tipos:
- base_dir: pathlib.Path
- raw_path: str
- must_exist: bool
Valores esperados:
- raw_path relativo ou absoluto
Retorno:
- Path resolvido
Tipo de retorno:
- pathlib.Path
Exceções possíveis:
- FileNotFoundError se must_exist e path não existe
Dependências:
- pathlib.Path
Complexidade aproximada:
- O(1)

### resolve_output_dir()
Arquivo: scripts/common/path_utils.py
Linha: 19
Objetivo: Resolver path de saida e opcionalmente criar diretorio.
Parâmetros:
- base_dir: Path
- raw_path: str
- create: bool
Tipos:
- base_dir: pathlib.Path
- raw_path: str
- create: bool
Valores esperados:
- raw_path relativo ou absoluto
Retorno:
- Path resolvido
Tipo de retorno:
- pathlib.Path
Exceções possíveis:
- OSError em mkdir (permissao)
Dependências:
- pathlib.Path
Complexidade aproximada:
- O(1)

## scripts/common/logging_utils.py

### configure_logging()
Arquivo: scripts/common/logging_utils.py
Linha: 12
Objetivo: Configurar logging com arquivo em logs/ e console.
Parâmetros:
- level: int (default logging.INFO)
- fmt: str
Tipos:
- level: int
- fmt: str
Valores esperados:
- fmt compatível com logging
Retorno:
- None
Tipo de retorno:
- None
Exceções possíveis:
- OSError ao criar logs/ ou abrir arquivo
Dependências:
- logging, datetime, pathlib
Complexidade aproximada:
- O(1)

## scripts/common/id_utils.py

### _safe_str()
Arquivo: scripts/common/id_utils.py
Linha: 33
Objetivo: Converter valor para string segura (strip) com tratamento de NaN/None.
Parâmetros:
- value: object
Tipos:
- object
Valores esperados:
- Qualquer
Retorno:
- string limpa
Tipo de retorno:
- str
Exceções possíveis:
- N/A
Dependências:
- pandas.isna
Complexidade aproximada:
- O(1)

### clean_patient_name()
Arquivo: scripts/common/id_utils.py
Linha: 38
Objetivo: Limpar nome removendo prefixos e caracteres corrompidos.
Parâmetros:
- text: object
Tipos:
- object
Valores esperados:
- string com nome
Retorno:
- string limpa
Tipo de retorno:
- str
Exceções possíveis:
- N/A
Dependências:
- re
Complexidade aproximada:
- O(n)

### normalize_name()
Arquivo: scripts/common/id_utils.py
Linha: 47
Objetivo: Normalizar nome para lowercase ASCII alnum.
Parâmetros:
- value: object
Tipos:
- object
Valores esperados:
- nome humano
Retorno:
- nome normalizado
Tipo de retorno:
- str
Exceções possíveis:
- N/A
Dependências:
- unicodedata, re
Complexidade aproximada:
- O(n)

### normalize_prontuario()
Arquivo: scripts/common/id_utils.py
Linha: 64
Objetivo: Extrair parte numerica do prontuario.
Parâmetros:
- value: object
Tipos:
- object
Valores esperados:
- texto com numeros
Retorno:
- string numerica ou vazio
Tipo de retorno:
- str
Exceções possíveis:
- N/A
Dependências:
- re
Complexidade aproximada:
- O(n)

### format_birth_yyMMdd()
Arquivo: scripts/common/id_utils.py
Linha: 72
Objetivo: Converter data de nascimento para YYMMDD.
Parâmetros:
- value: object
Tipos:
- object
Valores esperados:
- data em formatos comuns
Retorno:
- string YYMMDD ou ""
Tipo de retorno:
- str
Exceções possíveis:
- N/A (usa pandas.to_datetime com errors=coerce)
Dependências:
- pandas.to_datetime
Complexidade aproximada:
- O(n)

### format_birth_metadata()
Arquivo: scripts/common/id_utils.py
Linha: 88
Objetivo: Converter YYMMDD para formato YY/MM/DD.
Parâmetros:
- value: object
Tipos:
- object
Valores esperados:
- data valida
Retorno:
- string formatada ou ""
Tipo de retorno:
- str
Exceções possíveis:
- N/A
Dependências:
- format_birth_yyMMdd
Complexidade aproximada:
- O(1)

### format_test_yyMMddHHMMSS()
Arquivo: scripts/common/id_utils.py
Linha: 95
Objetivo: Converter data/hora de teste para YYMMDDHHMMSS.
Parâmetros:
- value: object
Tipos:
- object
Valores esperados:
- data/hora em formatos comuns
Retorno:
- string YYMMDDHHMMSS ou ""
Tipo de retorno:
- str
Exceções possíveis:
- N/A
Dependências:
- pandas.to_datetime
Complexidade aproximada:
- O(n)

### format_test_metadata()
Arquivo: scripts/common/id_utils.py
Linha: 111
Objetivo: Converter YYMMDDHHMMSS para YY/MM/DD HH:MM:SS.
Parâmetros:
- value: object
Tipos:
- object
Valores esperados:
- string de 12 digitos
Retorno:
- string formatada ou ""
Tipo de retorno:
- str
Exceções possíveis:
- N/A
Dependências:
- format_test_yyMMddHHMMSS
Complexidade aproximada:
- O(1)

### extract_prontuario_and_name()
Arquivo: scripts/common/id_utils.py
Linha: 118
Objetivo: Extrair prontuario e nome de um campo combinado.
Parâmetros:
- patientid_field: object
Tipos:
- object
Valores esperados:
- texto contendo prontuario e nome
Retorno:
- (prontuario, nome)
Tipo de retorno:
- Tuple[Optional[str], Optional[str]]
Exceções possíveis:
- N/A
Dependências:
- re
Complexidade aproximada:
- O(n)

### parse_patient_unique_id()
Arquivo: scripts/common/id_utils.py
Linha: 136
Objetivo: Parsear patient_unique_id em partes (prontuario, nome, birth, test).
Parâmetros:
- pid: object
Tipos:
- object
Valores esperados:
- ID com separadores '_' e '-'
Retorno:
- (prontuario, name_part, birth_part, test_part)
Tipo de retorno:
- Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]
Exceções possíveis:
- N/A
Dependências:
- re, normalize_name
Complexidade aproximada:
- O(n)

### build_patient_unique_id()
Arquivo: scripts/common/id_utils.py
Linha: 189
Objetivo: Construir patient_unique_id canonical.
Parâmetros:
- prontuario: object
- name: object
- birth_raw: object
- test_raw: object
Tipos:
- object
Valores esperados:
- valores de prontuario/nome/data
Retorno:
- string de ID
Tipo de retorno:
- str
Exceções possíveis:
- N/A
Dependências:
- normalize_prontuario, normalize_name, format_birth_yyMMdd, format_test_yyMMddHHMMSS
Complexidade aproximada:
- O(n)

### match_name_prefix()
Arquivo: scripts/common/id_utils.py
Linha: 208
Objetivo: Encontrar match exato ou por prefixo em lookup de nomes normalizados.
Parâmetros:
- norm_name: str
- name_lookup: dict[str, object]
Tipos:
- str, dict
Valores esperados:
- norm_name não vazio
Retorno:
- (value, method)
Tipo de retorno:
- Tuple[object | None, str]
Exceções possíveis:
- N/A
Dependências:
- N/A
Complexidade aproximada:
- O(n) no tamanho do lookup

### normalize_patient_id()
Arquivo: scripts/common/id_utils.py
Linha: 224
Objetivo: Canonicalizar patient_unique_id para lookup de hash.
Parâmetros:
- patient_id: object
Tipos:
- object
Valores esperados:
- ID com variações
Retorno:
- string normalizada
Tipo de retorno:
- str
Exceções possíveis:
- N/A
Dependências:
- parse_patient_unique_id
Complexidade aproximada:
- O(n)

## scripts/common/name_utils.py

### tokens_from_raw()
Arquivo: scripts/common/name_utils.py
Linha: 21
Objetivo: Tokenizar nome bruto e normalizar tokens.
Parâmetros:
- raw_name: str
Tipos:
- str
Valores esperados:
- nome com espacos
Retorno:
- lista de tokens normalizados
Tipo de retorno:
- list[str]
Exceções possíveis:
- N/A
Dependências:
- normalize_name
Complexidade aproximada:
- O(n)

### generate_name_variations()
Arquivo: scripts/common/name_utils.py
Linha: 31
Objetivo: Gerar variações de nome ancoradas no primeiro token.
Parâmetros:
- raw_name: str
Tipos:
- str
Valores esperados:
- nome completo
Retorno:
- set de variações
Tipo de retorno:
- set[str]
Exceções possíveis:
- N/A
Dependências:
- tokens_from_raw, itertools.combinations
Complexidade aproximada:
- O(k^2) no numero de tokens

### norm_sex()
Arquivo: scripts/common/name_utils.py
Linha: 95
Objetivo: Normalizar sexo para 'm', 'f' ou ''.
Parâmetros:
- raw: str
Tipos:
- str
Valores esperados:
- Masculino/Feminino/etc
Retorno:
- 'm', 'f' ou ''
Tipo de retorno:
- str
Exceções possíveis:
- N/A
Dependências:
- N/A
Complexidade aproximada:
- O(1)

### compare_gender()
Arquivo: scripts/common/name_utils.py
Linha: 105
Objetivo: Comparar sexo normalizado entre duas strings.
Parâmetros:
- a: str
- b: str
Tipos:
- str
Valores esperados:
- valores de sexo
Retorno:
- True se ambos iguais e não vazios
Tipo de retorno:
- bool
Exceções possíveis:
- N/A
Dependências:
- norm_sex
Complexidade aproximada:
- O(1)

### build_name_signatures()
Arquivo: scripts/common/name_utils.py
Linha: 119
Objetivo: Gerar assinaturas de nome (colapsadas e com espaco).
Parâmetros:
- raw_name: str
Tipos:
- str
Valores esperados:
- nome completo
Retorno:
- set de assinaturas
Tipo de retorno:
- set[str]
Exceções possíveis:
- N/A
Dependências:
- generate_name_variations
Complexidade aproximada:
- O(k^2)

## scripts/common/date_utils.py

### parse_dob_parts()
Arquivo: scripts/common/date_utils.py
Linha: 18
Objetivo: Parsear string de data em (dia, mes, ano).
Parâmetros:
- raw: Optional[str]
Tipos:
- Optional[str]
Valores esperados:
- DD/MM/YYYY ou YYYY/MM/DD
Retorno:
- (day, month, year) ou (None, None, None)
Tipo de retorno:
- Tuple[Optional[int], Optional[int], Optional[int]]
Exceções possíveis:
- N/A (captura erros)
Dependências:
- re
Complexidade aproximada:
- O(n)

### extract_birth_year()
Arquivo: scripts/common/date_utils.py
Linha: 51
Objetivo: Extrair ano de nascimento.
Parâmetros:
- raw_dob: Optional[str]
Tipos:
- Optional[str]
Valores esperados:
- data valida
Retorno:
- ano ou None
Tipo de retorno:
- Optional[int]
Exceções possíveis:
- N/A
Dependências:
- parse_dob_parts
Complexidade aproximada:
- O(n)

### estimate_birth_year_range()
Arquivo: scripts/common/date_utils.py
Linha: 65
Objetivo: Estimar faixa de ano de nascimento a partir de idade + data de teste.
Parâmetros:
- age: Optional[int]
- test_date: object
Tipos:
- Optional[int], object
Valores esperados:
- age 1..120
Retorno:
- (min_year, max_year) ou (None, None)
Tipo de retorno:
- Tuple[Optional[int], Optional[int]]
Exceções possíveis:
- N/A
Dependências:
- N/A
Complexidade aproximada:
- O(1)

### birth_year_range_expr()
Arquivo: scripts/common/date_utils.py
Linha: 96
Objetivo: Expressao Polars para faixa de ano de nascimento.
Parâmetros:
- age_col: str
- test_date_col: str
Tipos:
- str
Valores esperados:
- colunas existentes no DataFrame
Retorno:
- (expr_min, expr_max)
Tipo de retorno:
- Tuple[pl.Expr, pl.Expr]
Exceções possíveis:
- N/A
Dependências:
- polars
Complexidade aproximada:
- O(1)

### mapping_dob_to_year_month_day_exprs()
Arquivo: scripts/common/date_utils.py
Linha: 119
Objetivo: Expressao Polars para extrair dob_year/dob_month/dob_day de data_nascimento.
Parâmetros:
- N/A
Tipos:
- N/A
Valores esperados:
- coluna data_nascimento em YY/MM/DD
Retorno:
- (year_expr, month_expr, day_expr)
Tipo de retorno:
- Tuple[pl.Expr, pl.Expr, pl.Expr]
Exceções possíveis:
- N/A
Dependências:
- polars
Complexidade aproximada:
- O(1)

## scripts/common/patient_lookup.py

### build_patient_table()
Arquivo: scripts/common/patient_lookup.py
Linha: 47
Objetivo: Unir patients_id_mapping com medical_records_history e derivar colunas de identidade.
Parâmetros:
- records_path: Path
- mapping_root: Path
Tipos:
- pathlib.Path
Valores esperados:
- parquets existentes
Retorno:
- DataFrame Polars consolidado
Tipo de retorno:
- pl.DataFrame
Exceções possíveis:
- FileNotFoundError se patients_id_mapping não encontrado
Dependências:
- polars, mapping_dob_to_year_month_day_exprs, normalize_name
Complexidade aproximada:
- O(n) leitura + join

### build_righteye_table()
Arquivo: scripts/common/patient_lookup.py
Linha: 160
Objetivo: Derivar tabela de identidade por paciente a partir do RightEye.
Parâmetros:
- righteye_path: Path
Tipos:
- pathlib.Path
Valores esperados:
- parquet RightEye com colunas de identidade
Retorno:
- DataFrame Polars com colunas normalizadas
Tipo de retorno:
- pl.DataFrame
Exceções possíveis:
- COMPORTAMENTO NÃO CONFIRMADO (schema invalido)
Dependências:
- polars, birth_year_range_expr, normalize_name
Complexidade aproximada:
- O(n log n) devido sort

### find_by_dob()
Arquivo: scripts/common/patient_lookup.py
Linha: 248
Objetivo: Filtrar pacientes por dia/mes/ano (qualquer combinacao).
Parâmetros:
- patients: pl.DataFrame
- day: Optional[int]
- month: Optional[int]
- year: Optional[int]
Tipos:
- pl.DataFrame, Optional[int]
Valores esperados:
- colunas dob_year/dob_month/dob_day
Retorno:
- subset do DataFrame
Tipo de retorno:
- pl.DataFrame
Exceções possíveis:
- N/A
Dependências:
- polars
Complexidade aproximada:
- O(n)

### find_by_exact_name()
Arquivo: scripts/common/patient_lookup.py
Linha: 275
Objetivo: Filtrar pacientes com nome normalizado exato.
Parâmetros:
- patients: pl.DataFrame
- norm_name: str
Tipos:
- pl.DataFrame, str
Valores esperados:
- coluna norm_nome
Retorno:
- subset do DataFrame
Tipo de retorno:
- pl.DataFrame
Exceções possíveis:
- N/A
Dependências:
- polars
Complexidade aproximada:
- O(n)

### find_by_first_name()
Arquivo: scripts/common/patient_lookup.py
Linha: 282
Objetivo: Filtrar por prefixo do primeiro token normalizado.
Parâmetros:
- patients: pl.DataFrame
- first_token: str
Tipos:
- pl.DataFrame, str
Valores esperados:
- coluna norm_nome
Retorno:
- subset do DataFrame
Tipo de retorno:
- pl.DataFrame
Exceções possíveis:
- N/A
Dependências:
- polars
Complexidade aproximada:
- O(n)

### find_by_name_variations()
Arquivo: scripts/common/patient_lookup.py
Linha: 294
Objetivo: Filtrar por conjunto de variações (match exato ou prefixo).
Parâmetros:
- patients: pl.DataFrame
- variations: set[str]
Tipos:
- pl.DataFrame, set[str]
Valores esperados:
- coluna norm_nome
Retorno:
- subset do DataFrame
Tipo de retorno:
- pl.DataFrame
Exceções possíveis:
- N/A
Dependências:
- polars
Complexidade aproximada:
- O(n * v) para prefixos

### find_by_sex()
Arquivo: scripts/common/patient_lookup.py
Linha: 320
Objetivo: Filtrar por sexo normalizado, sem eliminar se vazio.
Parâmetros:
- patients: pl.DataFrame
- sex_norm: str
Tipos:
- pl.DataFrame, str
Valores esperados:
- coluna sexo
Retorno:
- subset do DataFrame (ou original)
Tipo de retorno:
- pl.DataFrame
Exceções possíveis:
- N/A
Dependências:
- polars
Complexidade aproximada:
- O(n)

### find_by_rapidfuzz()
Arquivo: scripts/common/patient_lookup.py
Linha: 338
Objetivo: Filtrar por score RapidFuzz acima do threshold.
Parâmetros:
- patients: pl.DataFrame
- norm_name: str
- threshold: int
Tipos:
- pl.DataFrame, str, int
Valores esperados:
- rapidfuzz instalado
Retorno:
- subset do DataFrame
Tipo de retorno:
- pl.DataFrame
Exceções possíveis:
- ImportError (rapdifuzz não instalado) tratado com warning
Dependências:
- rapidfuzz.process.cdist
Complexidade aproximada:
- O(n * m) para computo de distancias

## scripts/common/patient_utils.py

### extract_birth_year_expr()
Arquivo: scripts/common/patient_utils.py
Linha: 8
Objetivo: Derivar ano de nascimento a partir de YY/MM/DD.
Parâmetros:
- col: str (default data_nascimento)
Tipos:
- str
Valores esperados:
- coluna string YY/MM/DD
Retorno:
- expr Polars
Tipo de retorno:
- pl.Expr
Exceções possíveis:
- N/A
Dependências:
- polars
Complexidade aproximada:
- O(1)

## scripts/common/value_utils.py

### parse_label_from_values()
Arquivo: scripts/common/value_utils.py
Linha: 19
Objetivo: Binarizar campo livre a partir de lista de valores falsos.
Parâmetros:
- value: object
- false_values: Collection[str]
- case_sensitive: bool
Tipos:
- object, Collection[str], bool
Valores esperados:
- false_values não vazio quando usado
Retorno:
- True/False/None
Tipo de retorno:
- bool | None
Exceções possíveis:
- N/A
Dependências:
- re
Complexidade aproximada:
- O(n)

### parse_bool_field()
Arquivo: scripts/common/value_utils.py
Linha: 52
Objetivo: Normalizar campo booleano com padroes PT/EN.
Parâmetros:
- value: object
Tipos:
- object
Valores esperados:
- texto livre
Retorno:
- True/False/None
Tipo de retorno:
- bool | None
Exceções possíveis:
- N/A
Dependências:
- re
Complexidade aproximada:
- O(n)

## scripts/common/df_utils.py

### dedup_and_log()
Arquivo: scripts/common/df_utils.py
Linha: 13
Objetivo: Deduplicar DataFrame por subset e logar quantidade removida.
Parâmetros:
- df: pl.DataFrame
- subset: list[str]
- label: str
Tipos:
- pl.DataFrame, list[str], str
Valores esperados:
- subset com colunas existentes
Retorno:
- DataFrame deduplicado
Tipo de retorno:
- pl.DataFrame
Exceções possíveis:
- N/A
Dependências:
- polars
Complexidade aproximada:
- O(n)

## scripts/pipeline_utils.py

### detect_encoding()
Arquivo: scripts/pipeline_utils.py
Linha: 29
Objetivo: Detectar encoding do arquivo com chardet.
Parâmetros:
- path: Path
- num_bytes: int
Tipos:
- Path, int
Valores esperados:
- arquivo existente
Retorno:
- encoding
Tipo de retorno:
- str
Exceções possíveis:
- N/A (fallback utf-8)
Dependências:
- chardet
Complexidade aproximada:
- O(num_bytes)

### read_csv_arrow()
Arquivo: scripts/pipeline_utils.py
Linha: 40
Objetivo: Ler CSV em Arrow Table com encoding detectado.
Parâmetros:
- path: Path
Tipos:
- Path
Retorno:
- Arrow Table
Tipo de retorno:
- pyarrow.Table
Exceções possíveis:
- COMPORTAMENTO NÃO CONFIRMADO (falha de parsing)
Dependências:
- pyarrow.csv
Complexidade aproximada:
- O(n)

### iter_csv_arrow()
Arquivo: scripts/pipeline_utils.py
Linha: 52
Objetivo: Iterar CSV em batches Arrow RecordBatch.
Parâmetros:
- path: Path
- batch_size: int
Tipos:
- Path, int
Retorno:
- iterator de RecordBatch
Tipo de retorno:
- Iterator[pa.RecordBatch]
Exceções possíveis:
- COMPORTAMENTO NÃO CONFIRMADO
Dependências:
- pyarrow.csv
Complexidade aproximada:
- O(n)

### normalize_patient_id()
Arquivo: scripts/pipeline_utils.py
Linha: 186
Objetivo: Wrapper para normalizar patient_unique_id (pipeline).
Parâmetros:
- patient_id: object
Tipos:
- object
Retorno:
- string normalizada
Tipo de retorno:
- str
Dependências:
- common.id_utils.normalize_patient_id
Complexidade aproximada:
- O(n)

### load_hash_mapping()
Arquivo: scripts/pipeline_utils.py
Linha: 199
Objetivo: Ler mapping parquet e construir dict patient_id -> hash.
Parâmetros:
- mapping_path: Path
Tipos:
- Path
Retorno:
- dict
Tipo de retorno:
- Dict[str, str]
Exceções possíveis:
- COMPORTAMENTO NÃO CONFIRMADO
Dependências:
- polars
Complexidade aproximada:
- O(n)

### drop_columns_if_present()
Arquivo: scripts/pipeline_utils.py
Linha: 208
Objetivo: Remover colunas se existirem.
Parâmetros:
- df: pl.DataFrame
- columns: list[str]
Retorno:
- pl.DataFrame
Complexidade aproximada:
- O(k)

### dedupe_mapping()
Arquivo: scripts/pipeline_utils.py
Linha: 214
Objetivo: Remover duplicatas do mapping e logar.
Parâmetros:
- mapping: pl.DataFrame
Retorno:
- pl.DataFrame
Dependências:
- logging
Complexidade aproximada:
- O(n)

## scripts/pipeline/raw_to_consolidated/patient_preparation.py

### apply_target_partitions()
Arquivo: scripts/pipeline/raw_to_consolidated/patient_preparation.py
Linha: 38
Objetivo: Ajustar numero de partições Spark.
Parâmetros:
- df: Spark DataFrame
- target_partitions: int | None
Tipos:
- Spark DataFrame, Optional[int]
Valores esperados:
- target_partitions > 0
Retorno:
- Spark DataFrame com partitions ajustadas
Tipo de retorno:
- Spark DataFrame
Exceções possíveis:
- COMPORTAMENTO NÃO CONFIRMADO
Dependências:
- Spark
Complexidade aproximada:
- O(1) + custo Spark

### find_csv_files()
Arquivo: scripts/pipeline/raw_to_consolidated/patient_preparation.py
Linha: 50
Objetivo: Encontrar CSVs em diretorio ou arquivo.
Parâmetros:
- base: Path
- relative_path: str
Tipos:
- Path, str
Valores esperados:
- path existente
Retorno:
- lista de Paths CSV
Tipo de retorno:
- List[Path]
Exceções possíveis:
- FileNotFoundError via resolve_input_path
Dependências:
- common.path_utils
Complexidade aproximada:
- O(n) no numero de arquivos

### detect_encoding()
Arquivo: scripts/pipeline/raw_to_consolidated/patient_preparation.py
Linha: 57
Objetivo: Detectar encoding do arquivo.
Parâmetros:
- path: Path
- num_bytes: int
Tipos:
- Path, int
Valores esperados:
- arquivo existente
Retorno:
- encoding string
Tipo de retorno:
- str
Exceções possíveis:
- N/A (fallback latin-1)
Dependências:
- chardet
Complexidade aproximada:
- O(num_bytes)

### build_spark_session()
Arquivo: scripts/pipeline/raw_to_consolidated/patient_preparation.py
Linha: 67
Objetivo: Criar SparkSession para stage patients.
Parâmetros:
- workers: int | None
Tipos:
- Optional[int]
Valores esperados:
- workers > 0 ou None
Retorno:
- SparkSession
Tipo de retorno:
- pyspark.sql.SparkSession
Exceções possíveis:
- RuntimeError se pyspark não instalado
Dependências:
- pyspark
Complexidade aproximada:
- O(1)

### try_read_csv_rows_with_header_guesses()
Arquivo: scripts/pipeline/raw_to_consolidated/patient_preparation.py
Linha: 88
Objetivo: Ler CSV com tentativa de encoding e header heuristico.
Parâmetros:
- path: Path
Tipos:
- Path
Valores esperados:
- CSV com linhas de dados
Retorno:
- lista de dicts (linhas)
Tipo de retorno:
- List[Dict[str, str]]
Exceções possíveis:
- ValueError se não conseguir parsear
Dependências:
- csv, detect_encoding
Complexidade aproximada:
- O(n) linhas

### normalize_row_columns()
Arquivo: scripts/pipeline/raw_to_consolidated/patient_preparation.py
Linha: 139
Objetivo: Normalizar colunas esperadas (PatientID, PatientBirthdate, TestingDate).
Parâmetros:
- row: Dict[str, str]
Tipos:
- dict
Valores esperados:
- chaves variaveis
Retorno:
- dict normalizado
Tipo de retorno:
- Dict[str, str]
Exceções possíveis:
- N/A
Dependências:
- N/A
Complexidade aproximada:
- O(k)

### build_patient_unique_id_from_row()
Arquivo: scripts/pipeline/raw_to_consolidated/patient_preparation.py
Linha: 180
Objetivo: Gerar patient_unique_id a partir de campos brutos.
Parâmetros:
- patientid_raw: str
- birthdate_raw: str
- testingdate_raw: str
Tipos:
- str
Valores esperados:
- strings possivelmente vazias
Retorno:
- patient_unique_id
Tipo de retorno:
- str
Exceções possíveis:
- N/A
Dependências:
- extract_prontuario_and_name, build_patient_unique_id
Complexidade aproximada:
- O(n)

### process_file()
Arquivo: scripts/pipeline/raw_to_consolidated/patient_preparation.py
Linha: 185
Objetivo: Processar um CSV e gerar rows de patients e mapping.
Parâmetros:
- path: Path
Tipos:
- Path
Valores esperados:
- CSV valido
Retorno:
- (patient_rows, mapping_rows)
Tipo de retorno:
- Tuple[List[Dict], List[Dict]]
Exceções possíveis:
- Captura exceções e retorna listas vazias
Dependências:
- try_read_csv_rows_with_header_guesses, normalize_row_columns,
  build_patient_unique_id_from_row, format_birth_metadata, format_test_metadata,
  extract_prontuario_and_name, normalize_name
Complexidade aproximada:
- O(n)
Fluxo detalhado:
1) Ler CSV com heuristicas de header.
2) Normalizar colunas e construir patient_unique_id.
3) Normalizar datas (birth/test) e alinhar campos.
4) Gerar patient_rows com patient_unique_id.
5) Gerar mapping_rows com prontuario/nome/data.

### build_parser()
Arquivo: scripts/pipeline/raw_to_consolidated/patient_preparation.py
Linha: 235
Objetivo: Construir argparse do stage.
Parâmetros:
- N/A
Retorno:
- ArgumentParser
Tipo de retorno:
- argparse.ArgumentParser
Exceções possíveis:
- N/A
Dependências:
- argparse
Complexidade aproximada:
- O(1)

### run()
Arquivo: scripts/pipeline/raw_to_consolidated/patient_preparation.py
Linha: 252
Objetivo: Orquestrar processamento de arquivos e escrita parquet via Spark.
Parâmetros:
- args: argparse.Namespace
Tipos:
- argparse.Namespace
Valores esperados:
- args.input, args.output
Retorno:
- None
Exceções possíveis:
- SystemExit indireto se sem CSVs (log error)
Dependências:
- ThreadPoolExecutor, SparkSession
Complexidade aproximada:
- O(n) + custos Spark
Fluxo detalhado:
1) Resolver base/output e listar CSVs.
2) Processar arquivos em paralelo e escrever JSONL temporarios.
3) Criar SparkSession e ler JSONL.
4) Escrever patients-*.parquet e patients_id_mapping-*.parquet.
5) Remover temporarios.

### main()
Arquivo: scripts/pipeline/raw_to_consolidated/patient_preparation.py
Linha: 330
Objetivo: Entrypoint CLI.
Parâmetros:
- N/A
Retorno:
- None
Exceções possíveis:
- N/A
Dependências:
- configure_logging
Complexidade aproximada:
- O(1)

## scripts/pipeline/raw_to_consolidated/waveform_consolidation.py

### apply_target_partitions()
Arquivo: scripts/pipeline/raw_to_consolidated/waveform_consolidation.py
Linha: 42
Objetivo: Ajustar numero de partições Spark.
Parâmetros:
- df: Spark DataFrame
- target_partitions: int | None
Retorno: Spark DataFrame
Exceções possíveis: COMPORTAMENTO NÃO CONFIRMADO
Dependências: Spark
Complexidade: O(1) + custo Spark

### build_spark_session()
Arquivo: scripts/pipeline/raw_to_consolidated/waveform_consolidation.py
Linha: 54
Objetivo: Criar SparkSession para consolidacao de waveforms.
Parâmetros:
- workers, max_records_per_file, heartbeat_interval, network_timeout
Retorno: SparkSession
Exceções: RuntimeError se pyspark ausente
Dependências: pyspark
Complexidade: O(1)

### normalize_name()
Arquivo: scripts/pipeline/raw_to_consolidated/waveform_consolidation.py
Linha: 86
Objetivo: Alias para normalize_name_token.
Parâmetros:
- raw_name: str
Retorno: str
Complexidade: O(n)

### read_csv_lines_with_fallback()
Arquivo: scripts/pipeline/raw_to_consolidated/waveform_consolidation.py
Linha: 91
Objetivo: Ler CSV com fallback de encoding.
Parâmetros:
- input_file: str
Retorno: List[List[str]]
Exceções: ValueError se não decodificar
Dependências: csv
Complexidade: O(n)

### parse_float()
Arquivo: scripts/pipeline/raw_to_consolidated/waveform_consolidation.py
Linha: 109
Objetivo: Converter string para float com tolerancia a vazio.
Parâmetros: value: str
Retorno: Optional[float]
Complexidade: O(1)

### infer_birth_yyMMdd_from_metadata()
Arquivo: scripts/pipeline/raw_to_consolidated/waveform_consolidation.py
Linha: 119
Objetivo: Inferir nascimento YYMMDD a partir de metadata.
Parâmetros: metadata_records
Retorno: str
Complexidade: O(n)

### infer_test_yyMMddHHMMSS_from_metadata()
Arquivo: scripts/pipeline/raw_to_consolidated/waveform_consolidation.py
Linha: 128
Objetivo: Inferir data de teste a partir de metadata.
Parâmetros: metadata_records
Retorno: str
Complexidade: O(n)

### infer_patientid_from_metadata()
Arquivo: scripts/pipeline/raw_to_consolidated/waveform_consolidation.py
Linha: 137
Objetivo: Inferir PatientID do metadata.
Parâmetros: metadata_records
Retorno: str
Complexidade: O(n)

### format_test_metadata()
Arquivo: scripts/pipeline/raw_to_consolidated/waveform_consolidation.py
Linha: 145
Objetivo: Formatar YYMMDDHHMMSS para YY/MM/DD HH:MM:SS.
Parâmetros: test_yyMMddHHMMSS
Retorno: str
Complexidade: O(1)

### extract_patient_info_from_filename()
Arquivo: scripts/pipeline/raw_to_consolidated/waveform_consolidation.py
Linha: 154
Objetivo: Extrair id_prontuario, nome e datas do nome do arquivo.
Parâmetros: filename: str
Retorno: Dict com identidade e patient_unique_id
Exceções: N/A (fallback para filename)
Dependências: regex, normalize_name_token, build_patient_unique_id
Complexidade: O(n)

### apply_metadata_identity_fallback()
Arquivo: scripts/pipeline/raw_to_consolidated/waveform_consolidation.py
Linha: 234
Objetivo: Mesclar identidade derivada do filename com metadata sem colapsar identidade valida.
Parâmetros:
- patient_info: dict
- metadata_records: list[dict]
Retorno: dict atualizado
Complexidade: O(n)

### process_reteval_csv()
Arquivo: scripts/pipeline/raw_to_consolidated/waveform_consolidation.py
Linha: 279
Objetivo: Processar um CSV RETeval e gerar parquets metadata + waveforms.
Parâmetros:
- input_file: str
- output_dir: str
Retorno:
- (metadata_path, waveforms_path) ou None
Exceções:
- ValueError se decodificacao falhar
Dependências:
- read_csv_lines_with_fallback, extract_patient_info_from_filename,
  apply_metadata_identity_fallback, parse_float, pyarrow
Complexidade aproximada:
- O(n) no tamanho do CSV
Fluxo detalhado:
1) Ler CSV com fallback de encoding.
2) Extrair 11 linhas de metadata e montar registros por teste.
3) Derivar patient_info a partir do filename e metadata.
4) Escrever metadata parquet (um registro por teste).
5) Detectar secoes de waveform e mapear colunas por test_id.
6) Iterar secoes e escrever waveforms em parquet incremental.
7) Remover outputs se não houver dados de waveform.

### consolidate_files()
Arquivo: scripts/pipeline/raw_to_consolidated/waveform_consolidation.py
Linha: 498
Objetivo: Consolidar parquets temporarios em consolidated_metadata/waveforms via Spark.
Parâmetros:
- output_dir, workers, metadata_partitions, waveform_partitions,
  max_records_per_file, spark_heartbeat_interval, spark_network_timeout
Retorno:
- (consolidated_metadata_path, consolidated_waveforms_path) ou None
Exceções:
- COMPORTAMENTO NÃO CONFIRMADO (Spark)
Complexidade:
- O(n) + custos Spark

### save_error_report()
Arquivo: scripts/pipeline/raw_to_consolidated/waveform_consolidation.py
Linha: 573
Objetivo: Escrever relatório de erros em processing_errors.txt.
Parâmetros:
- errors: List[Dict[str, str]]
- output_dir: Path
Retorno: None
Complexidade: O(n)

### build_parser()
Arquivo: scripts/pipeline/raw_to_consolidated/waveform_consolidation.py
Linha: 595
Objetivo: Construir argparse do stage.
Parâmetros: N/A
Retorno: ArgumentParser
Complexidade: O(1)

### run()
Arquivo: scripts/pipeline/raw_to_consolidated/waveform_consolidation.py
Linha: 634
Objetivo: Processar todos CSVs e consolidar outputs.
Parâmetros: args
Retorno: None (SystemExit se falha)
Complexidade: O(n) + custos Spark
Fluxo detalhado:
1) Resolver input/output e listar CSVs.
2) Processar arquivos em paralelo com ThreadPoolExecutor.
3) Registrar erros e salvar relatório.
4) Consolidar metadata/waveforms em parquets finais.

### main()
Arquivo: scripts/pipeline/raw_to_consolidated/waveform_consolidation.py
Linha: 705
Objetivo: Entrypoint CLI.
Parâmetros: N/A
Retorno: None
Dependências: configure_logging

## scripts/pipeline/raw_to_consolidated/consolidate_from_raw.py

### _latest_match()
Arquivo: scripts/pipeline/raw_to_consolidated/consolidate_from_raw.py
Linha: 29
Objetivo: Selecionar path mais recente por mtime.
Parâmetros: paths: list[Path]
Retorno: Path
Complexidade: O(n log n)

### _discover_dataset()
Arquivo: scripts/pipeline/raw_to_consolidated/consolidate_from_raw.py
Linha: 33
Objetivo: Descobrir dataset por patterns recursivos.
Parâmetros: root, patterns, label
Retorno: Path
Exceções: FileNotFoundError
Complexidade: O(n)

### run()
Arquivo: scripts/pipeline/raw_to_consolidated/consolidate_from_raw.py
Linha: 43
Objetivo: Orquestrar consolidacao + audit cross.
Parâmetros: args
Retorno: None
Dependências: run_patient_preparation, run_waveform_consolidation, run_id_audit
Complexidade: O(n) + custos Spark

### build_parser()
Arquivo: scripts/pipeline/raw_to_consolidated/consolidate_from_raw.py
Linha: 98
Objetivo: Construir argparse do stage.
Retorno: ArgumentParser

## scripts/pipeline/hashing/normalize_patients.py

### _resolve_input()
Arquivo: scripts/pipeline/hashing/normalize_patients.py
Linha: 15
Objetivo: Resolver path absoluto de input.
Parâmetros: base, raw_path
Retorno: Path

### run()
Arquivo: scripts/pipeline/hashing/normalize_patients.py
Linha: 20
Objetivo: Normalizar coluna de ID em CSVs.
Parâmetros: base, inputs, column, output_dir
Retorno: None
Exceções: COMPORTAMENTO NÃO CONFIRMADO
Complexidade: O(n)

## scripts/pipeline/hashing/hash_mapping.py

### run()
Arquivo: scripts/pipeline/hashing/hash_mapping.py
Linha: 19
Objetivo: Gerar mapping hash parquet.
Parâmetros: base, input_csv, output_parquet, column, salt
Retorno: None
Exceções: ValueError se coluna nao encontrada
Dependências: pipeline_utils.PatientIDHasher
Complexidade: O(n)

## scripts/pipeline/hashing/hash_apply_streaming.py

### _resolve_parquet_files()
Arquivo: scripts/pipeline/hashing/hash_apply_streaming.py
Linha: 25
Objetivo: Listar arquivos parquet validos (ignora markers).
Parâmetros: path: Path
Retorno: List[str]
Exceções: FileNotFoundError se nenhum parquet
Complexidade: O(n)

### _output_filename_for_input()
Arquivo: scripts/pipeline/hashing/hash_apply_streaming.py
Linha: 36
Objetivo: Derivar nome curto de output para arquivos hash.
Parâmetros: input_path, name_suffix
Retorno: str
Complexidade: O(1)

### _is_empty_like_expr()
Arquivo: scripts/pipeline/hashing/hash_apply_streaming.py
Linha: 53
Objetivo: Expressao Polars para detectar vazio/NaN/None.
Parâmetros: column: str
Retorno: pl.Expr
Complexidade: O(1)

### _coerce_numeric_columns()
Arquivo: scripts/pipeline/hashing/hash_apply_streaming.py
Linha: 62
Objetivo: Coagir colunas numericas com logging de invalidos.
Parâmetros: df, float_columns, int_columns
Retorno: pl.DataFrame
Complexidade: O(n)

### _read_dataset_as_polars()
Arquivo: scripts/pipeline/hashing/hash_apply_streaming.py
Linha: 88
Objetivo: Ler dataset CSV/Parquet em Polars.
Parâmetros: path
Retorno: pl.DataFrame
Complexidade: O(n)

### _build_id_map()
Arquivo: scripts/pipeline/hashing/hash_apply_streaming.py
Linha: 98
Objetivo: Criar mapa source_file|test_id -> patient_unique_id.
Parâmetros: metadata_path
Retorno: Dict[str, str]
Exceções: ValueError se colunas ausentes
Complexidade: O(n)

### _build_id_map_before_after()
Arquivo: scripts/pipeline/hashing/hash_apply_streaming.py
Linha: 129
Objetivo: Criar mapa de IDs corrigidos comparando metadata before/after.
Parâmetros: before_path, after_path
Retorno: Dict[str, str]
Exceções: ValueError se colunas ausentes
Complexidade: O(n)

### _iter_input_chunks()
Arquivo: scripts/pipeline/hashing/hash_apply_streaming.py
Linha: 181
Objetivo: Iterar CSV/Parquet em chunks Polars.
Parâmetros: input_path, chunk_size
Retorno: iterator de pl.DataFrame
Complexidade: O(n)

### _apply_single_input()
Arquivo: scripts/pipeline/hashing/hash_apply_streaming.py
Linha: 194
Objetivo: Aplicar hash em um arquivo e escrever parquet em streaming.
Parâmetros:
- input_path, output_path, mapping, debug_writer, column, drop_columns,
  chunk_size, float_columns, int_columns, metadata_id_map
Retorno: None
Exceções: ValueError se coluna de ID ausente
Complexidade: O(n)
Fluxo detalhado:
1) Iterar chunks do input.
2) Normalizar patient_unique_id.
3) Aplicar correcoes via metadata_id_map (source_file|test_id).
4) Mapear para hashed ID e registrar missing.
5) Coagir colunas numericas e remover colunas sensiveis.
6) Escrever chunk em parquet.

### run()
Arquivo: scripts/pipeline/hashing/hash_apply_streaming.py
Linha: 277
Objetivo: Aplicar hash a multiplos inputs.
Parâmetros: base, inputs, mapping_path, output_dir, debug_csv, column, drop_columns,
  chunk_size, float_columns, int_columns, metadata_before, metadata_after, metadata, name_suffix
Retorno: None
Complexidade: O(n)

## scripts/pipeline/hashing/hash_orchestrator.py

### _parse_list()
Arquivo: scripts/pipeline/hashing/hash_orchestrator.py
Linha: 16
Objetivo: Expandir lista de strings separadas por virgula.
Parâmetros: values: List[str] | None
Retorno: List[str]
Complexidade: O(n)

### _parse_csv_columns()
Arquivo: scripts/pipeline/hashing/hash_orchestrator.py
Linha: 25
Objetivo: Converter string CSV em lista.
Parâmetros: value: str
Retorno: List[str]
Complexidade: O(n)

### run_hash_orchestrator()
Arquivo: scripts/pipeline/hashing/hash_orchestrator.py
Linha: 29
Objetivo: Orquestrar normalize -> mapping -> apply com validacoes.
Parâmetros: args
Retorno: None
Exceções: ValueError se inputs obrigatorios ausentes
Complexidade: O(n)

## scripts/pipeline/consolidated_to_parquet/parquet_generation.py

### run_consolidated_to_parquet()
Arquivo: scripts/pipeline/consolidated_to_parquet/parquet_generation.py
Linha: 9
Objetivo: Delegar para processing.erg_dataset_extraction.run.
Parâmetros: args
Retorno: None

## scripts/pipeline/anonymize/anonymize_from_output.py

### _write_unknown_sexo_audit()
Arquivo: scripts/pipeline/anonymize/anonymize_from_output.py
Linha: 27
Objetivo: Escrever audit CSV de pacientes com sexo Unknown.
Parâmetros: annotations, reports_dir, run_tag
Retorno: None
Complexidade: O(n)

### _enrich_id_map_with_annotations()
Arquivo: scripts/pipeline/anonymize/anonymize_from_output.py
Linha: 45
Objetivo: Enriquecer id_map com anotacoes de patients_id_mapping.
Parâmetros: id_map_path, patients_root, reports_dir, run_tag
Retorno: None
Exceções: COMPORTAMENTO NÃO CONFIRMADO (parquet schema)
Complexidade: O(n)
Fluxo detalhado:
1) Localizar patients_id_mapping-*.parquet.
2) Concatenar colunas relevantes + ANNOTATE_COLS.
3) Normalizar patient_unique_id e derivar ano_nascimento.
4) Remover sexo Unknown (vira null) e escrever audit.
5) Join com id_map e salvar.

### _latest_match()
Arquivo: scripts/pipeline/anonymize/anonymize_from_output.py
Linha: 144
Objetivo: Escolher path mais recente por mtime.
Parâmetros: paths
Retorno: Path

### _discover_dataset()
Arquivo: scripts/pipeline/anonymize/anonymize_from_output.py
Linha: 148
Objetivo: Descobrir dataset por patterns (preferindo subdir).
Parâmetros: input_root, preferred_subdir, patterns, label
Retorno: Path
Exceções: FileNotFoundError

### _hashed_output_path_for_input()
Arquivo: scripts/pipeline/anonymize/anonymize_from_output.py
Linha: 167
Objetivo: Gerar nome curto do parquet hash de entrada.
Parâmetros: input_path, hashed_dir, name_suffix
Retorno: Path

### _load_cross_summary()
Arquivo: scripts/pipeline/anonymize/anonymize_from_output.py
Linha: 183
Objetivo: Ler summary do id_audit.
Parâmetros: summary_csv
Retorno: dict ou None
Exceções: COMPORTAMENTO NÃO CONFIRMADO

### _log_before_after_cross_validation()
Arquivo: scripts/pipeline/anonymize/anonymize_from_output.py
Linha: 205
Objetivo: Comparar counts de IDs antes/depois do hash.
Parâmetros: before_summary, after_summary
Retorno: None

### run()
Arquivo: scripts/pipeline/anonymize/anonymize_from_output.py
Linha: 234
Objetivo: Orquestrar fluxo anonymize completo.
Parâmetros: args
Retorno: None
Complexidade: O(n) + custos de hash/parquet
Fluxo detalhado:
1) Resolver input_root e output_root.
2) Descobrir datasets patients/metadata/waveforms.
3) Rodar audit before.
4) Gerar mapping de IDs (unique_ids_both_sources.csv) e aplicar hash.
5) Enriquecer id_map com anotacoes.
6) Gerar datasets finais com erg_dataset_extraction.
7) Rodar audit after e validar contagens.

### build_parser()
Arquivo: scripts/pipeline/anonymize/anonymize_from_output.py
Linha: 373
Objetivo: Construir argparse do anonymize.
Retorno: ArgumentParser

## scripts/pipeline/purge/purge_orphan_ids.py

### _read_audit_csv()
Arquivo: scripts/pipeline/purge/purge_orphan_ids.py
Linha: 81
Objetivo: Ler CSV de auditoria de IDs.
Parâmetros: path
Retorno: pd.DataFrame

### _ids_for_presence()
Arquivo: scripts/pipeline/purge/purge_orphan_ids.py
Linha: 85
Objetivo: Filtrar IDs por tipo de presenca.
Parâmetros: df, presence
Retorno: list[str]

### _presence_map()
Arquivo: scripts/pipeline/purge/purge_orphan_ids.py
Linha: 91
Objetivo: Mapear patient_unique_id -> presence.
Parâmetros: df
Retorno: dict[str, str]

### _find_parquet_targets()
Arquivo: scripts/pipeline/purge/purge_orphan_ids.py
Linha: 95
Objetivo: Encontrar parquets alvo por patterns.
Parâmetros: root, patterns
Retorno: list[Path]

### _is_spark_dir()
Arquivo: scripts/pipeline/purge/purge_orphan_ids.py
Linha: 104
Objetivo: Checar se path e diretorio (Spark output).
Parâmetros: path
Retorno: bool

### _extract_context()
Arquivo: scripts/pipeline/purge/purge_orphan_ids.py
Linha: 108
Objetivo: Extrair colunas de contexto para audit log.
Parâmetros: row
Retorno: dict

### _write_purge_log()
Arquivo: scripts/pipeline/purge/purge_orphan_ids.py
Linha: 112
Objetivo: Escrever purge_log CSV.
Parâmetros: records, log_path, dry_run
Retorno: None

### _purge_pyarrow()
Arquivo: scripts/pipeline/purge/purge_orphan_ids.py
Linha: 148
Objetivo: Remover IDs orfaos usando PyArrow.
Parâmetros: path, ids_to_remove, presence_map, dry_run
Retorno: list[PurgeRecord]
Complexidade: O(n)

### _build_spark()
Arquivo: scripts/pipeline/purge/purge_orphan_ids.py
Linha: 222
Objetivo: Criar SparkSession para purge.
Parâmetros: workers
Retorno: SparkSession

### _purge_spark()
Arquivo: scripts/pipeline/purge/purge_orphan_ids.py
Linha: 244
Objetivo: Remover IDs orfaos usando Spark.
Parâmetros: path, ids_to_remove, presence_map, spark, dry_run
Retorno: list[PurgeRecord]
Complexidade: O(n) + custos Spark

### run()
Arquivo: scripts/pipeline/purge/purge_orphan_ids.py
Linha: 303
Objetivo: Orquestrar purge em patients e waveforms.
Parâmetros: args
Retorno: None
Complexidade: O(n) + IO

### build_parser()
Arquivo: scripts/pipeline/purge/purge_orphan_ids.py
Linha: 377
Objetivo: Construir argparse.
Retorno: ArgumentParser

## scripts/pipeline/stage_runner.py

### stage_consolidate()
Arquivo: scripts/pipeline/stage_runner.py
Linha: 25
Objetivo: Executar patient_preparation + waveform_consolidation.
Parâmetros: args
Retorno: None

### stage_parquet()
Arquivo: scripts/pipeline/stage_runner.py
Linha: 60
Objetivo: Executar run_consolidated_to_parquet.
Parâmetros: args
Retorno: None

### stage_hash()
Arquivo: scripts/pipeline/stage_runner.py
Linha: 80
Objetivo: Executar run_hash_orchestrator.
Parâmetros: args
Retorno: None

### stage_consolidate_and_audit()
Arquivo: scripts/pipeline/stage_runner.py
Linha: 85
Objetivo: Executar consolidate_from_raw.
Parâmetros: args
Retorno: None

### stage_annotate()
Arquivo: scripts/pipeline/stage_runner.py
Linha: 90
Objetivo: Executar annotate_patient_mapping + audit_records_coverage.
Parâmetros: args
Retorno: None

### stage_purge()
Arquivo: scripts/pipeline/stage_runner.py
Linha: 106
Objetivo: Executar run_purge_orphan_ids.
Parâmetros: args
Retorno: None

### stage_anonymize()
Arquivo: scripts/pipeline/stage_runner.py
Linha: 111
Objetivo: Executar run_anonymize_from_output.
Parâmetros: args
Retorno: None

### build_parser()
Arquivo: scripts/pipeline/stage_runner.py
Linha: 116
Objetivo: Construir argparse com subparsers.
Retorno: ArgumentParser

### main()
Arquivo: scripts/pipeline/stage_runner.py
Linha: 414
Objetivo: Entrypoint do stage runner.
Retorno: None

## scripts/processing/erg_dataset_extraction.py

### find_latest_patients_file()
Arquivo: scripts/processing/erg_dataset_extraction.py
Linha: 68
Objetivo: Encontrar patients file mais recente.
Parâmetros: base_dir
Retorno: Path | None

### resolve_data_coleta()
Arquivo: scripts/processing/erg_dataset_extraction.py
Linha: 84
Objetivo: Gerar data YYYYMMDD atual.
Retorno: str

### load_dataframe()
Arquivo: scripts/processing/erg_dataset_extraction.py
Linha: 88
Objetivo: Ler parquet ou CSV com pandas.
Parâmetros: path
Retorno: pd.DataFrame

### write_waveforms_parquet_chunked()
Arquivo: scripts/processing/erg_dataset_extraction.py
Linha: 94
Objetivo: Ler waveforms e escrever parquet com waveform_type_id.
Parâmetros:
- input_path, parquet_path, drop_cols, block_size_mb, use_threads
Retorno: None
Exceções: ValueError se waveform_type ausente
Complexidade: O(n)
Fluxo detalhado:
1) Ler dataset em batches.
2) Mapear waveform_type para id.
3) Remover colunas sensiveis.
4) Escrever Parquet incremental.

### extract_features()
Arquivo: scripts/processing/erg_dataset_extraction.py
Linha: 153
Objetivo: Selecionar colunas de features no patients.
Parâmetros: df_patients
Retorno: pd.DataFrame
Exceções: ValueError se não houver colunas

### clean_metadata()
Arquivo: scripts/processing/erg_dataset_extraction.py
Linha: 163
Objetivo: Remover colunas sensiveis da metadata.
Parâmetros: df_metadata
Retorno: pd.DataFrame

### resolve_input_paths()
Arquivo: scripts/processing/erg_dataset_extraction.py
Linha: 168
Objetivo: Resolver paths de metadata, waveforms e patients.
Parâmetros: input_path
Retorno: (metadata_path, waveforms_path, patients_path)
Exceções: FileNotFoundError se não encontrar

### build_parser()
Arquivo: scripts/processing/erg_dataset_extraction.py
Linha: 223
Objetivo: Construir argparse.

### run()
Arquivo: scripts/processing/erg_dataset_extraction.py
Linha: 265
Objetivo: Orquestrar limpeza e geracao dos datasets finais.
Parâmetros: args
Retorno: None
Complexidade: O(n)
Fluxo detalhado:
1) Resolver input/output.
2) Ler metadata e patients.
3) Limpar metadata e extrair features.
4) Definir nomes de output.
5) Gerar waveform_types e waveforms parquet.
6) Escrever features CSV/Parquet.

### main()
Arquivo: scripts/processing/erg_dataset_extraction.py
Linha: 343
Objetivo: Entrypoint CLI.

## scripts/processing/erg_spectral_extraction.py

### resolve_latest_file()
Arquivo: scripts/processing/erg_spectral_extraction.py
Linha: 57
Objetivo: Selecionar ultimo arquivo por nome.

### resolve_preview_csv()
Arquivo: scripts/processing/erg_spectral_extraction.py
Linha: 64
Objetivo: Resolver preview CSV (preview2 ou preview legacy).

### resolve_waveform_inputs()
Arquivo: scripts/processing/erg_spectral_extraction.py
Linha: 74
Objetivo: Resolver waveforms/metadata/types e detectar modo preview.

### load_waveform_type_map()
Arquivo: scripts/processing/erg_spectral_extraction.py
Linha: 126
Objetivo: Mapear waveform_type_id -> waveform_type.

### setup_file_logging()
Arquivo: scripts/processing/erg_spectral_extraction.py
Linha: 142
Objetivo: Configurar log file em tmp/logs.

### validate_metadata_uniqueness()
Arquivo: scripts/processing/erg_spectral_extraction.py
Linha: 155
Objetivo: Detectar ambiguidade em dims (patient_unique_id, test_id).
Exceções: ValueError se strict

### read_metadata_dimensions_from_csv()
Arquivo: scripts/processing/erg_spectral_extraction.py
Linha: 183
Objetivo: Ler dims de metadata via CSV em chunks.
Exceções: RuntimeError se arquivo LFS pointer

### load_metadata_dimensions()
Arquivo: scripts/processing/erg_spectral_extraction.py
Linha: 207
Objetivo: Ler dims de metadata via Parquet ou CSV.

### is_lfs_pointer_csv()
Arquivo: scripts/processing/erg_spectral_extraction.py
Linha: 233
Objetivo: Detectar arquivo CSV como ponteiro Git LFS.

### resolve_signal()
Arquivo: scripts/processing/erg_spectral_extraction.py
Linha: 244
Objetivo: Resolver sinal (pupil ou voltage) por waveform_type_id.

### estimate_sampling_rate_hz()
Arquivo: scripts/processing/erg_spectral_extraction.py
Linha: 254
Objetivo: Estimar taxa de amostragem a partir de time_ms.

### preprocess_signal()
Arquivo: scripts/processing/erg_spectral_extraction.py
Linha: 268
Objetivo: Interpolar NaNs no sinal.

### extract_fft_features()
Arquivo: scripts/processing/erg_spectral_extraction.py
Linha: 276
Objetivo: Extrair energia e frequencias FFT.

### extract_welch_features()
Arquivo: scripts/processing/erg_spectral_extraction.py
Linha: 299
Objetivo: Extrair features via Welch.

### extract_wavelet_features()
Arquivo: scripts/processing/erg_spectral_extraction.py
Linha: 328
Objetivo: Extrair energia por nivel DWT e entropia.

### hash_bucket()
Arquivo: scripts/processing/erg_spectral_extraction.py
Linha: 368
Objetivo: Hash deterministico para bucketizacao.

### prepare_waveform_chunk()
Arquivo: scripts/processing/erg_spectral_extraction.py
Linha: 382
Objetivo: Preparar chunk com signal_value e dimensoes.
Exceções: ValueError se colunas ausentes

### write_bucket_rows()
Arquivo: scripts/processing/erg_spectral_extraction.py
Linha: 442
Objetivo: Escrever linhas por bucket CSV.

### log_waveform_sizes()
Arquivo: scripts/processing/erg_spectral_extraction.py
Linha: 482
Objetivo: Logar distribuicao de pontos por waveform.

### validate_time_order()
Arquivo: scripts/processing/erg_spectral_extraction.py
Linha: 497
Objetivo: Logar waveforms com time_ms desordenado.

### detect_time_gaps()
Arquivo: scripts/processing/erg_spectral_extraction.py
Linha: 504
Objetivo: Detectar gaps temporais.

### bucketize_waveforms()
Arquivo: scripts/processing/erg_spectral_extraction.py
Linha: 522
Objetivo: Bucketizar waveforms (Parquet) em CSVs temporarios.

### bucketize_waveforms_csv()
Arquivo: scripts/processing/erg_spectral_extraction.py
Linha: 571
Objetivo: Bucketizar waveforms (CSV) em CSVs temporarios.

### build_group_feature_row()
Arquivo: scripts/processing/erg_spectral_extraction.py
Linha: 607
Objetivo: Gerar linha de features para um grupo (patient_id, test_id, waveform_type,...).
Fluxo detalhado:
1) Ordenar por time_ms.
2) Validar time_ms e signal_value.
3) Estimar sampling_rate.
4) Extrair FFT, Welch, Wavelet.

### process_bucket_file()
Arquivo: scripts/processing/erg_spectral_extraction.py
Linha: 655
Objetivo: Processar bucket CSV e gerar lista de features.

### process_all_buckets()
Arquivo: scripts/processing/erg_spectral_extraction.py
Linha: 682
Objetivo: Paralelizar processamento de buckets.

### main()
Arquivo: scripts/processing/erg_spectral_extraction.py
Linha: 732
Objetivo: Entrypoint CLI da extracao espectral.

## scripts/processing/annotate_patient_mapping.py

### _find_mapping_files()
Arquivo: scripts/processing/annotate_patient_mapping.py
Linha: 80
Objetivo: Encontrar patients_id_mapping parquets.

### _read_parquet_polars()
Arquivo: scripts/processing/annotate_patient_mapping.py
Linha: 87
Objetivo: Ler parquet (diretorio ou arquivo).

### _write_parquet_inplace()
Arquivo: scripts/processing/annotate_patient_mapping.py
Linha: 91
Objetivo: Reescrever parquet inplace com tmp.

### _build_lookup()
Arquivo: scripts/processing/annotate_patient_mapping.py
Linha: 111
Objetivo: Construir lookup por prontuario e por nome.

### _build_metadata_name_lookup()
Arquivo: scripts/processing/annotate_patient_mapping.py
Linha: 136
Objetivo: Mapear patient_unique_id -> nome_paciente a partir de metadata.

### _match_row()
Arquivo: scripts/processing/annotate_patient_mapping.py
Linha: 151
Objetivo: Resolver match (prontuario, nome, fallback metadata).

### _resolve_sexo()
Arquivo: scripts/processing/annotate_patient_mapping.py
Linha: 192
Objetivo: Resolver sexo priorizando records e logando divergencia.

### _annotate_file()
Arquivo: scripts/processing/annotate_patient_mapping.py
Linha: 206
Objetivo: Anotar um mapping parquet e gerar audit_df.
Fluxo detalhado:
1) Ler mapping.
2) Para cada row, aplicar _match_row.
3) Construir colunas string e booleanas.
4) Remover colunas existentes e escrever inplace.
5) Gerar audit por patient_unique_id.

### run()
Arquivo: scripts/processing/annotate_patient_mapping.py
Linha: 285
Objetivo: Orquestrar anotacao de todos os mappings.

### build_parser()
Arquivo: scripts/processing/annotate_patient_mapping.py
Linha: 369
Objetivo: Construir argparse.

## scripts/processing/add_gender_to_patients.py

### build_parser()
Arquivo: scripts/processing/add_gender_to_patients.py
Linha: 22
Objetivo: Construir argparse.

### run()
Arquivo: scripts/processing/add_gender_to_patients.py
Linha: 32
Objetivo: Join de sexo por nome_completo e salvar parquet.

### main()
Arquivo: scripts/processing/add_gender_to_patients.py
Linha: 67
Objetivo: Entrypoint CLI.

## scripts/analysis/audit_unique_patient_ids.py

### _pick_latest_from_dir()
Arquivo: scripts/analysis/audit_unique_patient_ids.py
Linha: 60
Objetivo: Selecionar arquivo mais recente em um diretorio.

### resolve_dataset_path()
Arquivo: scripts/analysis/audit_unique_patient_ids.py
Linha: 69
Objetivo: Resolver path de dataset (arquivo ou diretorio).

### read_table()
Arquivo: scripts/analysis/audit_unique_patient_ids.py
Linha: 79
Objetivo: Ler parquet/csv com colunas candidatas.
Exceções: ValueError se colunas ausentes

### first_non_empty_series()
Arquivo: scripts/analysis/audit_unique_patient_ids.py
Linha: 102
Objetivo: Escolher primeira coluna nao vazia entre varias.

### non_empty_agg()
Arquivo: scripts/analysis/audit_unique_patient_ids.py
Linha: 114
Objetivo: Agregador que retorna primeiro valor não vazio.

### build_unique_identity_table()
Arquivo: scripts/analysis/audit_unique_patient_ids.py
Linha: 122
Objetivo: Gerar tabela unica por patient_unique_id.

### build_id_occurrence_counts()
Arquivo: scripts/analysis/audit_unique_patient_ids.py
Linha: 173
Objetivo: Contar ocorrencias de IDs.

### build_comparison_table()
Arquivo: scripts/analysis/audit_unique_patient_ids.py
Linha: 184
Objetivo: Comparar patients vs metadata (cross).

### build_before_after_table()
Arquivo: scripts/analysis/audit_unique_patient_ids.py
Linha: 212
Objetivo: Comparar before/after por dataset.

### build_parser()
Arquivo: scripts/analysis/audit_unique_patient_ids.py
Linha: 245
Objetivo: Construir argparse.

### _require_args()
Arquivo: scripts/analysis/audit_unique_patient_ids.py
Linha: 284
Objetivo: Validar args obrigatorios por modo.

### run_cross()
Arquivo: scripts/analysis/audit_unique_patient_ids.py
Linha: 291
Objetivo: Executar auditoria cross e salvar CSVs.

### run_before_after()
Arquivo: scripts/analysis/audit_unique_patient_ids.py
Linha: 400
Objetivo: Executar auditoria before/after e salvar CSVs.

### run()
Arquivo: scripts/analysis/audit_unique_patient_ids.py
Linha: 492
Objetivo: Roteamento por modo.

### main()
Arquivo: scripts/analysis/audit_unique_patient_ids.py
Linha: 503
Objetivo: Entrypoint CLI.

## scripts/analysis/audit_records_coverage.py

### _read_parquet()
Arquivo: scripts/analysis/audit_records_coverage.py
Linha: 55
Objetivo: Ler parquet (arquivo ou diretorio).

### _find_files()
Arquivo: scripts/analysis/audit_records_coverage.py
Linha: 59
Objetivo: Encontrar arquivos por patterns.

### _collect_base_prontuarios()
Arquivo: scripts/analysis/audit_records_coverage.py
Linha: 66
Objetivo: Coletar prontuarios das bases e deduplicar mapping.

### _select_available()
Arquivo: scripts/analysis/audit_records_coverage.py
Linha: 98
Objetivo: Selecionar colunas disponiveis.

### _write_report()
Arquivo: scripts/analysis/audit_records_coverage.py
Linha: 102
Objetivo: Escrever parquet/csv de report (ou dry-run).

### run()
Arquivo: scripts/analysis/audit_records_coverage.py
Linha: 111
Objetivo: Gerar relatórios de cobertura de records.

### build_parser()
Arquivo: scripts/analysis/audit_records_coverage.py
Linha: 239
Objetivo: Construir argparse.

## scripts/analysis/records_split.py

### _read_parquet()
Arquivo: scripts/analysis/records_split.py
Linha: 21
Objetivo: Ler parquet com PyArrow.

### _check_duplicate_columns()
Arquivo: scripts/analysis/records_split.py
Linha: 25
Objetivo: Logar colunas duplicadas.

### _write_output()
Arquivo: scripts/analysis/records_split.py
Linha: 33
Objetivo: Escrever parquet ou CSV de output.

### run()
Arquivo: scripts/analysis/records_split.py
Linha: 42
Objetivo: Executar cross-reference e split condicional.

### _build_parser()
Arquivo: scripts/analysis/records_split.py
Linha: 147
Objetivo: Construir argparse.

### main()
Arquivo: scripts/analysis/records_split.py
Linha: 186
Objetivo: Entrypoint CLI.

## scripts/analysis/dbscan_density.py

### parse_args()
Arquivo: scripts/analysis/dbscan_density.py
Linha: 46
Objetivo: Construir argparse.

### resolve_paths()
Arquivo: scripts/analysis/dbscan_density.py
Linha: 106
Objetivo: Resolver input/output paths.

### split_feature_columns()
Arquivo: scripts/analysis/dbscan_density.py
Linha: 121
Objetivo: Separar colunas numericas e categoricas.

### build_model_matrix()
Arquivo: scripts/analysis/dbscan_density.py
Linha: 135
Objetivo: Construir matriz de modelo com one-hot.

### nan_euclidean()
Arquivo: scripts/analysis/dbscan_density.py
Linha: 161
Objetivo: Distancia euclidiana ignorando NaN.

### log_mean_distance_distribution()
Arquivo: scripts/analysis/dbscan_density.py
Linha: 171
Objetivo: Logar distribuicao de distancias medias.

### run_dbscan()
Arquivo: scripts/analysis/dbscan_density.py
Linha: 195
Objetivo: Executar DBSCAN com distancia custom.

### plot_pca_clusters()
Arquivo: scripts/analysis/dbscan_density.py
Linha: 206
Objetivo: Plotar PCA 2D por cluster.

### summarize_clusters()
Arquivo: scripts/analysis/dbscan_density.py
Linha: 297
Objetivo: Gerar tabelas de resumo por cluster.

### run_density_clustering()
Arquivo: scripts/analysis/dbscan_density.py
Linha: 362
Objetivo: Particionar por waveform_type e executar DBSCAN.

### _transform()
Arquivo: scripts/analysis/dbscan_density.py
Linha: 409
Objetivo: Funcao local para normalizar strings de label.
Notas:
- Definida dentro de run_density_clustering.

### _name()
Arquivo: scripts/analysis/dbscan_density.py
Linha: 414
Objetivo: Funcao local para gerar nome padrao de coluna.
Notas:
- Definida dentro de run_density_clustering.

### _balance()
Arquivo: scripts/analysis/dbscan_density.py
Linha: 419
Objetivo: Funcao local para calcular proporcao por classe.
Notas:
- Definida dentro de run_density_clustering.

### _scorer()
Arquivo: scripts/analysis/dbscan_density.py
Linha: 424
Objetivo: Funcao local de scoring para distancias.
Notas:
- Definida dentro de run_density_clustering.

### save_outputs()
Arquivo: scripts/analysis/dbscan_density.py
Linha: 450
Objetivo: Salvar outputs CSVs e logar ruido global.

### main()
Arquivo: scripts/analysis/dbscan_density.py
Linha: 477
Objetivo: Entrypoint CLI.

## scripts/analysis/dbscan_sweep.py

### _init_sweep_worker()
Arquivo: scripts/analysis/dbscan_sweep.py
Linha: 43
Objetivo: Inicializar matriz global no worker.

### _run_combo_worker()
Arquivo: scripts/analysis/dbscan_sweep.py
Linha: 48
Objetivo: Rodar DBSCAN para um combo de eps/min_samples.

### parse_float_list()
Arquivo: scripts/analysis/dbscan_sweep.py
Linha: 80
Objetivo: Parsear lista de floats.

### parse_int_list()
Arquivo: scripts/analysis/dbscan_sweep.py
Linha: 92
Objetivo: Parsear lista de ints.

### parse_args()
Arquivo: scripts/analysis/dbscan_sweep.py
Linha: 104
Objetivo: Construir argparse.

### iter_partitions()
Arquivo: scripts/analysis/dbscan_sweep.py
Linha: 144
Objetivo: Iterar partições por waveform_type (ou + TestStepType).

### run_sweep()
Arquivo: scripts/analysis/dbscan_sweep.py
Linha: 185
Objetivo: Executar sweep e gerar by_waveform + global_df.

### main()
Arquivo: scripts/analysis/dbscan_sweep.py
Linha: 297
Objetivo: Entrypoint CLI.

## scripts/analysis/classification/data_prep.py

### filter_annotated()
Arquivo: scripts/analysis/classification/data_prep.py
Linha: 20
Objetivo: Filtrar registros anotados conforme regra.

### binarize_column()
Arquivo: scripts/analysis/classification/data_prep.py
Linha: 73
Objetivo: Binarizar coluna com parser custom.

### expand_multilabel_column()
Arquivo: scripts/analysis/classification/data_prep.py
Linha: 115
Objetivo: Expandir multilabel em colunas booleanas.

### join_label()
Arquivo: scripts/analysis/classification/data_prep.py
Linha: 166
Objetivo: Join de labels em features.

### aggregate_per_patient()
Arquivo: scripts/analysis/classification/data_prep.py
Linha: 195
Objetivo: Agregar por paciente para evitar leakage.

### split_train_test()
Arquivo: scripts/analysis/classification/data_prep.py
Linha: 234
Objetivo: Split train/test estratificado.

## scripts/analysis/classification/pipeline.py

### build_classification_pipeline()
Arquivo: scripts/analysis/classification/pipeline.py
Linha: 31
Objetivo: Construir pipeline sklearn (preprocess + model).

### nested_cv_select_hyperparams()
Arquivo: scripts/analysis/classification/pipeline.py
Linha: 78
Objetivo: Nested CV para selecao de hiperparametros (binary).

### nested_cv_multiclass()
Arquivo: scripts/analysis/classification/pipeline.py
Linha: 202
Objetivo: Nested CV para multi-classe.

### nested_cv_multilabel()
Arquivo: scripts/analysis/classification/pipeline.py
Linha: 315
Objetivo: Nested CV para multilabel.

## scripts/analysis/classification/evaluation.py

### log_class_balance()
Arquivo: scripts/analysis/classification/evaluation.py
Linha: 30
Objetivo: Logar distribuicao de classes.

### apply_smote_if_needed()
Arquivo: scripts/analysis/classification/evaluation.py
Linha: 71
Objetivo: Aplicar SMOTE se classe minoritaria abaixo do threshold.

### evaluate_model()
Arquivo: scripts/analysis/classification/evaluation.py
Linha: 109
Objetivo: Calcular metricas simples e classification_report.

### evaluate_binary_classifier()
Arquivo: scripts/analysis/classification/evaluation.py
Linha: 140
Objetivo: Calcular metricas padrao e opcionalmente retornar predicoes.

### plot_confusion_matrix_from_counts()
Arquivo: scripts/analysis/classification/evaluation.py
Linha: 229
Objetivo: Plotar matriz de confusao.

## scripts/analysis/classification/feature_importance.py

### run_feature_importance()
Arquivo: scripts/analysis/classification/feature_importance.py
Linha: 25
Objetivo: Calcular MDI e permutation importance.

## scripts/analysis/classification/persistence.py

### _run_dir()
Arquivo: scripts/analysis/classification/persistence.py
Linha: 26
Objetivo: Resolver diretoria de run.

### save_training_dataset()
Arquivo: scripts/analysis/classification/persistence.py
Linha: 38
Objetivo: Salvar datasets train/test com run_tag.

### save_model()
Arquivo: scripts/analysis/classification/persistence.py
Linha: 76
Objetivo: Salvar pipeline com joblib.

### save_predictions()
Arquivo: scripts/analysis/classification/persistence.py
Linha: 95
Objetivo: Salvar predicoes e metricas basicas.

### save_feature_importance()
Arquivo: scripts/analysis/classification/persistence.py
Linha: 130
Objetivo: Salvar feature importance.

## scripts/questionnaire/record_linkage.py

### _compute_all_fuzzy()
Arquivo: scripts/questionnaire/record_linkage.py
Linha: 84
Objetivo: Computar ratio/partial/token_sort/token_set e best via rapidfuzz.

### _score_from_best()
Arquivo: scripts/questionnaire/record_linkage.py
Linha: 113
Objetivo: Converter best fuzzy score em score parcial.

### _classify()
Arquivo: scripts/questionnaire/record_linkage.py
Linha: 127
Objetivo: Classificar par (query,candidato) com base em sinais.

### _build_reasons()
Arquivo: scripts/questionnaire/record_linkage.py
Linha: 181
Objetivo: Gerar lista de motivos explicaveis.

### _phase0_prontuario()
Arquivo: scripts/questionnaire/record_linkage.py
Linha: 245
Objetivo: Join prontuario mapping x RightEye.

### _sex_filter_nonelim()
Arquivo: scripts/questionnaire/record_linkage.py
Linha: 276
Objetivo: Filtrar por sexo sem eliminar se vazio.

### _build_name_filter_cond()
Arquivo: scripts/questionnaire/record_linkage.py
Linha: 283
Objetivo: Construir condicao Polars de nome.

### _build_pool()
Arquivo: scripts/questionnaire/record_linkage.py
Linha: 291
Objetivo: Construir pool de candidatos com blocking.

### _score_one()
Arquivo: scripts/questionnaire/record_linkage.py
Linha: 326
Objetivo: Calcular score para um candidato.

### _log_review()
Arquivo: scripts/questionnaire/record_linkage.py
Linha: 428
Objetivo: Logar bloco de revisao para MATCH_MULTIPLE/NO_MATCH.

### match_record()
Arquivo: scripts/questionnaire/record_linkage.py
Linha: 486
Objetivo: Resolver match de uma submissao.
Complexidade: O(n) no tamanho do pool
Fluxo detalhado:
1) Checar prontuario exato (fase0).
2) Construir pool por ano/nome/sexo.
3) Calcular fuzzy scores uma vez.
4) Ordenar e decidir MATCH_UNIQUE/MULTIPLE/NO_MATCH.

### _decide_phase()
Arquivo: scripts/questionnaire/record_linkage.py
Linha: 604
Objetivo: Derivar fase textual a partir de motivos.

### _load_questionnaire()
Arquivo: scripts/questionnaire/record_linkage.py
Linha: 621
Objetivo: Ler JSON do questionario.

### _write()
Arquivo: scripts/questionnaire/record_linkage.py
Linha: 626
Objetivo: Escrever parquet+csv se DataFrame não vazio.

### _process()
Arquivo: scripts/questionnaire/record_linkage.py
Linha: 638
Objetivo: Processar respostas e gerar outputs.
Fluxo detalhado:
1) Carregar respostas e tabelas base.
2) Para cada resposta, criar _Query e match_record.
3) Acumular outputs (confirmed, ambiguous, not_found, explain).
4) Escrever outputs e report.

### build_parser()
Arquivo: scripts/questionnaire/record_linkage.py
Linha: 893
Objetivo: Construir argparse.

### run()
Arquivo: scripts/questionnaire/record_linkage.py
Linha: 908
Objetivo: Resolver paths e chamar _process.

## scripts/visualization/parquet_preview.py

### resolve_input_files()
Arquivo: scripts/visualization/parquet_preview.py
Linha: 49
Objetivo: Resolver arquivos parquet em path.

### read_parquet_head()
Arquivo: scripts/visualization/parquet_preview.py
Linha: 57
Objetivo: Ler primeiras linhas de parquet por row_group.

### resolve_latest_file()
Arquivo: scripts/visualization/parquet_preview.py
Linha: 76
Objetivo: Selecionar ultimo arquivo por padrao.

### resolve_erg_dataset_files()
Arquivo: scripts/visualization/parquet_preview.py
Linha: 83
Objetivo: Resolver waveforms/metadata/features/waveform_types.

### pick_first_patients_from_waveforms()
Arquivo: scripts/visualization/parquet_preview.py
Linha: 116
Objetivo: Selecionar primeiros patient_unique_id do dataset.

### filter_parquet_by_patients()
Arquivo: scripts/visualization/parquet_preview.py
Linha: 133
Objetivo: Filtrar parquet por patient_unique_id.

### build_preview2()
Arquivo: scripts/visualization/parquet_preview.py
Linha: 150
Objetivo: Gerar preview2 com amostra de pacientes.

### main()
Arquivo: scripts/visualization/parquet_preview.py
Linha: 262
Objetivo: Entrypoint CLI.

## scripts/visualization/waveform_sample_plot.py

### parse_patient_ids()
Arquivo: scripts/visualization/waveform_sample_plot.py
Linha: 38
Objetivo: Parsear lista de IDs separados por virgula.

### resolve_latest_file()
Arquivo: scripts/visualization/waveform_sample_plot.py
Linha: 44
Objetivo: Selecionar ultimo arquivo por padrao.

### resolve_input_path()
Arquivo: scripts/visualization/waveform_sample_plot.py
Linha: 49
Objetivo: Resolver path para CSV/parquet ou diretorio.

### get_available_columns()
Arquivo: scripts/visualization/waveform_sample_plot.py
Linha: 75
Objetivo: Listar colunas disponiveis no input.

### iter_waveform_chunks()
Arquivo: scripts/visualization/waveform_sample_plot.py
Linha: 87
Objetivo: Iterar chunks de waveforms.

### pick_first_unique_patients()
Arquivo: scripts/visualization/waveform_sample_plot.py
Linha: 107
Objetivo: Selecionar primeiros pacientes unicos.

### collect_rows_for_patients()
Arquivo: scripts/visualization/waveform_sample_plot.py
Linha: 124
Objetivo: Coletar linhas para pacientes selecionados.

### downsample_points()
Arquivo: scripts/visualization/waveform_sample_plot.py
Linha: 176
Objetivo: Downsample de pontos.

### sanitize_for_filename()
Arquivo: scripts/visualization/waveform_sample_plot.py
Linha: 183
Objetivo: Sanitizar texto para filename.

### build_curve_label()
Arquivo: scripts/visualization/waveform_sample_plot.py
Linha: 187
Objetivo: Construir label de curva com chaves.

### plot_patient_waveforms()
Arquivo: scripts/visualization/waveform_sample_plot.py
Linha: 199
Objetivo: Plotar waveforms por paciente e salvar PNG.

### main()
Arquivo: scripts/visualization/waveform_sample_plot.py
Linha: 284
Objetivo: Entrypoint CLI.
