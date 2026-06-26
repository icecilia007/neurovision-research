"""
This module is responsible for loading the original and translated texts.

It defines a class to represent a translation and two functions to load the original text and the translations from the file system.
"""
import os
import re
from dataclasses import dataclass

@dataclass
class Translation:
    """
    Represents a translated text.

    This class stores the content of a translated text, as well as metadata about the translation, such as the model name and the date of translation.

    Attributes:
        model_name (str): The name of the model that generated the translation.
        date (str): The date the translation was generated.
        content (str): The content of the translated text.
        filename (str): The filename of the translated text.
    """
    model_name: str
    date: str
    content: str
    filename: str

def load_original_text(filepath: str) -> str:
    """
    Loads the original text from a file.

    Args:
        filepath (str): The path to the original text file.

    Returns:
        str: The content of the original text file.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()

def load_translations(directory: str) -> list[Translation]:
    """
    Loads all translations from a directory.

    This function iterates over all the files in a directory and, if the file is a .txt file, it reads the content of the file and parses the filename to extract the model name and the date of translation.
    It then creates a Translation object with the extracted information and the content of the file and adds it to a list.

    Args:
        directory (str): The path to the directory containing the translated text files.

    Returns:
        list[Translation]: A list of Translation objects.
    """
    translations = []
    for filename in os.listdir(directory):
        if filename.endswith(".txt"):
            filepath = os.path.join(directory, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Parse filename to get model name and date
            # The regex captures the model name and the date from the filename.
            # Example: CHYPS-V-br20-qwen-3-max-25-07-24.txt
            # model_name: qwen-3-max
            # date: 25-07-24
            match = re.search(r"CHYPS-V-br20-(.*?)-(\d{2}-\d{2}-\d{2})\.txt", filename)
            if match:
                model_name = match.group(1)
                date = match.group(2)
            else:
                model_name = "Unknown"
                date = "Unknown"

            # Handle human translation separately
            if "Human" in filename:
                model_name = "Human"
                match = re.search(r"CHYPS-V-br20-Human-(\d{2}-\d{2}-\d{2})\.txt", filename)
                if match:
                    date = match.group(1)


            translations.append(Translation(model_name, date, content, filename))
    return translations