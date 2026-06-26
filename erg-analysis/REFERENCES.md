# Referências — erg-analysis

## Baseline de classificação ERG

### Constable et al. 2025

Constable, P. A., Pinzon-Arenas, J. O., Mercado Diaz, L. R., Lee, I. O., Marmolejo-Ramos, F., Loh, L., Zhdanov, A., Kulyabin, M., Brabec, M., Skuse, D. H., Thompson, D. A., & Posada-Quintero, H. (2025). Spectral Analysis of Light-Adapted Electroretinograms in Neurodevelopmental Disorders: Classification with Machine Learning. *Bioengineering*, 12(1), 15.
- DOI: [10.3390/bioengineering12010015](https://doi.org/10.3390/bioengineering12010015)
- PMC (acesso aberto): [PMC11761560](https://pmc.ncbi.nlm.nih.gov/articles/PMC11761560/)
- Resultados de referência: BA = 0,87 (binário ASD vs. controle, apenas homens), BA = 0,53 (4 grupos: ASD/TDAH/controle)
- Usado como baseline no Passo 7 do notebook de classificação

---

## Dispositivo ERG

### RETeval (LKC Technologies)

O dispositivo utilizado para coleta dos exames ERG é o **RETeval** (LKC Technologies), um eletrorretinógrafo portátil que gera arquivos CSV com as formas de onda por protocolo de estimulação.

- Fabricante: [https://www.lkctechnologies.com/reteval](https://www.lkctechnologies.com/reteval)

---

## Metodologia de classificação

### Nested Cross-Validation

Cawley, G. C., & Talbot, N. L. C. (2010). On over-fitting in model selection and subsequent selection bias in performance evaluation. *Journal of Machine Learning Research*, 11, 2079–2107.
- URL: [https://jmlr.org/papers/v11/cawley10a.html](https://jmlr.org/papers/v11/cawley10a.html)

### Random Forest

Breiman, L. (2001). Random Forests. *Machine Learning*, 45(1), 5–32.
- DOI: [10.1023/A:1010933404324](https://doi.org/10.1023/A:1010933404324)

### Decision Tree (CART)

Breiman, L., Friedman, J. H., Olshen, R. A., & Stone, C. J. (1984). *Classification and Regression Trees*. Wadsworth & Brooks/Cole.

### scikit-learn

Pedregosa, F., et al. (2011). Scikit-learn: Machine learning in Python. *Journal of Machine Learning Research*, 12, 2825–2830.
- URL: [https://jmlr.org/papers/v12/pedregosa11a.html](https://jmlr.org/papers/v12/pedregosa11a.html)
- Repositório: [https://github.com/scikit-learn/scikit-learn](https://github.com/scikit-learn/scikit-learn)

---

## Proteção de dados

### Lei Geral de Proteção de Dados Pessoais (LGPD)

Lei nº 13.709, de 14 de agosto de 2018. *Lei Geral de Proteção de Dados Pessoais (LGPD)*. Presidência da República, Brasil.
- Texto integral: [https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm)

---

## Sobre o acesso aos dados

Os dados brutos e intermediários desta pesquisa não são disponibilizados publicamente em cumprimento à LGPD. Para solicitar acesso mediante justificativa, entre em contato via **icsbarbosa@sga.pucminas.br** ou **izabelaengineer@gmail.com**.
