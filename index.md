## Instrumentos de Pesquisa sobre Neurodivergência e Hipersensibilidade Visual

<p style="text-align: justify;">Este repositório reúne os artefatos produzidos ao longo da pesquisa: (1) uma pipeline de processamento e classificação de dados de Eletrorretinograma (ERG) para predição de neurodivergência; (2) um framework de avaliação de 25 traduções do questionário CHYPS-V (Cardiff Hypersensitivity Scale, Visual) para o Português Brasileiro; e (3) o código fonte do sistema NeuroVision, utilizado para criação, distribuição e coleta de respostas do questionário CHYPS-BR.</p>

### Componentes

#### [erg-analysis](https://github.com/icecilia007/neurovision-research/tree/master/erg-analysis)

Pipeline de processamento e classificação de dados de Eletrorretinograma (ERG) para predição de neurodivergência.

- Pipeline completa de consolidação, anonimização e extração de features dos exames RETeval
- Modelos de classificação multi label (Decision Tree, Random Forest) com validação cruzada aninhada
- Notebook final com análise completa e figuras do TCC

**Dataset público:** [`classification_dataset.parquet`](https://github.com/icecilia007/neurovision-research/blob/master/erg-analysis/data/classification_dataset.parquet), dataset pré processado e anonimizado, pronto para reproduzir os resultados de classificação.

Os demais dados da pesquisa (brutos e intermediários) não são disponibilizados publicamente em cumprimento à LGPD. Para solicitar acesso, entre em contato via icsbarbosa@sga.pucminas.br ou izabelaengineer@gmail.com.

#### [cardiff-translation](https://github.com/icecilia007/neurovision-research/tree/master/cardiff-translation)

Framework de avaliação de 25 traduções do questionário CHYPS-V para o Português Brasileiro.

- Avaliação por métricas de legibilidade (ALT) e similaridade semântica (BERTScore, COMET)
- 25 modelos avaliados, sendo 12 proprietários, 9 de pesos abertos, 3 ferramentas de tradução especializada e 1 tradutor humano
- Modelo selecionado: Deepseek v3.2 deepthink (métrica composta de 0,7452)

#### [holhos-project](https://github.com/icecilia007/neurovision-research/tree/master/holhos-project)

Código fonte do [NeuroVision](https://neurovision.me/questionnaire/Mw/respond), sistema web para criação, distribuição e coleta de respostas do questionário CHYPS-BR.

- Frontend em Python com NiceGUI
- Backend em Python com FastAPI
- Banco de dados PostgreSQL 15 via Docker Compose

#### [OutrosInstrumentos](https://github.com/icecilia007/neurovision-research/tree/master/OutrosInstrumentos)

Documentos complementares da pesquisa.

### Autores e Orientadores

| Papel | Nome | E-mail | ORCID |
|:------|:-----|:-------|:------|
| Autora | Izabela Cecilia Silva Barbosa | izabelaengineer@gmail.com | [0009-0007-6514-8515](https://orcid.org/0009-0007-6514-8515) |
| Orientador | Cleiton Silva Tavares | cleitontavares@pucminas.br | [0009-0008-4235-409X](https://orcid.org/0009-0008-4235-409X) |
| Orientador | Hugo Bastos de Paula | hugodepaula@gmail.com | [0000-0002-6193-3205](https://orcid.org/0000-0002-6193-3205) |
| Orientador | Jerome Baron | jerome.baron.ufmg@gmail.com | [0000-0002-3809-7835](https://orcid.org/0000-0002-3809-7835) |
| Orientador | Ricardo Queiroz Guimarães | rg2020@gmail.com | [0000-0001-7600-855X](https://orcid.org/0000-0001-7600-855X) |

#### Instituição

PUC Minas, Engenharia de Software, 2025/2

#### Como citar

Se você usar este repositório em sua pesquisa, utilize a citação disponível no arquivo [`CITATION.cff`](https://github.com/icecilia007/neurovision-research/blob/master/CITATION.cff) ou clique em "Cite this repository" no GitHub.

Licenciado sob [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

## Referências

As principais referências utilizadas no desenvolvimento da pesquisa e dos artefatos deste repositório são apresentadas abaixo.

1. Adithya PC, Alaql A, Tzekov R, Sankar R, Moreno WA. Model based photopic electroretinogram source separation: A multiresolution analysis approach. In: 2017 International Caribbean Conference on Devices, Circuits and Systems (ICCDCS); 2017. p. 21-24. doi: [10.1109/ICCDCS.2017.7959700](https://doi.org/10.1109/ICCDCS.2017.7959700).

2. Constable PA, Pinzon-Arenas JO, Mercado Diaz LR, Lee IO, Marmolejo-Ramos F, Loh L, et al. Spectral Analysis of Light-Adapted Electroretinograms in Neurodevelopmental Disorders: Classification with Machine Learning. Bioengineering. 2025;12(1):15. doi: [10.3390/bioengineering12010015](https://doi.org/10.3390/bioengineering12010015).

3. Constable PA, Ritvo ER, Ritvo AR, Lee IO, McNair ML, Stahl D, et al. Light-Adapted Electroretinogram Differences in Autism Spectrum Disorder. J Autism Dev Disord. 2020;50(8):2874-2885. doi: [10.1007/s10803-020-04396-5](https://doi.org/10.1007/s10803-020-04396-5).

4. Choi H, Hong J, Kang HG, Park MH, Ha S, Lee J, et al. Retinal fundus imaging as biomarker for ADHD using machine learning for screening and visual attention stratification. npj Digit Med. 2025;8(1):164. doi: [10.1038/s41746-025-01547-9](https://doi.org/10.1038/s41746-025-01547-9).

5. Demmin DL, Davis Q, Roché M, Silverstein SM. Electroretinographic anomalies in schizophrenia. J Abnorm Psychol. 2018;127(4):417-428.

6. Dubois MA, Pelletier CA, Mérette C, Jomphe V, Turgeon R, Bélanger RE, et al. Evaluation of electroretinography (ERG) parameters as a biomarker for ADHD. Prog Neuropsychopharmacol Biol Psychiatry. 2023;127:110807. doi: [10.1016/j.pnpbp.2023.110807](https://doi.org/10.1016/j.pnpbp.2023.110807).

7. Albasu FB, Kulyabin M, Zhdanov A, Dolganov A, Borisov V, Ronkin M. ERG Classification by Using ML Methods Based on Short-Time Fourier Transform. In: 2024 IEEE Ural-Siberian Conference on Biomedical Engineering, Radioelectronics and Information Technology (USBEREIT); 2024. p. 318-321. doi: [10.1109/USBEREIT61901.2024.10583978](https://doi.org/10.1109/USBEREIT61901.2024.10583978).

8. Albasu FB, Dey S, Dolganov AY, Hamzaoui OE, Mustafa WM, Zhdanov AE. OculusGraphy: Description and Time Domain Analysis of Full-Field Electroretinograms Database. In: 2023 IEEE Ural-Siberian Conference on Biomedical Engineering, Radioelectronics and Information Technology (USBEREIT); 2023. p. 64-67. doi: [10.1109/USBEREIT58508.2023.10158887](https://doi.org/10.1109/USBEREIT58508.2023.10158887).

9. Agrawal M, Hegselmann S, Lang H, Kim Y, Sontag D. Large language models are few-shot clinical information extractors. In: Proceedings of the 2022 Conference on Empirical Methods in Natural Language Processing; 2022. p. 1998-2022. doi: [10.18653/v1/2022.emnlp-main.130](https://doi.org/10.18653/v1/2022.emnlp-main.130).

10. Moreau I, Hébert M, Maziade M, Painchaud A, Mérette C. The Electroretinogram as a Potential Biomarker of Psychosis in Children at Familial Risk. Schizophr Bull Open. 2022;3(1):sgac016. doi: [10.1093/schizbullopen/sgac016](https://doi.org/10.1093/schizbullopen/sgac016).

11. Price A, Sumner P, Powell G. The subtypes of visual hypersensitivity are transdiagnostic across neurodivergence, neurology and mental health. Vision Res. 2025;234:108640. doi: [10.1016/j.visres.2025.108640](https://doi.org/10.1016/j.visres.2025.108640).

12. Price A, Sumner P, Powell G. Understanding the subtypes of visual hypersensitivity: Four coherent factors and their measurement with the Cardiff Hypersensitivity Scale (CHYPS). Vision Res. 2025;233:108610. doi: [10.1016/j.visres.2025.108610](https://doi.org/10.1016/j.visres.2025.108610).

13. Posada-Quintero HF, Manjur SM, Hossain MB, Marmolejo-Ramos F, Lee IO, Skuse DH, et al. Autism spectrum disorder detection using variable frequency complex demodulation of the electroretinogram. Res Autism Spectr Disord. 2023;109:102258. doi: [10.1016/j.rasd.2023.102258](https://doi.org/10.1016/j.rasd.2023.102258).

14. Gu Y, Tinn R, Cheng H, Lucas M, Usuyama N, Liu X, et al. Domain-Specific Language Model Pretraining for Biomedical Natural Language Processing. ACM Trans Comput Healthcare. 2021;3(1):2. doi: [10.1145/3458754](https://doi.org/10.1145/3458754).

15. Feng Y. Semantic Textual Similarity Analysis of Clinical Text in the Era of LLM. In: 2024 IEEE Conference on Artificial Intelligence (CAI); 2024. p. 1284-1289. doi: [10.1109/CAI59869.2024.00227](https://doi.org/10.1109/CAI59869.2024.00227).

16. Simão L, Lana-Peixoto M, Abrantes C, Moreira M, Teixeira A. The Brazilian version of the 25-Item National Eye Institute Visual Function Questionnaire: Translation, reliability and validity. Arq Bras Oftalmol. 2008;71:540-546. doi: [10.1590/S0004-27492008000400014](https://doi.org/10.1590/S0004-27492008000400014).

17. McCarty P, Frye RE. Early Detection and Diagnosis of Autism Spectrum Disorder: Why Is It So Difficult? Semin Pediatr Neurol. 2020;35:100831. doi: [10.1016/j.spen.2020.100831](https://doi.org/10.1016/j.spen.2020.100831).

18. Han L, Gladkoff S, Erofeev G, Sorokina I, Galiano B, Nenadic G. Neural machine translation of clinical text: an empirical investigation into multilingual pre-trained language models and transfer-learning. Front Digit Health. 2024;6:1211564.

19. Souza MPM, Moreno GCL, Hein N, Kroenke A. ALT - Análise de Legibilidade Textual. 2021. Disponível em: https://legibilidade.com/. Acesso em: 09 jun. 2026.

20. Zhang T, Kishore V, Wu F, Weinberger KQ, Artzi Y. BERTScore: Evaluating Text Generation with BERT. International Conference on Learning Representations (ICLR). 2020.

21. Rei R, Stewart C, Farinha AC, Lavie A. COMET: A Neural Framework for MT Evaluation. Proceedings of the 2020 Conference on Empirical Methods in Natural Language Processing (EMNLP). 2020. p. 2685-2702. doi: [10.18653/v1/2020.emnlp-main.213](https://doi.org/10.18653/v1/2020.emnlp-main.213).

22. Robson AG, Frishman LJ, Grigg J, Hamilton R, Jeffrey BG, Kondo M, et al. ISCEV Standard for full-field clinical electroretinography (2022 update). Doc Ophthalmol. 2022;144(3):165-177. doi: [10.1007/s10633-022-09872-0](https://doi.org/10.1007/s10633-022-09872-0).

23. Kato K, Kondo M, Sugimoto M, Ikesugi K, Matsubara H. Effect of Pupil Size on Flicker ERGs Recorded With RETeval System: New Mydriasis-Free Full-Field ERG System. Invest Ophthalmol Vis Sci. 2015;56(6):3684-3690. doi: [10.1167/iovs.14-16349](https://doi.org/10.1167/iovs.14-16349).

24. Hébert M, Mérette C, Gagné AM, Paccalet T, Moreau I, Lavoie J, et al. The Electroretinogram May Differentiate Schizophrenia From Bipolar Disorder. Biol Psychiatry. 2020;87(3):263-270. doi: [10.1016/j.biopsych.2019.06.014](https://doi.org/10.1016/j.biopsych.2019.06.014).

25. Chicco D, Jurman G. The advantages of the Matthews correlation coefficient (MCC) over F1 score and accuracy in binary classification evaluation. BMC Genomics. 2020;21(1):6. doi: [10.1186/s12864-019-6413-7](https://doi.org/10.1186/s12864-019-6413-7).

26. Wilkinson MD, Dumontier M, Aalbersberg IJJ, Appleton G, Axton M, Baak A, et al. The FAIR Guiding Principles for scientific data management and stewardship. Sci Data. 2016;3:160018. doi: [10.1038/sdata.2016.18](https://doi.org/10.1038/sdata.2016.18).

27. Sounderajah V, Guni A, Liu X, Collins GS, Karthikesalingam A, Markar SR, et al. The STARD-AI reporting guideline for diagnostic accuracy studies using artificial intelligence. Nat Med. 2025;31:3283-3289. doi: [10.1038/s41591-025-03953-8](https://doi.org/10.1038/s41591-025-03953-8).

28. Nunnally JC, Bernstein IH. Psychometric Theory. 3rd ed. New York: McGraw-Hill; 1994.

29. Pedregosa F, et al. Scikit-learn: Machine Learning in Python. J Mach Learn Res. 2011;12:2825-2830.

30. Wohlin C, Runeson P, Höst M, Ohlsson MC, Regnell B, Wesslén A. Experimentation in Software Engineering. Berlin, Heidelberg: Springer; 2012. doi: [10.1007/978-3-642-29044-2](https://doi.org/10.1007/978-3-642-29044-2).

31. IBGE. Censo 2022 identifica 2,4 milhões de pessoas diagnosticadas com autismo no Brasil. 2025. Disponível em: https://agenciadenoticias.ibge.gov.br/agencia-noticias/2012-agencia-de-noticias/noticias/43464-censo-2022-identifica-2-4-milhoes-de-pessoas-diagnosticadas-com-autismo-no-brasil. Acesso em: 20 set. 2025.

32. UOL VivaBem. Autismo em adultos: 'Diagnóstico veio aos 50 e trouxe alívio'. 2022. Disponível em: https://www.uol.com.br/vivabem/noticias/redacao/2022/11/26/a-importancia-do-diagnostico-mesmo-que-tardio-do-autismo.htm. Acesso em: 20 set. 2025.

33. Terra. TDAH: cresce no Brasil o número de diagnósticos em adultos. 2025. Disponível em: https://www.terra.com.br/vida-e-estilo/saude/tdah-cresce-no-brasil-o-numero-de-diagnosticos-em-adultos,ad87b45504404dd4d2f13054fd05a2409igu4foa.html. Acesso em: 20 set. 2025.

34. EBSERH. TDAH em adultos: diagnóstico e tratamento para uma vida mais equilibrada. 2025. Disponível em: https://www.gov.br/ebserh/pt-br/hospitais-universitarios/regiao-nordeste/hu-univasf/comunicacao/noticias/tdah-em-adultos-diagnostico-e-tratamento-para-uma-vida-mais-equilibrada. Acesso em: 20 set. 2025.

35. Revista Pesquisa FAPESP. Não tratado, o transtorno bipolar é uma doença progressiva, afirma o psiquiatra Flávio Kapczinski. 2024. Disponível em: https://revistapesquisa.fapesp.br/nao-tratado-o-transtorno-bipolar-e-uma-doenca-progressiva-afirma-o-psiquiatra-flavio-kapczinski/. Acesso em: 20 set. 2025.

36. Carceres PCP, Covre P. Impacto do diagnóstico precoce e tardio da dislexia --- compreendendo esse transtorno. Rev Psicopedagogia. 2018;35(108).

