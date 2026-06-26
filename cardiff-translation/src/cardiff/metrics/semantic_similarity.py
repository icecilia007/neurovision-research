"""
This module implements semantic similarity metrics.

The metrics are:
- BERTScore
- COMET

Semantic similarity is the task of determining how similar two texts are. In the context of machine translation, semantic similarity is used to evaluate the quality of a translation by comparing it to a reference translation.

This module implements two semantic similarity metrics:
- BERTScore: This metric computes a similarity score for each token in the candidate sentence with each token in the reference sentence. It uses contextual embeddings from BERT-based models.
- COMET: This metric is a neural framework for MT evaluation. It is a multilingual and multi-referenced metric that is trained to predict human judgments of translation quality.

References:
- BERTScore: Evaluating Text Generation with BERT - https://arxiv.org/abs/1904.09675
- COMET: A Neural Framework for MT Evaluation - https://arxiv.org/abs/2009.01500
"""
import torch
from transformers import AutoModel, AutoTokenizer
from comet import download_model, load_from_checkpoint

_COMET_MODEL = None
_BERT_MODEL = None
_BERT_TOKENIZER = None


def bertscore(candidate: str, reference: str, bert_scorer=None) -> float:
    """
    Calculates the BERTScore using NeoBERTugues (8192 tokens support).
    """
    global _BERT_MODEL, _BERT_TOKENIZER
    
    if _BERT_MODEL is None:
        print("[BERTScore] Loading NeoBERTugues model...")
        
        # Força tokenizador lento (Python) em vez do Fast (Rust)
        _BERT_TOKENIZER = AutoTokenizer.from_pretrained(
            "lorenzocc/NeoBERTugues",
            trust_remote_code=True,
            use_fast=False  # Desabilita o tokenizador Fast (Rust)
        )
        _BERT_MODEL = AutoModel.from_pretrained(
            "lorenzocc/NeoBERTugues",
            trust_remote_code=True
        )
        _BERT_MODEL.eval()
        
        if torch.cuda.is_available():
            _BERT_MODEL = _BERT_MODEL.cuda()
            print("[BERTScore] Model loaded on GPU")
        else:
            print("[BERTScore] Model loaded on CPU")
    
    model = _BERT_MODEL
    tokenizer = _BERT_TOKENIZER
    device = next(model.parameters()).device
    
    # Tokeniza
    cand_inputs = tokenizer(
        candidate,
        return_tensors="pt",
        padding=True,
        truncation=True
    ).to(device)
    
    ref_inputs = tokenizer(
        reference,
        return_tensors="pt",
        padding=True,
        truncation=True
    ).to(device)
    
    # Embeddings
    with torch.no_grad():
        cand_outputs = model(**cand_inputs)
        ref_outputs = model(**ref_inputs)
    
    cand_embeddings = cand_outputs.last_hidden_state[0]
    ref_embeddings = ref_outputs.last_hidden_state[0]
    
    # Remove padding
    cand_mask = cand_inputs['attention_mask'][0].bool()
    ref_mask = ref_inputs['attention_mask'][0].bool()
    
    cand_embeddings = cand_embeddings[cand_mask]
    ref_embeddings = ref_embeddings[ref_mask]
    
    # Similaridade cosseno
    similarities = torch.matmul(cand_embeddings, ref_embeddings.T)
    cand_norms = torch.norm(cand_embeddings, dim=1, keepdim=True)
    ref_norms = torch.norm(ref_embeddings, dim=1, keepdim=True)
    similarities = similarities / (cand_norms * ref_norms.T + 1e-8)
    
    # Precision e Recall
    precision = similarities.max(dim=1)[0].mean().item()
    recall = similarities.max(dim=0)[0].mean().item()
    
    # F1
    if precision + recall > 0:
        f1 = 2 * (precision * recall) / (precision + recall)
    else:
        f1 = 0.0
    
    return f1

def comet(candidate: str, reference: str, source: str, comet_model=None) -> float:
    """
    Calculates the COMET score for a given candidate, reference, and source text.

    COMET (Cross-lingual Optimized Metric for Evaluation of Translation) is a neural framework for MT evaluation.
    It is a multilingual and multi-referenced metric that is trained to predict human judgments of translation quality.
    This implementation uses the wmt22-comet-da model.

    COMET is based on a cross-lingual pretrained language model (XLM-R) and it is trained on direct assessments of machine translation quality (so-called "DA" scores).
    The model takes as input a source sentence, a candidate translation, and a reference translation, and it outputs a score that represents the quality of the translation.

    Args:
        candidate (str): The candidate text.
        reference (str): The reference text.
        source (str): The source text.

    Returns:
        float: The COMET score.
    """
    if not comet_model:
        global _COMET_MODEL
        if _COMET_MODEL is None:
            model_path = download_model("Unbabel/wmt22-comet-da")
            _COMET_MODEL = load_from_checkpoint(model_path)
        comet_model = _COMET_MODEL

    data = [{"src": source, "mt": candidate, "ref": reference}]
    print(f"[COMET] Predicting score...")

    model_output = comet_model.predict(data, batch_size=8, gpus=0, num_workers=0)
    score_value = model_output.scores[0]

    print(f"[COMET] Result: {score_value}")

    return score_value
