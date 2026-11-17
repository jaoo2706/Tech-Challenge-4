"""Avaliação da recuperação na base real com rótulos automáticos (padrão "prata").

Sem perguntas rotuladas por humanos, cada pergunta é associada a um tema do dicionário de THEMES.
Uma avaliação recuperada conta como relevante se o texto casa com o tema (sem negação) dentro do
recorte de notas da pergunta. Os rótulos têm limites: avaliações pertinentes que usam outras palavras
não são contadas, e o critério favorece a busca lexical, que procura as mesmas palavras. Os números
servem para comparar estratégias e detectar regressões, não como medida absoluta de qualidade.
"""
import argparse
import json
from pathlib import Path
from statistics import mean

from .index import Index
from .rag import THEMES, find_theme

CASES = [
    ("Quais avaliações mencionam que o pedido não chegou?", 1, 2, "Pedido não recebido"),
    ("O que os clientes relatam sobre atrasos na entrega?", 1, 2, "Atraso mencionado"),
    ("Quais clientes receberam um produto diferente do pedido?", 1, 2, "Produto errado"),
    ("Quais reclamações falam de produtos quebrados ou com defeito?", 1, 2, "Dano ou defeito"),
    ("Quais clientes pedem troca, devolução ou reembolso?", 1, 2, "Troca ou reembolso"),
    ("Quais clientes não receberam resposta ou contato da loja?", 1, 2, "Falta de contato ou resposta"),
    ("Quais avaliações elogiam a rapidez da entrega?", 4, 5, "Entrega rápida"),
    ("O que os clientes elogiam sobre a qualidade dos produtos?", 4, 5, "Qualidade elogiada"),
    ("Quais avaliações elogiam o atendimento?", 4, 5, "Atendimento elogiado"),
    ("Quais clientes recomendam a loja?", 4, 5, "Recomendação"),
]


def run(index, k=8):
    output = {"k": k, "backend": index.backend, "rotulo": "prata (regex do tema, sem negação)", "estrategias": {}}
    for strategy in ("lexical", "semantic", "hybrid"):
        rows = []
        for question, low, high, theme in CASES:
            pool = index.candidates(low, high)
            docs = index.search(question, pool, k=k, strategy=strategy)
            hits = [bool(find_theme(THEMES[theme], doc["text"])) for doc in docs]
            first = next((rank for rank, hit in enumerate(hits, 1) if hit), None)
            rows.append({"pergunta": question, "tema": theme, "recuperadas": len(docs),
                         "precisao": sum(hits) / len(docs) if docs else 0.0,
                         "rr": 1 / first if first else 0.0})
        output["estrategias"][strategy] = {
            "precisao_media": round(mean(r["precisao"] for r in rows), 3),
            "mrr": round(mean(r["rr"] for r in rows), 3),
            "casos": rows,
        }
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", default="data/index/olist")
    parser.add_argument("--output", default="reports/avaliacao_olist_prata.json")
    parser.add_argument("--k", type=int, default=8)
    args = parser.parse_args()
    report = run(Index(args.index), args.k)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for name, row in report["estrategias"].items():
        print(name, "P@%d" % args.k, row["precisao_media"], "MRR", row["mrr"])
