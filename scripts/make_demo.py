"""Gera os CSVs sintéticos usados para testar o fluxo sem baixar a Olist."""
import csv
from pathlib import Path

EXAMPLES = [
    ("D01", 1, 6, "Meu pedido chegou com seis dias de atraso. O rastreio ficou parado por vários dias."),
    ("D02", 2, 4, "O pacote chegou atrasado e perdi a data do aniversário."),
    ("D03", 1, 12, "Entrega com atraso de doze dias. O atendimento não tinha atualização do rastreamento."),
    ("D04", 2, 2, "Atraso na entrega apesar de o produto ter chegado intacto."),
    ("D05", 1, None, "Não recebi o pedido. No sistema constava como entregue."),
    ("D06", 1, None, "O pedido não chegou. Já passou o prazo de entrega."),
    ("D07", 2, 1, "Recebi um produto errado, de cor diferente da que comprei."),
    ("D08", 1, 0, "Veio um item errado. Pedi um modelo e recebi outro."),
    ("D09", 1, 0, "O copo veio quebrado e a caixa estava amassada."),
    ("D10", 2, 0, "O produto apresentou defeito na primeira vez que liguei."),
    ("D11", 2, 0, "O acabamento veio danificado. A embalagem estava rasgada."),
    ("D12", 5, -4, "Entrega rápida e encomenda bem embalada."),
    ("D13", 5, -2, "Chegou antes do prazo e o produto tem boa qualidade."),
    ("D14", 4, -1, "Produto de ótima qualidade, acabamento bem feito."),
    ("D15", 5, 0, "Excelente qualidade do tecido. O tamanho ficou perfeito."),
    ("D16", 5, -3, "Achei o material de boa qualidade. O produto é resistente."),
    ("D17", 5, -5, "O pedido chegou rápido. Gostei da proteção da embalagem."),
    ("D18", 4, 0, "Bom atendimento. A equipe tirou minhas dúvidas sobre a compra."),
    ("D19", 5, -1, "Atendimento excelente, responderam minha pergunta no mesmo dia."),
    ("D20", 3, 0, "O tamanho estava correto, mas o acabamento podia ser melhor."),
    ("D21", 3, 0, "Gostei da compra, mas a caixa veio aberta."),
    ("D22", 2, 3, "O prazo de entrega foi alterado e o pacote chegou depois do prazo."),
    ("D23", 5, 0, "Boa qualidade das costuras e acabamento muito bonito."),
    ("D24", 5, -1, "Tudo certo com a compra, o pacote chegou completo."),
]


def main():
    target = Path("data/demo")
    target.mkdir(parents=True, exist_ok=True)
    with (target / "olist_order_reviews_dataset.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["review_id", "order_id", "review_score", "review_comment_title",
                         "review_comment_message", "review_creation_date"])
        for order, score, _, text in EXAMPLES:
            writer.writerow([f"SINT-{order}", order, score, "", text, "2018-05-25"])
        writer.writerow(["SINT-vazio", "D25", 4, "", "", "2018-05-25"])
    with (target / "olist_orders_dataset.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["order_id", "order_purchase_timestamp", "order_delivered_customer_date",
                         "order_estimated_delivery_date"])
        for i, (order, _, delay, _) in enumerate(EXAMPLES):
            year = 2017 if i % 5 == 0 else 2018
            delivered = "" if delay is None else f"{year}-05-{12 + delay:02}"
            writer.writerow([order, f"{year}-05-01", delivered, f"{year}-05-12"])


if __name__ == "__main__":
    main()
