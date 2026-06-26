# Análise de Legibilidade Textual com o ALT

> Transcrição do background metodológico da ferramenta [ALT — Análise de Legibilidade Textual](https://legibilidade.com/sobre), mantida em inglês por ser síntese da documentação original.

---

# Textual Legibility Analysis with ALT

## Background

The followin Background is a summary of the ALT Tool (Análise de Legibilidade Textual). You can find more details about this on the [Legibilidade website](https://legibilidade.com/sobre).

"ALT - Análise de Legibilidade Textual" offers readability indices for Portuguese texts. These indices are calculated using formulas adapted from English. The algorithm processes texts by counting letters, syllables, words, sentences, and complex words to apply known readability formulas.

Readability indices assess how difficult a text is to read, primarily based on sentence length and word complexity. Word complexity is measured differently by various indices; for instance, the Automated Readability Index and Coleman-Liau use average word length in letters, while Flesch-Kincaid and Gunning Fog Index use syllable count. Some metrics also infer complexity from word frequency.

The indices use two main scales:

* **0-100 scale:** Where 100 indicates very simple text.
* **0-20 scale:** Where the number represents the years of study required for comprehension (lower numbers mean simpler text).

The following formulas, adapted for Portuguese with coefficients derived from multiple linear regression on a dataset of 100 diverse texts, are used:

**Flesch reading ease:**

    `226 − 1.04 × (Number of words / Number of sentences) − 72 × (Number of syllables / Number of words)`

**Gulpease Index:**

    `89 + 300 × (Number of sentences) − 10 × (Number of letters) / Number of words`

    (This index did not require coefficient changes for Portuguese.)

**Flesch-Kincaid grade level:**

    `0.36 × (Number of words / Number of sentences) + 10.4 × (Number of syllables / Number of words) − 18`

**Adapted Gunning fog index:**

    `0.49 × (Number of words / Number of sentences) + 19 × (Number of complex words / Number of words)`

    ("Complex words" are defined here as words not among the 5,000 most frequent words in Brazilian Portuguese, instead of being based on syllable count.)

**Automated readability index (ARI):**

    `4.6 × (Number of letters / Number of words) + 0.44 × (Number of words / Number of sentences) − 20`

**Coleman-Liau index:**

    `5.4 × (Number of letters / Number of words) − 21 × (Number of sentences / Number of words) − 14`

**Final readability score:**

The final readability score provided by the site is the arithmetic mean of four indices from the 0-20 scale:

    `Final Formula = (Flesch-Kincaid + Gunning fog + ARI + Coleman-Liau) / 4`

The article also notes the limitations of these indices, stating that they do not measure cohesion or coherence. It also warns that oversimplifying text to achieve a better score might compromise content quality, particularly in scientific texts where specialized terminology is often necessary. The page includes examples of texts with their calculated readability indices and a Pearson correlation table for the different indices.

## Methods

ALT Tool was run for each text file with the following parameters:

1. Consider as new sentences all those:

    * **Ended by a semicolon (;) and followed by a new line.**
    * **Ended by a colon (:) and followed by a new line.**

2. Remove from the word count:

    * **Prepositions**
    * **Articles, articles + pronouns, and articles + prepositions**
    * **Pronouns**

