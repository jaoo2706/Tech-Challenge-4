# Roteiro de apresentação — Tech Challenge 4

**Duração-alvo · 6 min 30 s**  
**Formato · gravação de tela com narração**

## Preparação da gravação

- Use o índice oficial já preparado. Confirme que o painel mostra **Base histórica da Olist** e rode uma pergunta para aquecer o Ollama. Os comandos estão no [README](README.md).
- Prepare as abas antes de gravar. Deixe abertas a arquitetura renderizada no README, a investigação, a frequência e a avaliação.
- Experimente as duas perguntas da demonstração e deixe as respostas abertas em abas separadas. Escolha ao menos uma citação que sustente diretamente a frase. Deixe aberta a consulta sobre garantia de cinco anos para celulares, com todas as notas. Se houver resposta sem suporte, mostre o resultado como falha observada ou escolha outra pergunta já testada para demonstrar a abstenção.
- Durante o vídeo, leia apenas as falas. As ações indicam o que deve estar na tela. Faça os cliques em pausas curtas e corte a espera da geração, se necessário.

## 0:00–0:45 · Problema de negócio

**Tela.** Abra o painel na tela inicial e aponte para a pergunta e o filtro de nota.

**Fala.** “Oi, eu sou João Vitor Ochiliski Ribeiro. Este é o Voice of Customer Intelligence, projeto da Fase 4. Imagine que o time de logística percebe uma queda nas avaliações e quer entender o que mudou. A nota sinaliza insatisfação, mas o comentário mostra se o cliente esperou mais do que o prometido, se o pedido nem chegou ou se o problema foi outro. Ler milhares de avaliações manualmente demora e dificulta a investigação. A proposta é fazer uma pergunta em linguagem natural e poder voltar ao relato original para conferir o achado.”

## 0:45–1:35 · Preparação da base

**Tela.** Mostre o início da arquitetura e a seção de preparação do README.

**Fala.** “Usamos o histórico público da Olist e indexamos 42.555 avaliações com texto. Cruzamos as avaliações e os pedidos pelo identificador do pedido. Juntamos título e comentário quando esses campos existem, limpamos o texto e removemos linhas sem conteúdo útil e duplicações no mesmo pedido. Cada documento corresponde a uma avaliação, para que o sentido do comentário curto fique preservado. Guardamos a nota, as datas, o ID original e a diferença entre a entrega prevista e a efetiva. Isso permite investigar, por exemplo, somente pedidos com atraso registrado e nota baixa.”

## 1:35–2:30 · Recuperação e geração

**Tela.** Siga no diagrama da pergunta até a validação das fontes.

**Fala.** “A busca primeiro aplica os filtros e depois compara a pergunta às avaliações do recorte. Na configuração principal, o Multilingual E5 representa consultas e comentários em vetores. A similaridade vetorial ajuda a encontrar aproximações de significado. A busca lexical complementa isso com palavras e expressões que aparecem nos comentários. Combinamos a posição das duas listas e selecionamos até oito avaliações, ou 16 numa pergunta panorâmica, buscando diversidade de pedidos. O modelo local recebe a pergunta e os trechos identificados. Cada achado volta com uma citação verificável. O código confere se o ID foi enviado ao modelo e extrai a citação do comentário original.”

## 2:30–3:45 · Demonstração com fontes

**Tela.** No modo **Investigar avaliações**, escolha notas **1 e 2**. Use a pergunta “Quais avaliações mencionam que o pedido não chegou?”. Clique numa citação e mostre o texto, a nota e o ID do pedido. Em outra aba, escolha notas **4 e 5** e mostre “O que os clientes elogiam sobre a qualidade dos produtos?”.

**Fala.** “Vou começar pelas notas baixas e perguntar sobre pedidos que não chegaram. O resultado traz um achado e um trecho da avaliação que o sustenta. Abrindo a fonte eu vejo o comentário preparado, a nota e o identificador do pedido. Na prática, consigo conferir se o cliente relatou que não recebeu ou se apenas reclamou da demora. Mudo o recorte para notas altas e pergunto sobre a qualidade do produto. O mesmo fluxo recupera evidências para elogios e me permite conferir a expressão usada pelo cliente.”

**Ação.** Leia uma citação curta de cada consulta a partir do que de fato apareceu no painel. Dê espaço para a banca ver os IDs.

## 3:45–4:35 · Frequência por recorte

**Tela.** Abra **Frequência de temas**, selecione **Reclamações**, notas **1 e 2**, marque **Apenas entregas atrasadas** e faça a consulta. Abra um exemplo de menção.

**Fala.** “Para saber com que frequência um tema aparece, usamos todos os pedidos com texto nesse recorte. Aqui o filtro exige nota baixa e atraso registrado nas datas. A contagem procura expressões explícitas de um conjunto de temas e cada pedido entra uma vez por tema. O denominador é o total de pedidos com comentário que passou pelo filtro. Um mesmo pedido pode mencionar vários temas. Esse resultado ajuda a priorizar o que investigar, com a cobertura do dicionário que está descrita no projeto.”

## 4:35–5:20 · Pergunta sem resposta

**Tela.** Retorne a **Investigar avaliações**, limpe os filtros e mostre “Quais avaliações mencionam a garantia estendida de cinco anos para celulares?”. Se houver tempo, mostre também “Qual era a margem de lucro da Olist?”.

**Fala.** “Também testamos perguntas que a base não consegue responder. Há avaliações sobre garantia estendida, mas elas não comprovam a combinação de cinco anos e celulares. A busca recupera textos próximos; a triagem e a checagem dos detalhes da pergunta evitam usar uma garantia diferente como prova. Se a pergunta for sobre dados internos, como margem de lucro, a base também não serve. Cada citação é extraída do comentário original, e uma checagem adicional tenta verificar se ela sustenta o achado. Ainda conferimos a coerência pela leitura.”

## 5:20–6:30 · Avaliação e conclusão

**Tela.** Mostre as métricas no README. Volte ao painel na última frase.

**Fala.** “Na demo, a busca recuperou cerca de 66% dos pedidos relevantes entre os cinco primeiros resultados. Na base real, com rótulos automáticos, a híbrida obteve o melhor MRR, 0,83. Essa medida valoriza encontrar uma avaliação pertinente logo nas primeiras posições. Nessa comparação, até a busca lexical passou pelo filtro mínimo do E5. O maior desafio foi distinguir assunto parecido de evidência suficiente, como vimos na pergunta sobre garantia. Na checagem final com seis perguntas, três receberam respostas com citações e três ficaram sem resposta por falta de evidência ou por estarem fora do escopo. Assim, o time de logística pode investigar o problema e conferir o relato antes de agir.”

## Se a banca perguntar

| Pergunta | Resposta curta |
| --- | --- |
| Por que usar uma avaliação por documento? | Os relatos são curtos e a avaliação inteira preserva o contexto e o vínculo com pedido e nota. |
| Qual é a diferença entre atraso declarado e medido? | O atraso medido compara as datas operacionais. O declarado aparece como expressão no comentário. |
| Por que dois mecanismos de busca? | A lexical captura termos específicos. A vetorial aproxima consultas e relatos por similaridade. A demo LSA deu empate nas médias. |
| As citações garantem que a resposta está correta? | A validação extrai o trecho do contexto e confere o vínculo com o ID. Uma segunda checagem automática avalia se o trecho apoia o achado, mas a pertinência ainda exige avaliação humana. |
| O que os 66% representam? | Recall@5 médio nos sete casos positivos rotulados da demo sintética. |

## Checklist de submissão

- [x] Índice oficial com E5 construído: 42.555 avaliações de 42.421 pedidos.
- [x] Perguntas validadas no Ollama com a base real (veja `reports/exemplos_olist.json`). Reconfira antes de gravar, pois a saída do modelo pode variar um pouco.
- [ ] Grave com a base real. Se mostrar a demo sintética, avise em voz alta que os dados são sintéticos.
- [ ] Publicar este projeto em um repositório público. O arquivo `.gitignore` exclui credenciais locais, CSVs brutos e índices.
- [ ] Gravar, assistir ao vídeo final e confirmar duração de até sete minutos, áudio e legibilidade das evidências.
- [ ] Testar os links do repositório e do vídeo fora da sessão autenticada antes do envio.
