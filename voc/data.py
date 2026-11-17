"""Preparação determinística e registro de proveniência do corpus."""
import csv
import hashlib
import re
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path


def clean(value):
    value = unicodedata.normalize("NFKC", value or "")
    value = re.sub(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", "[email ocultado]", value)
    value = re.sub(r"(?<!\w)(?:\+55\s*)?(?:\(?\d{2}\)?\s*)?\d{4,5}[- ]\d{4}(?!\w)", "[telefone ocultado]", value)
    return " ".join(value.split())


def day(value):
    try:
        return date.fromisoformat((value or "")[:10]).isoformat()
    except ValueError:
        return None


def rows(path, required):
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        missing = set(required) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path.name}: colunas ausentes: {', '.join(sorted(missing))}")
        yield from reader


def prepare(source):
    source = Path(source)
    reviews = source / "olist_order_reviews_dataset.csv"
    orders_path = source / "olist_orders_dataset.csv"
    orders = {}
    if orders_path.is_file():
        for row in rows(orders_path, ["order_id", "order_purchase_timestamp"]):
            orders[row["order_id"]] = row
    files = [reviews, orders_path] if orders else [reviews]
    stats = Counter()
    documents = []
    seen = set()
    for row in rows(reviews, ["review_id", "order_id", "review_score", "review_comment_message"]):
        stats["linhas_lidas"] += 1
        review, order = row["review_id"], row["order_id"]
        score = (row["review_score"] or "").strip()
        if not review or not order or score not in {"1", "2", "3", "4", "5"}:
            stats["metadados_invalidos"] += 1
            continue
        title = clean(row.get("review_comment_title"))
        comment = clean(row["review_comment_message"])
        comment = " — ".join(dict.fromkeys(part for part in [title, comment] if part))
        if not any(char.isalnum() for char in comment):
            stats["sem_texto_util"] += 1
            continue
        key = (order, score, comment.casefold())
        if key in seen:
            stats["duplicatas"] += 1
            continue
        seen.add(key)
        meta = orders.get(order, {})
        delivered = day(meta.get("order_delivered_customer_date"))
        expected = day(meta.get("order_estimated_delivery_date"))
        delay = (date.fromisoformat(delivered) - date.fromisoformat(expected)).days if delivered and expected else None
        fingerprint = hashlib.sha256(f"{review}|{order}|{score}|{comment}".encode()).hexdigest()
        documents.append({
            "id": "R" + fingerprint[:16], "review_id": review, "order_id": order,
            "score": int(score), "text": comment, "review_date": day(row.get("review_creation_date")),
            "purchase_date": day(meta.get("order_purchase_timestamp")), "delay_days": delay,
        })
    if len(documents) < 3:
        raise ValueError("A indexação exige pelo menos três avaliações úteis.")
    return documents, {
        **stats, "indexadas": len(documents), "pedidos_com_texto": len({d["order_id"] for d in documents}),
        "origens": {path.name: hashlib.file_digest(path.open("rb"), "sha256").hexdigest()
                    if hasattr(hashlib, "file_digest") else hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in files},
        "metadados_pedido": bool(orders),
    }
