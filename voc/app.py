"""Interface web e API local para exploração da voz do cliente."""
import argparse
import time
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from .index import Index
from .rag import answer


def create_app(index):
    app = Flask(__name__)

    @app.get("/")
    def home():
        return render_template("index.html", demo=index.demo, stats=index.stats, backend=index.backend)

    @app.get("/healthz")
    def health():
        return {"status": "ok", "documents": len(index.docs), "demo": index.demo}

    @app.post("/api/ask")
    def ask():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify(error="Envie um objeto JSON."), 400
        mode = data.get("mode", "investigar")
        raw_question = data.get("question", "")
        if not isinstance(raw_question, str) or not isinstance(mode, str):
            return jsonify(error="A pergunta e o modo precisam ser texto."), 400
        question = raw_question.strip()
        if mode not in {"investigar", "todos", "elogios", "reclamações"}:
            return jsonify(error="Modo inválido."), 400
        if mode == "investigar" and not 5 <= len(question) <= 500:
            return jsonify(error="Digite uma pergunta de 5 a 500 caracteres."), 400
        try:
            min_score, max_score = int(data.get("min_score", 1)), int(data.get("max_score", 5))
            year = int(data["year"]) if data.get("year") not in ("", None) else None
        except (ValueError, TypeError):
            return jsonify(error="Nota ou ano inválido."), 400
        delayed = data.get("delayed", False)
        if not 1 <= min_score <= max_score <= 5 or not isinstance(delayed, bool):
            return jsonify(error="Recorte inválido."), 400
        if (year is not None or delayed) and not index.stats["metadados_pedido"]:
            return jsonify(error="Importe o CSV de pedidos para filtrar por ano ou atraso."), 400
        start = time.perf_counter()
        result = answer(index, question, min_score, max_score, year, delayed, mode)
        result["elapsed_ms"] = round((time.perf_counter() - start) * 1000)
        return jsonify(result)

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Executa o painel Voice of Customer.")
    parser.add_argument("--index", default="data/index")
    parser.add_argument("--port", default=5050, type=int)
    params = parser.parse_args()
    if not (Path(params.index) / "index.json").is_file():
        parser.error("Índice ausente. Execute python -m voc.index antes de iniciar o painel.")
    create_app(Index(params.index)).run(host="127.0.0.1", port=params.port, threaded=True)
