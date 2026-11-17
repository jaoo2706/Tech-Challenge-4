"""Verificação funcional reproduzível do RAG no índice oficial da Olist.

Confere status esperado e presença literal das fontes. A pertinência semântica
continua exigindo leitura humana; isto não mede Recall nem precisão.
"""
import argparse
import json
import os
from pathlib import Path
from time import perf_counter

from .index import Index
from .rag import answer


CASES = [
    ("Quais avaliações mencionam que o pedido não chegou?", 1, 2, "respondido"),
    ("Quais são os principais problemas relatados pelos clientes?", 1, 2, "respondido"),
    ("O que os clientes elogiam sobre a qualidade dos produtos?", 4, 5, "respondido"),
    ("Quais avaliações mencionam a garantia estendida de cinco anos para celulares?", 1, 5, "insuficiente"),
    ("O que os clientes relatam sobre entregas por drones?", 1, 5, "insuficiente"),
    ("Qual era a margem de lucro da Olist?", 1, 5, "insuficiente"),
]


def run(index):
    rows = []
    for question, low, high, expected in CASES:
        start = perf_counter()
        response = answer(index, question, low, high)
        evidence = {doc["id"]: doc["text"] for doc in response["evidence"]}
        citations_literal = all(
            source["id"] in evidence and source["trecho"] in evidence[source["id"]]
            for finding in response["findings"] for source in finding["fontes"]
        )
        rows.append({
            "pergunta": question, "notas": [low, high], "esperado": expected,
            "status": response["status"], "achados": response["findings"],
            "citacoes_literais": citations_literal,
            "passou": response["status"] == expected and citations_literal,
            "ms": round((perf_counter() - start) * 1000),
        })
        print(f"{'OK' if rows[-1]['passou'] else 'FALHOU'} {response['status']}: {question}", flush=True)
    return {"backend": index.backend, "modelo": os.getenv("OLLAMA_MODEL", "gemma3:4b"),
            "indexadas": len(index.docs), "casos": rows, "aprovados": sum(row["passou"] for row in rows)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", default="data/index/olist")
    parser.add_argument("--output", default="reports/checagem_olist.json")
    args = parser.parse_args()
    report = run(Index(args.index))
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{report['aprovados']}/{len(report['casos'])} casos aprovados. Relatório: {target}")
    raise SystemExit(report["aprovados"] != len(report["casos"]))
