"""Late chunking utilities for token-level embedding and pooling."""

from __future__ import annotations

from typing import Optional

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer


class LateChunkingEmbedder:
    """Embedder for late and long-late chunking."""

    def __init__(
        self,
        model_name: str,
        window_tokens: int = 512,
        window_overlap: int = 64,
        device: Optional[str] = None,
    ):
        self.model_name = model_name
        self.window_tokens = max(16, int(window_tokens))
        self.window_overlap = max(0, int(window_overlap))
        if self.window_overlap >= self.window_tokens:
            self.window_overlap = max(0, self.window_tokens // 4)

        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
        self.model = AutoModel.from_pretrained(model_name)
        self.model.to(self.device)
        self.model.eval()

    def _encode_window(self, token_ids: list[int]) -> np.ndarray:
        """Encode one token window into token embeddings."""
        if not token_ids:
            return np.zeros((0, self.model.config.hidden_size), dtype=np.float32)

        input_ids = torch.tensor([token_ids], dtype=torch.long, device=self.device)
        attention_mask = torch.ones_like(input_ids, dtype=torch.long, device=self.device)

        with torch.no_grad():
            out = self.model(input_ids=input_ids, attention_mask=attention_mask)
            hidden = out.last_hidden_state.squeeze(0)

        arr = hidden.detach().cpu().numpy().astype(np.float32)
        if arr.shape[0] > len(token_ids):
            arr = arr[: len(token_ids)]
        return arr

    def _long_encode(self, token_ids: list[int]) -> np.ndarray:
        """Encode long token sequence with overlapping windows.

        Collects all windows first, then runs a single padded batched forward
        pass instead of one forward pass per window — significantly faster for
        long documents with many windows.
        """
        n = len(token_ids)
        if n == 0:
            return np.zeros((0, self.model.config.hidden_size), dtype=np.float32)

        if n <= self.window_tokens:
            return self._encode_window(token_ids)

        # ── Collect window slices ─────────────────────────────────────────────
        stride = max(1, self.window_tokens - self.window_overlap)
        win_ids: list[list[int]] = []
        start = 0
        while start < n:
            end = min(n, start + self.window_tokens)
            win_ids.append(token_ids[start:end])
            if end >= n:
                break
            start += stride

        # ── Single batched forward pass (pad to uniform length) ───────────────
        max_len = max(len(w) for w in win_ids)
        pad_id = self.tokenizer.pad_token_id if self.tokenizer.pad_token_id is not None else 0
        input_ids = torch.tensor(
            [w + [pad_id] * (max_len - len(w)) for w in win_ids],
            dtype=torch.long,
            device=self.device,
        )
        attention_mask = torch.tensor(
            [[1] * len(w) + [0] * (max_len - len(w)) for w in win_ids],
            dtype=torch.long,
            device=self.device,
        )
        with torch.no_grad():
            out = self.model(input_ids=input_ids, attention_mask=attention_mask)
            hidden = out.last_hidden_state  # (num_wins, max_len, hidden_dim)

        # ── Unpad and remove overlap ──────────────────────────────────────────
        segments: list[np.ndarray] = []
        for i, w in enumerate(win_ids):
            w_len = len(w)
            part_emb = hidden[i, :w_len].detach().cpu().numpy().astype(np.float32)
            if i > 0 and self.window_overlap > 0:
                skip = min(self.window_overlap, part_emb.shape[0])
                part_emb = part_emb[skip:]
            if part_emb.size > 0:
                segments.append(part_emb)

        if not segments:
            return np.zeros((0, self.model.config.hidden_size), dtype=np.float32)

        return np.concatenate(segments, axis=0)

    def _token_bounds_for_char_span(
        self,
        offsets: list[tuple[int, int]],
        char_start: int,
        char_end: int,
    ) -> tuple[int, int]:
        """Map character span to token span [start_idx, end_idx)."""
        start_idx: Optional[int] = None
        end_idx: Optional[int] = None

        for i, (s, e) in enumerate(offsets):
            if e <= s:
                continue
            if start_idx is None and e > char_start:
                start_idx = i
            if s < char_end:
                end_idx = i + 1
            elif s >= char_end:
                break

        if start_idx is None:
            start_idx = 0
        if end_idx is None:
            end_idx = max(start_idx + 1, len(offsets))
        if end_idx <= start_idx:
            end_idx = min(len(offsets), start_idx + 1)

        return start_idx, end_idx

    @staticmethod
    def _mean_pool(vectors: np.ndarray) -> np.ndarray:
        """Mean pool and L2-normalize vectors."""
        if vectors.size == 0:
            return np.zeros((0,), dtype=np.float32)
        pooled = vectors.mean(axis=0)
        norm = float(np.linalg.norm(pooled))
        if norm > 0:
            pooled = pooled / norm
        return pooled.astype(np.float32)

    def embed_document_chunks(
        self,
        text: str,
        chunk_spans: list[tuple[int, int]],
    ) -> list[list[float]]:
        """Build embeddings for chunk spans from document-level token embeddings."""
        if not text.strip() or not chunk_spans:
            return []

        enc = self.tokenizer(
            text,
            return_offsets_mapping=True,
            add_special_tokens=False,
            truncation=False,
        )

        token_ids = list(enc["input_ids"])
        offsets = [tuple(x) for x in enc["offset_mapping"]]

        token_embeddings = self._long_encode(token_ids)
        token_count = min(token_embeddings.shape[0], len(offsets))
        token_embeddings = token_embeddings[:token_count]
        offsets = offsets[:token_count]

        vectors: list[list[float]] = []
        for char_start, char_end in chunk_spans:
            t_start, t_end = self._token_bounds_for_char_span(offsets, char_start, char_end)
            t_start = max(0, min(t_start, token_count - 1)) if token_count else 0
            t_end = max(t_start + 1, min(t_end, token_count)) if token_count else 0

            if token_count == 0 or t_end <= t_start:
                vec = np.zeros((self.model.config.hidden_size,), dtype=np.float32)
            else:
                vec = self._mean_pool(token_embeddings[t_start:t_end])
            vectors.append(vec.tolist())

        return vectors

    def embed_query(self, text: str) -> list[float]:
        """Embed query with mean pooling."""
        if not text.strip():
            return []

        enc = self.tokenizer(
            text,
            add_special_tokens=False,
            truncation=True,
            max_length=self.window_tokens,
        )
        ids = list(enc["input_ids"])
        emb = self._encode_window(ids)
        vec = self._mean_pool(emb)
        return vec.tolist()
