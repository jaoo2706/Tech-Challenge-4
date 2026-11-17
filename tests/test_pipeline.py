import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from scripts.import_olist import TABLES, import_archive
from voc.app import create_app
from voc.index import Index, build
from voc.rag import _phrase_excerpt, answer, filter_specific_constraints, find_theme, validate, verify_support, THEMES


class PipelineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        storage = tempfile.TemporaryDirectory()
        cls.addClassCleanup(storage.cleanup)
        cls.directory = Path(storage.name)
        build("data/demo", cls.directory / "index", "lsa", demo=True)
        cls.index = Index(cls.directory / "index")
        cls.client = create_app(cls.index).test_client()

    def test_import_zip(self):
        archive = self.directory / "olist.zip"
        with ZipFile(archive, "w") as destination:
            for name in TABLES:
                destination.write(Path("data/demo") / name, f"extraido/{name}")
        imported = self.directory / "raw"
        import_archive(archive, imported)
        for name in TABLES:
            self.assertEqual((imported / name).read_bytes(), (Path("data/demo") / name).read_bytes())

    def test_health_dashboard_and_filters(self):
        self.assertEqual(self.client.get("/healthz").json,
                         {"status": "ok", "documents": 24, "demo": True})
        self.assertEqual(self.client.get("/").status_code, 200)
        response = self.client.post("/api/ask", json={
            "mode": "reclamações", "min_score": 1, "max_score": 2, "year": 2018, "delayed": True,
        })
        self.assertEqual(response.status_code, 200)
        result = response.json
        self.assertEqual(result["status"], "contagem")
        self.assertTrue(all(doc["score"] <= 2 and doc["delay_days"] > 0
                            and doc["purchase_date"].startswith("2018") for doc in result["evidence"]))
        self.assertEqual(self.client.post("/api/ask", json={"question": "Pergunta", "min_score": 7}).status_code, 400)

    def test_rag_with_controlled_model_response(self):
        question = "Quais avaliações mencionam que o pedido não chegou?"

        def controlled_model(query, context):
            self.assertEqual(query, question)
            source = next(doc for doc in context if doc["order_id"] == "D05")
            return {"achados": [{"texto": "Há relato de pedido não recebido.",
                                 "fontes": [{"id": source["id"], "trecho": source["text"]}]}]}

        with patch("voc.rag.urllib.request.urlopen") as urlopen:
            def respond(request, **kwargs):
                data = json.loads(request.data)
                context = json.loads(data["messages"][1]["content"])
                if "trechos" in context:  # verificação de sustentação
                    payload = {"sustenta": True}
                    return io.BytesIO(json.dumps({"message": {"content": json.dumps(payload)}}).encode())
                if "avaliacoes" not in context and "evidencias" not in context:  # portão de escopo
                    return io.BytesIO(json.dumps({"message": {"content": '{"no_escopo": true}'}}).encode())
                if "avaliacoes" in context:  # etapa de triagem
                    payload = {"no_escopo": True, "relevantes": [item["id"] for item in context["avaliacoes"]]}
                    return io.BytesIO(json.dumps({"message": {"content": json.dumps(payload)}}).encode())
                documents = {doc["id"]: doc for doc in self.index.docs}
                evidence = [documents[item["id"]] for item in context["evidencias"]]
                payload = controlled_model(context["pergunta"], evidence)
                return io.BytesIO(json.dumps({"message": {"content": json.dumps(payload)}}).encode())

            urlopen.side_effect = respond
            response = self.client.post("/api/ask", json={"question": question, "max_score": 2})
        result = response.json
        self.assertEqual(result["status"], "respondido")
        cited = result["findings"][0]["fontes"][0]
        evidence = {doc["id"]: doc for doc in result["evidence"]}
        self.assertEqual(evidence[cited["id"]]["order_id"], "D05")
        self.assertIn(cited["trecho"], evidence[cited["id"]]["text"])

    def test_missing_evidence_unavailable_model_and_invalid_citation(self):
        no_evidence = answer(self.index, "xqzyw zqpwqv", model=lambda *_: self.fail("Chamou o modelo sem fontes."))
        self.assertEqual(no_evidence["status"], "insuficiente")
        abstention = answer(self.index, "Qual era a margem de lucro da Olist?", model=lambda *_: {"achados": []})
        self.assertEqual(abstention["status"], "insuficiente")
        with patch("voc.rag.urllib.request.urlopen", side_effect=OSError):
            result = self.client.post("/api/ask", json={"question": "O que relataram sobre atrasos na entrega?"}).json
        self.assertEqual(result["status"], "indisponivel")
        self.assertTrue(result["evidence"])
        source = result["evidence"][0]
        payload = {"achados": [{"texto": "Uma afirmação qualquer.",
                                "fontes": [{"id": source["id"], "trecho": "trecho inventado"}]}]}
        self.assertEqual(validate(payload, result["evidence"]), [])

    def test_negation_is_not_counted_as_theme(self):
        delay = THEMES["Atraso mencionado"]
        self.assertIsNone(find_theme(delay, "Entrega sem nenhum atraso, tudo certo"))
        self.assertIsNone(find_theme(delay, "Não houve atraso na entrega"))
        self.assertIsNotNone(find_theme(delay, "Houve atraso de uma semana"))

    def test_quote_matching_tolerates_case_accents_and_punctuation(self):
        evidence = [{"id": "R1", "text": "O pacote CHEGOU depois do prazo, infelizmente."}]
        payload = {"achados": [{"texto": "Houve atraso na entrega.",
                                "fontes": [{"id": "R1", "trecho": "chegou depois do prazo infelizmente"}]}]}
        findings = validate(payload, evidence)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["fontes"][0]["trecho"], "CHEGOU depois do prazo, infelizmente")

    def test_recurring_expression_requires_adjacent_words(self):
        self.assertIsNone(_phrase_excerpt("Não recebi o produto.", "recebi produto"))
        self.assertEqual(_phrase_excerpt("Material de péssima qualidade.", "pessima qualidade", 0, 0),
                         "péssima qualidade")

    def test_specific_question_requires_all_details_in_one_review(self):
        docs = [{"text": "A garantia estendida de um ano chegou para o celular."},
                {"text": "A garantia estendida de cinco anos chegou para o notebook."},
                {"text": "A garantia estendida de 5 anos chegou para o celular."}]
        with patch("voc.rag._chat", return_value={"restricoes":
                                                 ["garantia estendida", "cinco anos", "celulares"]}):
            selected = filter_specific_constraints(
                "Quais avaliações mencionam a garantia estendida de cinco anos para celulares?", docs)
        self.assertEqual(selected, docs[2:])
        with patch("voc.rag._chat", return_value={"restricoes": ["drones"]}):
            self.assertEqual(filter_specific_constraints(
                "O que dizem sobre entregas por drones?", [{"text": "A entrega demorou."}]), [])

    def test_support_verifies_each_citation(self):
        finding = {"texto": "A qualidade é excelente.", "fontes": [
            {"id": "R1", "trecho": "Produto de excelente qualidade"},
            {"id": "R2", "trecho": "A entrega demorou"},
        ]}

        def judge(_prompt, payload, _tokens):
            self.assertEqual(len(payload["trechos"]), 1)
            return {"sustenta": "qualidade" in payload["trechos"][0]}

        with patch("voc.rag._chat", side_effect=judge):
            result = verify_support([finding], [])
        self.assertEqual(result[0]["fontes"], finding["fontes"][:1])

    def test_broad_question_uses_larger_sample_and_count_question_redirects(self):
        seen = {}

        def model(question, context):
            seen["n"] = len(context)
            return {"achados": []}

        answer(self.index, "Quais são os principais problemas de atraso na entrega?", model=model)
        self.assertGreater(seen.get("n", 0), 0)
        redirected = answer(self.index, "Quantos pedidos tiveram atraso?",
                            model=lambda *_: self.fail("Contagem não deve chamar o modelo."))
        self.assertIn("Frequência", redirected["message"])

    def test_business_questions_abstain_without_calling_model(self):
        for question in ("Qual era a margem de lucro da Olist?", "Qual o custo de cada entrega para o vendedor?"):
            result = answer(self.index, question, model=lambda *_: self.fail("Não deveria chamar o modelo."))
            self.assertEqual(result["status"], "insuficiente")
