"""Busca vetorial exata, busca lexical e fusão dos rankings."""
import argparse
import json
import os
import uuid
from pathlib import Path

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from .data import prepare


class E5:
    model_id = "intfloat/multilingual-e5-small"

    def __init__(self):
        import torch
        from transformers import AutoModel, AutoTokenizer

        self.torch = torch
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        self.model = AutoModel.from_pretrained(self.model_id).to(self.device).eval()

    def encode(self, messages, kind):
        batches = []
        with self.torch.inference_mode():
            for start in range(0, len(messages), 64):
                text = [f"{kind}: {item}" for item in messages[start:start + 64]]
                batch = self.tokenizer(text, padding=True, truncation=True, max_length=512,
                                       return_tensors="pt").to(self.device)
                output = self.model(**batch).last_hidden_state
                mask = batch.attention_mask.unsqueeze(-1)
                avg = (output * mask).sum(1) / mask.sum(1)
                batches.append(self.torch.nn.functional.normalize(avg).cpu().numpy())
        return np.concatenate(batches).astype(np.float32)


def vectorizer():
    return TfidfVectorizer(strip_accents="unicode", ngram_range=(1, 2), sublinear_tf=True,
                           max_features=85_000, dtype=np.float32)


def build(source, target, backend, demo=False):
    documents, stats = prepare(source)
    texts = [doc["text"] for doc in documents]
    lexical = vectorizer().fit_transform(texts)
    if backend == "e5":
        dense = E5().encode(texts, "passage")
        basis = np.empty((0, 0), dtype=np.float32)
    else:
        dimensions = min(160, lexical.shape[0] - 1, lexical.shape[1] - 1)
        svd = TruncatedSVD(n_components=dimensions, n_iter=7, random_state=42)
        dense = normalize(svd.fit_transform(lexical))
        basis = svd.components_
    target = Path(target)
    target.mkdir(parents=True, exist_ok=True)
    version = uuid.uuid4().hex
    bundle = target / f"{version}.npz"
    np.savez(bundle, vectors=dense, basis=basis)
    manifest = {"docs": documents, "stats": stats, "backend": backend, "bundle": bundle.name,
                "demo": demo, "schema": 1}
    temporary = target / f"{version}.json"
    temporary.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, target / "index.json")
    return stats


class Index:
    def __init__(self, directory):
        directory = Path(directory)
        manifest = json.loads((directory / "index.json").read_text(encoding="utf-8"))
        if manifest.get("schema") != 1 or manifest.get("backend") not in {"e5", "lsa"}:
            raise ValueError("Versão de índice incompatível. Reconstrua o índice.")
        self.docs = manifest["docs"]
        self.stats = manifest["stats"]
        self.demo = manifest["demo"]
        self.backend = manifest["backend"]
        with np.load(directory / manifest["bundle"], allow_pickle=False) as artifact:
            self.vectors = artifact["vectors"]
            self.basis = artifact["basis"]
        self.lexical = vectorizer()
        self.words = self.lexical.fit_transform(doc["text"] for doc in self.docs)
        self.encoder = E5() if self.backend == "e5" else None

    def candidates(self, min_score=1, max_score=5, year=None, delayed=False):
        return np.array([
            i for i, doc in enumerate(self.docs)
            if min_score <= doc["score"] <= max_score
            and (year is None or (doc["purchase_date"] or "")[:4] == str(year))
            and (not delayed or (doc["delay_days"] or 0) > 0)
        ], dtype=int)

    def search(self, question, candidates, k=8, strategy="hybrid"):
        if not len(candidates):
            return []
        terms = self.lexical.transform([question])
        lexical_scores = (self.words @ terms.T).toarray().ravel()[candidates]
        dense_query = (self.encoder.encode([question], "query") if self.encoder
                       else normalize(terms @ self.basis.T))
        semantic_scores = (self.vectors @ dense_query[0])[candidates]
        groups = {
            "lexical": (lexical_scores, 0.035),
            "semantic": (semantic_scores, float(os.getenv("E5_MIN_SCORE", "0.84")) if self.encoder else 0.20),
        }
        votes = {}
        for name, (scores, threshold) in groups.items():
            if strategy not in {"hybrid", name}:
                continue
            top = np.argsort(-scores, kind="stable")[:60]
            for rank, pos in enumerate(top, start=1):
                if scores[pos] >= threshold:
                    votes[pos] = votes.get(pos, 0) + 1 / (30 + rank)
        if self.encoder:  # com E5, a similaridade vetorial é condição para entrar no contexto
            votes = {pos: vote for pos, vote in votes.items()
                     if semantic_scores[pos] >= groups["semantic"][1]}
        results = []
        used = set()
        for pos in sorted(votes, key=lambda item: (-votes[item], -semantic_scores[item], item)):
            doc = self.docs[candidates[pos]]
            if doc["order_id"] in used or doc["text"].casefold() in used:
                continue
            used.update((doc["order_id"], doc["text"].casefold()))
            results.append({**doc, "semantic": round(float(semantic_scores[pos]), 4),
                            "lexical": round(float(lexical_scores[pos]), 4)})
            if len(results) == k:
                break
        return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Constrói a base de conhecimento.")
    parser.add_argument("--source", default="data/raw")
    parser.add_argument("--target", default="data/index")
    parser.add_argument("--backend", choices=["e5", "lsa"], default="e5")
    parser.add_argument("--demo", action="store_true", help="Marca um corpus sintético na interface.")
    args = parser.parse_args()
    print(json.dumps(build(args.source, args.target, args.backend, args.demo), ensure_ascii=False, indent=2))
