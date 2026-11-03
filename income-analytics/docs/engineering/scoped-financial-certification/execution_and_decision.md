# Execução e decisão — certificação restrita PR69/62

## Resultado local e controles

- Escopo funcional/dependências: **394 PASS, 0 FAIL, 0 ERROR, 0 SKIP**.
- Controles finais de governança/certificação/escopo/segurança: **204 PASS**.
  Há sobreposição com outras suítes; os totais não devem ser somados.
- Três exemplos independentes adicionais: Selic, IPCA+ e Prefixado, com
  compra de 0,17 título a 1234,567891 e venda de 0,04 a 1300,123456.
  Quantidade final **0,13**, custo **160,49382583**, resultado realizado
  **2,62222260**, valor de mercado **195,00** a preço 1500 e resultado total
  **37,12839677**. Valor bruto validado em centavos HALF_UP; precisão interna
  preservada, sem arredondar indevidamente o custo do domínio.
- Reconstrução real do snapshot, sem stub de preços/ranking, preservou a classe
  financeira FIXED_INCOME, o grupo visual TREASURY e o histórico.
- Todos os 41 arquivos imutáveis conferidos com o inventário anterior do #62.
- Rastreamento do processo principal **e dos workers FastAPI** exercitou todos os
  módulos/funções obrigatórios; zero chamada financeira aos três módulos CERT_48.
  As definições importadas constam separadamente e não foram apagadas.
- Financial abrangente: **184 PASS, 15 FAIL, 9 ERROR, 0 SKIP**. São as mesmas
  24 identidades/causas históricas; os três casos independentes novos passaram.
  O estado abrangente continua BLOCKED, sem relabelar falhas como aprovações.

Uma execução local intermediária detectou corretamente `ENTRYPOINT_NOT_EXERCISED`
para a rota de aplicação B3: FastAPI executa essa rota em worker, fora do profiler
inicial do processo principal. A instrumentação foi ampliada aos workers criados
após o hook; a execução seguinte comprovou a chamada. Uma edição concorrente do
conteúdo também gerou `SOURCE_CHANGED_DURING_CERTIFICATION`, exigindo repetição.
Esses checkpoints não são evidências aprovadas. Nenhuma assertion foi afrouxada.

## Reproduzir

Com o ambiente Python 3.14 do lock já instalado, a partir da raiz da aplicação:

```powershell
python ci/governance.py financial --reports <diretorio-de-evidencias>
```

O job existente continua executando todos os testes financeiros/históricos.
Em seguida executa a certificação restrita e publica no mesmo artifact
`result.json`, `financial-junit.xml`, `scoped-junit.xml`, `scoped-financial.json`
e inventário. O comando retorna reprovação enquanto o gate financeiro abrangente
estiver bloqueado; o resultado técnico restrito é campo independente.

Para repetir somente o parecer técnico usando um relatório histórico preservado:

```powershell
python ci/scoped_financial.py --historical-report <financial/result.json> --output <diretorio>
```

Esse segundo comando retorna a situação **técnica**, nunca uma autorização
financeira. O SHA da evidência histórica é informado separadamente; para decisão
final exigir o relatório integrado da CI hospedada no commit candidato. Não se
aceita substituir a execução histórica atual por uma execução antiga.

O SHA de checkout, identidade de política, fingerprint de execução e run GitHub
continuam registrados no envelope de governança. A avaliação restrita registra
também a identidade do conteúdo, bloqueando alteração durante a execução. Os
documentos de escopo e o inventário estão vinculados ao fingerprint da política.
Resultados hospedados e links do commit final são registrados no PR #69 para
evitar uma cadeia circular de commits que tentem registrar seu próprio SHA.

## Gate decisório e ativação

O novo componente é **REVIEW_ONLY** e não contém botão de aceite nem caminho de
deploy. A proposta deixa os 24 casos históricos fora da lista funcional incluída,
mantendo seus resultados e issues. A retirada efetiva desses bloqueios do gate
decisório depende do parecer independente exigido pelo proprietário. Até lá,
`financial_release_decision=NO_GO` e os gates ativos ficam preservados.

Após revisão independente verificável do pacote/SHA, a ativação deverá ser uma
mudança separada revisável que vincule a decisão ao conteúdo aprovado e mantenha
falhas novas/dependências não certificadas/segurança bloqueantes. Não se autoriza
um bypass genérico do Financial por contagem, prefixo de módulo ou status histórico.

O proprietário informou **não ter revisor financeiro definido**. Portanto:

**Parecer técnico: PASS nas evidências executadas. Decisão financeira: NO-GO,
aguardando aprovação independente da não aplicabilidade/escopo.**

Isso não exige recuperar os históricos para sempre dentro deste trabalho. As
recuperações continuam no backlog #57/#58; a pendência deste release é uma decisão
concreta de aplicabilidade. Não houve merge, deploy, migração destrutiva ou mudança
de processos produtivos. O staging descartável não certifica restauração produtiva.
