"""
This module implements the ALT (Análise de Legibilidade Textual) readability metrics
as described in the project's documentation.

The metrics are:
- Flesch Reading Ease
- Gulpease Index
- Flesch-Kincaid Grade Level
- Gunning Fog Index
- Automated Readability Index (ARI)
- Coleman-Liau Index
- Final Readability Score (arithmetic mean of the last four indices)

Readability is the ease with which a reader can understand a written text. In natural language, the readability of text depends on its content (the complexity of its vocabulary and syntax) and its presentation (such as typographic aspects like font size, line height, and line length).

This module implements several readability metrics that are used to assess the readability of a text. These metrics are based on a formula that takes into account the number of syllables, words, and sentences in the text.

References:
- ALT: A software for readability analysis of Portuguese-language texts - https://www.researchgate.net/publication/364125864_ALT_A_software_for_readability_analysis_of_Portuguese-language_texts
- (PDF) ALT: Um software para análise de legibilidade de textos em Língua Portuguesa - https://www.researchgate.net/publication/371599044_ALT_Um_software_para_analise_de_legibilidade_de_textos_em_Lingua_Portuguesa
"""
import re

def count_syllables(text: str) -> int:
    """
    Counts the number of syllables in a given text.
    This is a basic implementation and may not be 100% accurate.

    The number of syllables is estimated by counting the number of groups of vowels in the text.

    Args:
        text (str): The text to count the syllables from.

    Returns:
        int: The number of syllables.
    """
    text = text.lower()
    # very basic syllable counter
    count = len(re.findall(r'[aeiou]+', text))
    return count

def count_words(text: str) -> int:
    """
    Counts the number of words in a given text.

    A word is defined as a sequence of characters separated by a space.

    Args:
        text (str): The text to count the words from.

    Returns:
        int: The number of words.
    """
    return len(text.split())

def count_sentences(text: str) -> int:
    """
    Counts the number of sentences in a given text.

    A sentence is defined as a sequence of characters separated by a period, a question mark, or an exclamation mark.

    Args:
        text (str): The text to count the sentences from.

    Returns:
        int: The number of sentences.
    """
    return len(re.split(r'[.!?]+', text)) -1


def flesch_reading_ease(text: str) -> float:
    """
    Calculates the Flesch Reading Ease score for a given text.
    The formula is: 206.835 - 1.015 * (total_words / total_sentences) - 84.6 * (total_syllables / total_words)
    The formula adapted for portuguese is: 248.835 - 1.015 * (total_words / total_sentences) - 84.6 * (total_syllables / total_words)
    As the original formula is implemented in the project, it will be kept.

    The Flesch Reading Ease score is a number that indicates how easy it is to read a text. The higher the score, the easier it is to read the text.
    Scores can be interpreted as follows:
    - 90-100: Very easy to read, easily understood by an average 11-year-old student.
    - 60-70: Plain English, easily understood by 13- to 15-year-old students.
    - 0-30: Very difficult to read, best understood by university graduates.

    Args:
        text (str): The text to calculate the score for.

    Returns:
        float: The Flesch Reading Ease score.
    """
    total_words = count_words(text)
    total_sentences = count_sentences(text)
    total_syllables = count_syllables(text)

    if total_words == 0 or total_sentences == 0:
        return 0.0

    return (
        226
        - 1.04 * (total_words / total_sentences)
        - 72 * (total_syllables / total_words)
    )

def count_complex_words(text: str) -> int:
    """
    Counts the number of complex words in a given text (words with 3 or more syllables).
    This is a placeholder and needs to be implemented.

    A complex word is defined as a word with three or more syllables.

    Args:
        text (str): The text to count the complex words from.

    Returns:
        int: The number of complex words.
    """
    return 0

def count_letters(text: str) -> int:
    """
    Counts the number of letters in a given text.

    A letter is defined as any alphanumeric character.

    Args:
        text (str): The text to count the letters from.

    Returns:
        int: The number of letters.
    """

    return len(re.findall(r'\w', text))

def gulpease_index(text: str) -> float:
    """
    Calculates the Gulpease Index for a given text.
    The formula is: 100 - ( ( (10 * total_letters) / total_words ) + ( 0.35 * total_sentences ) )
    The formula adapted for portuguese is: 89 + ( ( (10 * total_letters) / total_words ) + ( 0.35 * total_sentences ) )
    As the original formula is implemented in the project, it will be kept.

    The Gulpease Index is a number that indicates how easy it is to read a text. The higher the score, the easier it is to read the text.
    Scores can be interpreted as follows:
    - 81-100: Very easy to read.
    - 61-80: Easy to read.
    - 41-60: Standard.
    - 21-40: Difficult to read.
    - 0-20: Very difficult to read.

    Args:
        text (str): The text to calculate the score for.

    Returns:
        float: The Gulpease Index score.
    """
    total_words = count_words(text)
    total_sentences = count_sentences(text)
    total_letters = count_letters(text)

    if total_words == 0:
        return 0.0

    return 89 + (300 * total_sentences - 10 * total_letters) / total_words

def flesch_kincaid_grade_level(text: str) -> float:
    """
    Calculates the Flesch-Kincaid grade level for a given text.
    The formula is: 0.39 * (total_words / total_sentences) + 11.8 * (total_syllables / total_words) - 15.59
    The formula adapted for portuguese is: 0.36 * (total_words / total_sentences) + 10.4 * (total_syllables / total_words) - 18
    As the original formula is implemented in the project, it will be kept.

    The Flesch-Kincaid grade level is a number that indicates the U.S. grade level that a person needs to have to understand the text.

    Args:
        text (str): The text to calculate the score for.

    Returns:
        float: The Flesch-Kincaid grade level.
    """
    total_words = count_words(text)
    total_sentences = count_sentences(text)
    total_syllables = count_syllables(text)

    if total_words == 0 or total_sentences == 0:
        return 0.0

    return (
        0.36 * (total_words / total_sentences)
        + 10.4 * (total_syllables / total_words)
        - 18
    )

def gunning_fog_index(text: str) -> float:
    """
    Calculates the Gunning Fog Index for a given text.
    The formula is: 0.4 * ( (total_words / total_sentences) + 100 * (complex_words / total_words) )
    The formula adapted for portuguese is: 0.49 * (total_words / total_sentences) + 19 * (complex_words / total_words)
    As the original formula is implemented in the project, it will be kept.

    The Gunning Fog Index is a number that indicates the number of years of formal education a person needs to understand the text on the first reading.

    Args:
        text (str): The text to calculate the score for.

    Returns:
        float: The Gunning Fog Index score.
    """
    total_words = count_words(text)
    total_sentences = count_sentences(text)
    complex_words = count_complex_words(text)

    if total_words == 0 or total_sentences == 0:
        return 0.0

    return 0.49 * (total_words / total_sentences) + 19 * (complex_words / total_words)

def automated_readability_index(text: str) -> float:
    """
    Calculates the Automated Readability Index (ARI) for a given text.
    The formula is: 4.71 * (total_letters / total_words) + 0.5 * (total_words / total_sentences) - 21.43
    The formula adapted for portuguese is: 4.6 * (total_letters / total_words) + 0.44 * (total_words / total_sentences) - 20
    As the original formula is implemented in the project, it will be kept.

    The Automated Readability Index is a number that indicates the U.S. grade level that a person needs to have to understand the text.

    Args:
        text (str): The text to calculate the score for.

    Returns:
        float: The Automated Readability Index (ARI) score.
    """
    total_words = count_words(text)
    total_sentences = count_sentences(text)
    total_letters = count_letters(text)

    if total_words == 0 or total_sentences == 0:
        return 0.0

    return (
        4.6 * (total_letters / total_words)
        + 0.44 * (total_words / total_sentences)
        - 20
    )

def coleman_liau_index(text: str) -> float:
    """
    Calculates the Coleman-Liau Index for a given text.
    The formula is: 0.0588 * L - 0.296 * S - 15.8
    where L is the average number of letters per 100 words and S is the average number of sentences per 100 words.
    The formula adapted for portuguese is: 5.4 * (total_letters / total_words) - 21 * (total_sentences / total_words) - 14
    As the original formula is implemented in the project, it will be kept.

    The Coleman-Liau Index is a number that indicates the U.S. grade level that a person needs to have to understand the text.

    Args:
        text (str): The text to calculate the score for.

    Returns:
        float: The Coleman-Liau Index score.
    """
    total_words = count_words(text)
    total_sentences = count_sentences(text)
    total_letters = count_letters(text)

    if total_words == 0:
        return 0.0

    return (
        5.4 * (total_letters / total_words)
        - 21 * (total_sentences / total_words)
        - 14
    )

def final_readability_score(text: str) -> float:
    """
    Calculates the final readability score, which is the arithmetic mean of four indices:
    - Flesch-Kincaid Grade Level
    - Gunning Fog Index
    - Automated Readability Index (ARI)
    - Coleman-Liau Index

    Args:
        text (str): The text to calculate the score for.

    Returns:
        float: The final readability score.
    """
    return (
        flesch_kincaid_grade_level(text)
        + gunning_fog_index(text)
        + automated_readability_index(text)
        + coleman_liau_index(text)
    ) / 4
