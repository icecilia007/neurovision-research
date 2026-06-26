"""
This module implements the MetricX-24 metric.
"""

import torch
import transformers


class MetricX:
    """
    Initializes and runs a pretrained sequence classification model for
    scoring text pairs or triplets using the transformers library. The
    MetricX class loads a specified model and tokenizer, processes input
    texts, and returns prediction scores for each input set. Designed for
    use with GPU if available.
    """

    def __init__(
        self,
        model_name="google/metricx-24-hybrid-xxl-v2p6",
        tokenizer_name="google/mt5-base",
    ):
        print(f"[MetricX] Initializing with model: {model_name}")
        print(f"[MetricX] Tokenizer: {tokenizer_name}")
        self.model = transformers.AutoModelForSequenceClassification.from_pretrained(
            model_name, torch_dtype=torch.float32
        )
        self.tokenizer = transformers.AutoTokenizer.from_pretrained(
            tokenizer_name, legacy=False
        )
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"[MetricX] Using device: {self.device}")
        self.model.to(self.device)
        self.model.eval()
        print(f"[MetricX] Model initialization complete")

    def score(self, source_texts, hypothesis_texts, reference_texts):
        """
        Scores candidate texts against references using a model. Prepares input
        strings from source_texts, hypothesis_texts, and reference_texts,
        tokenizes them, runs inference with the model, and returns the
        predictions as a list.

        Args:
            source_texts (list): List of source texts.
            hypothesis_texts (list): List of candidate/hypothesis texts to score.
            reference_texts (list): List of reference texts for comparison.

        Returns:
            list: A list of prediction scores, one for each input set.
        """
        print(f"[MetricX.score] Processing {len(source_texts)} text(s)")
        inputs = []
        for src, hypo, ref in zip(source_texts, hypothesis_texts, reference_texts):
            if ref:
                inputs.append(f"source: {src} candidate: {hypo} reference: {ref}")
            else:
                inputs.append(f"source: {src} candidate: {hypo}")

        print(f"[MetricX.score] Tokenizing {len(inputs)} input(s)...")
        tokenized_inputs = self.tokenizer(
            inputs,
            max_length=2048,
            truncation=True,
            padding=True,
            return_tensors="pt",
        )

        input_ids = tokenized_inputs.input_ids.to(self.device)
        attention_mask = tokenized_inputs.attention_mask.to(self.device)
        print(f"[MetricX.score] Input shape: {input_ids.shape}")

        print(f"[MetricX.score] Running inference...")
        with torch.no_grad():
            outputs = self.model(
                input_ids=input_ids,
                attention_mask=attention_mask
            )

            logits = outputs.logits  # shape: [batch, num_labels]
            scores = logits[:, 0].float().tolist()


        print(f"[MetricX.score] Predictions: {scores}")
        return scores


def metricx(
    candidate: str, reference: str, source: str, metric_instance: MetricX
) -> float:
    """
    Calculates the MetricX-24 score for a given candidate, reference, and source text.

    Args:
        candidate (str): The candidate text.
        reference (str): The reference text.
        source (str): The source text.

    Returns:
        float: The MetricX-24 score.
    """
    print(f"[metricx] Source: {source[:50]}...")
    print(f"[metricx] Candidate: {candidate[:50]}...")
    print(f"[metricx] Reference: {reference[:50]}...")

    if not metric_instance:
        print(f"[metricx] No metric instance provided, creating new one")
        metric_instance = MetricX()

    score = metric_instance.score(
        source_texts=[source],
        hypothesis_texts=[candidate],
        reference_texts=[reference],
    )
    result = score[0]
    print(f"[metricx] Result: {result}")
    return result
