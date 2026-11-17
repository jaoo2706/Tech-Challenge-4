const byId = id => document.getElementById(id);
const nav = [...document.querySelectorAll(".nav")];
const statusLine = byId("status");
const results = byId("results");
const submit = byId("submit");
let mode = "investigar";
let inFlight = null;

function node(tag, text, className) {
  const element = document.createElement(tag);
  element.textContent = text;
  if (className) element.className = className;
  return element;
}

function clearResult() {
  inFlight?.abort();
  results.replaceChildren();
  statusLine.textContent = "";
  submit.disabled = false;
}

for (const button of nav) {
  button.addEventListener("click", () => {
    clearResult();
    mode = button.dataset.mode;
    for (const item of nav) {
      item.classList.toggle("active", item === button);
      item.setAttribute("aria-pressed", String(item === button));
    }
    const investigate = mode === "investigar";
    byId("investigate").hidden = !investigate;
    byId("frequency").hidden = investigate;
    byId("heading").textContent = investigate ? "O que os clientes relatam?" : "Quais temas aparecem?";
    byId("subtitle").textContent = investigate
      ? "Faça uma pergunta e confira as avaliações que sustentam a resposta."
      : "Compare as menções a temas predefinidos entre os pedidos com avaliação textual.";
    submit.textContent = investigate ? "Analisar avaliações" : "Contar menções";
  });
}

byId("filters").addEventListener("change", clearResult);
for (const button of document.querySelectorAll("[data-example]")) {
  button.addEventListener("click", () => {
    byId("question").value = button.dataset.example;
    byId("question").focus();
  });
}

function render(data) {
  statusLine.textContent = data.message + " " + data.eligible + " avaliações no recorte.";
  if (data.findings.length) results.append(node("h2", data.status === "contagem" ? "Temas por volume" : "Achados"));
  for (const finding of data.findings) {
    const card = node("article", "", "finding");
    card.append(node("p", finding.texto));
    for (const source of finding.fontes) {
      const link = node("a", "“" + source.trecho + "” · " + source.id, "citation");
      link.href = "#" + source.id;
      link.addEventListener("click", () => { byId(source.id).open = true; });
      card.append(link);
    }
    results.append(card);
  }
  if (data.evidence.length) {
    results.append(node("h2", data.status === "contagem" ? "Exemplos de menções" : "Avaliações recuperadas"));
  }
  for (const doc of data.evidence) {
    const detail = node("details", "");
    detail.id = doc.id;
    detail.append(node("summary", "Nota " + doc.score + " · " + doc.id));
    detail.append(node("blockquote", doc.text));
    const metadata = ["Avaliação original " + doc.review_id, "Pedido " + doc.order_id];
    if (doc.purchase_date) metadata.push("Compra " + doc.purchase_date);
    if (doc.delay_days !== null) metadata.push("Desvio do prazo: " + doc.delay_days + " dias");
    if (doc.semantic !== undefined) metadata.push("Cosseno " + doc.semantic + " · lexical " + doc.lexical);
    detail.append(node("p", metadata.join(" · "), "meta"));
    results.append(detail);
  }
}

byId("query").addEventListener("submit", async event => {
  event.preventDefault();
  clearResult();
  const question = byId("question").value.trim();
  if (mode === "investigar" && question.length < 5) {
    statusLine.textContent = "Digite uma pergunta de pelo menos cinco caracteres.";
    byId("question").focus();
    return;
  }
  const [min_score, max_score] = byId("rating").value.split(",").map(Number);
  const controller = new AbortController();
  inFlight = controller;
  submit.disabled = true;
  statusLine.textContent = mode === "investigar" ? "Buscando avaliações e consultando o modelo…" : "Contando menções…";
  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      signal: controller.signal,
      body: JSON.stringify({question, mode: mode === "investigar" ? mode : byId("theme").value,
        min_score, max_score, year: byId("year")?.value, delayed: byId("delayed")?.checked ?? false})
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Falha na consulta.");
    if (!controller.signal.aborted) render(data);
  } catch (error) {
    if (!controller.signal.aborted) statusLine.textContent = error.message;
  } finally {
    if (inFlight === controller) {
      submit.disabled = false;
      inFlight = null;
    }
  }
});
