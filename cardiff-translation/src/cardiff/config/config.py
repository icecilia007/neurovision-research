"""
This module contains the configuration for the project.

It defines two classes:
- Config: The default configuration for the project.
- QuestionsOnlyConfig: The configuration for the "questions-only" dataset.

The configuration classes are used to store the paths to the data and results files.
"""

from dataclasses import dataclass


@dataclass
class Config:
    """
    Configuration class for the project.

    This class stores the default paths to the data and results files.

    Attributes:
        original_text_path (str): The path to the original text file.
        translations_path (str): The path to the directory containing the translated text files.
        output_path (str): The path to the directory where the results will be saved.
        human_translation_filename (str): The filename of the human translation file.
    """

    original_text_path: str = "docs/CHYPS-V-plain-text.txt"
    translations_path: str = "translations/plain-text"
    output_path: str = "results/plain-text"
    human_translation_filename: str = "CHYPS-V-br20-Human-25-09-30.txt"


@dataclass
class QuestionsOnlyConfig(Config):
    """
    Configuration class for the "questions-only" dataset.

    This class inherits from the Config class and overrides the paths to the data and results files
    to point to the "questions-only" dataset.

    Attributes:
        original_text_path (str): The path to the original text file for the "questions-only" dataset.
        translations_path (str): The path to the directory containing the translated text files for the "questions-only" dataset.
        output_path (str): The path to the directory where the results for the "questions-only" dataset will be saved.
    """

    original_text_path: str = "docs/CHYPS-V-questions-only.txt"
    translations_path: str = "translations/questions-only"
    output_path: str = "results/questions-only"
