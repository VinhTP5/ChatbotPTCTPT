"""
reranker.py
-----------
BGE Reranker dùng BAAI/bge-reranker-v2-m3 để xếp lại thứ tự chunks sau retrieval.

Reranker là cross-encoder: nhận cặp (query, passage) → sigmoid score.
Chính xác hơn cosine similarity (bi-encoder) nhưng chậm hơn (~2-3 giây/lần hỏi).

Cách dùng:
    from reranker import get_reranker

    ranker = get_reranker()                          # singleton (tái dùng model)
    docs   = ranker.rerank(question, docs, top_n=5)  # xếp lại + cắt top_n

Yêu cầu:
    transformers, torch  (đã có trong requirements.txt qua langchain-huggingface)
"""

from __future__ import annotations

import logging
from typing import Optional

from langchain_core.documents import Document

logger = logging.getLogger(__name__)

# Singleton cache — mỗi model_name chỉ load 1 lần
_RERANKER_CACHE: dict[str, "BGEReranker"] = {}


class BGEReranker:
    """
    Cross-encoder reranker dùng AutoModelForSequenceClassification.

    Args:
        model_name: HuggingFace model ID (default BAAI/bge-reranker-v2-m3)
        device    : "cpu", "cuda", "mps" hoặc None (auto-detect)
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
        device: Optional[str] = None,
    ) -> None:
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError as e:
            raise ImportError(
                "Cần cài transformers và torch để dùng reranker. "
                "Chạy: pip install transformers torch"
            ) from e

        self.model_name = model_name

        # Auto-detect device
        if device is None:
            if torch.cuda.is_available():
                device = "cuda"
            elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
                device = "mps"
            else:
                device = "cpu"
        self.device = device

        logger.info("[BGEReranker] Loading model %s on %s …", model_name, device)
        try:
            self._tokenizer = AutoTokenizer.from_pretrained(model_name)
            self._model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self._model.eval()
            self._model.to(device)
            logger.info("[BGEReranker] Model loaded OK")
        except Exception as exc:
            raise RuntimeError(
                f"Không thể load reranker model '{model_name}': {exc}\n"
                "Hãy chạy lần đầu khi có internet để download model."
            ) from exc

    def rerank(
        self,
        query: str,
        docs: list[Document],
        top_n: Optional[int] = None,
    ) -> list[Document]:
        """
        Xếp lại docs theo score cross-encoder (giảm dần).

        Args:
            query : câu hỏi người dùng
            docs  : danh sách Document sau retrieval
            top_n : giữ lại bao nhiêu doc (None = giữ tất cả, đã sắp xếp)

        Returns:
            list[Document] đã sắp xếp theo relevance, cắt top_n nếu có.
        """
        import torch

        if not docs:
            return docs

        n = len(docs)
        effective_top_n = min(top_n, n) if top_n is not None else n

        # Tạo pairs (query, passage)
        pairs = [(query, doc.page_content or "") for doc in docs]

        # Tokenize theo batch 32 để tránh OOM
        BATCH = 32
        all_scores: list[float] = []

        for i in range(0, n, BATCH):
            batch_pairs = pairs[i : i + BATCH]
            inputs = self._tokenizer(
                batch_pairs,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                logits = self._model(**inputs).logits
                # Squeeze về 1D nếu output có shape (batch, 1)
                if logits.dim() == 2 and logits.shape[1] == 1:
                    logits = logits.squeeze(1)
                scores = torch.sigmoid(logits).cpu().tolist()

            if isinstance(scores, float):
                scores = [scores]
            all_scores.extend(scores if isinstance(scores, list) else [scores])

        # Sắp xếp theo score giảm dần
        ranked = sorted(
            zip(all_scores, docs),
            key=lambda x: x[0],
            reverse=True,
        )

        # Ghi score vào metadata để debug
        result: list[Document] = []
        for score, doc in ranked[:effective_top_n]:
            doc.metadata["rerank_score"] = round(float(score), 4)
            result.append(doc)

        return result


def get_reranker(model_name: str = "BAAI/bge-reranker-v2-m3") -> BGEReranker:
    """
    Trả về BGEReranker singleton (cache theo model_name).

    Gọi nhiều lần với cùng model_name sẽ tái dùng instance đã load.
    """
    global _RERANKER_CACHE
    if model_name not in _RERANKER_CACHE:
        _RERANKER_CACHE[model_name] = BGEReranker(model_name=model_name)
    return _RERANKER_CACHE[model_name]
