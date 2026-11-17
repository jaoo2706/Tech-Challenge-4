"""Compara recuperação lexical, semântica e híbrida com rótulos explícitos."""
import argparse
import json
from pathlib import Path
from statistics import mean
from time import perf_counter

from .index import Index
from .rag import answer


def run(index, cases, k=5, test_generation=False):
    output = {"backend": index.backend, "demo": index.demo, "k": k, "estrategias": {}}
    pool = index.candidates()
    for strategy in ("lexical", "semantic", "hybrid"):
        observations = []
        for case in cases:
            relevant = set(case["relevant_orders"])
            start = perf_counter()
            docs = index.search(case["question"], pool, k=k, strategy=strategy)
            order_ids = [doc["order_id"] for doc in docs]
            ranks = [i for i, key in enumerate(order_ids, 1) if key in relevant]
            observations.append({
                "pergunta": case["question"], "esperados": sorted(relevant), "recuperados": order_ids,
                "recall": len(ranks) / len(relevant) if relevant else None,
                "rr": (1 / ranks[0] if ranks else 0) if relevant else None,
                "ms": round(1000 * (perf_counter() - start), 2),
            })
        positives = [x for x in observations if x["esperados"]]
        negatives = [x for x in observations if not x["esperados"]]
        output["estrategias"][strategy] = {
            "recall_medio": mean(x["recall"] for x in positives) if positives else None,
            "mrr": mean(x["rr"] for x in positives) if positives else None,
            "fora_escopo_sem_recuperacao": sum(not x["recuperados"] for x in negatives),
            "perguntas_fora_escopo": len(negatives), "casos": observations,
        }
    if test_generation:
        output["geracao"] = []
        for case in cases:
            start = perf_counter()
            response = answer(index, case["question"])
            source_orders = {doc["id"]: doc["order_id"] for doc in response["evidence"]}
            cited = sorted({source_orders[source["id"]] for finding in response["findings"]
                            for source in finding["fontes"]})
            output["geracao"].append({
                "pergunta": case["question"], "esperados": case["relevant_orders"], "status": response["status"],
                "pedidos_citados": cited, "achados": response["findings"],
                "ms": round(1000 * (perf_counter() - start)),
            })
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", default="data/index")
    parser.add_argument("--cases", default="data/demo/queries.json")
    parser.add_argument("--output", default="reports/avaliacao_demo.json")
    parser.add_argument("--k", type=int, default=5, choices=range(1, 21))
    parser.add_argument("--generation", action="store_true")
    args = parser.parse_args()
    cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))
    index = Index(args.index)
    orders = {d["order_id"] for d in index.docs}
    if any(set(case["relevant_orders"]) - orders for case in cases):
        parser.error("Há pedidos rotulados que não pertencem a este índice. Informe os casos do corpus correto.")
    report = run(index, cases, args.k, args.generation)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for name, row in report["estrategias"].items():
        print(name, "Recall", row["recall_medio"], "MRR", row["mrr"])
