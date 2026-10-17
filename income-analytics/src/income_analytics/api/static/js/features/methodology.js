import { escapeConceptHtml, financialConcepts, methodologySections } from "../shared/financial-concepts.js";

export function setupMethodologyPage() {
  const explanation = document.querySelector("#performance-methodology-copy");
  if (explanation) explanation.textContent = financialConcepts.returnTooltip;
  const returnLink = document.querySelector(".performance-methodology-link");
  if (returnLink) returnLink.href = financialConcepts.returnMethodologyHref;
  const nav = document.querySelector(".primary-nav");
  if (nav && !nav.querySelector('[href="#ajuda-metodologia"]')) {
    nav.insertAdjacentHTML("beforeend", '<a href="#ajuda-metodologia" data-navigate title="Ajuda e metodologia">Ajuda e metodologia</a>');
  }
  const main = document.querySelector("main");
  if (!main || document.querySelector('[data-page="ajuda-metodologia"]')) return;
  const sections = methodologySections.map(section => `
    <section class="card methodology-section" id="${escapeConceptHtml(section.id)}">
      <p class="eyebrow">Como calculamos</p><h2>${escapeConceptHtml(section.title)}</h2>
      ${section.questions.map(item => `<article><h3>${escapeConceptHtml(item.question)}</h3><p>${escapeConceptHtml(item.answer)}</p></article>`).join("")}
    </section>`).join("");
  main.insertAdjacentHTML("beforeend", `<section class="page methodology-page" data-page="ajuda-metodologia" aria-labelledby="methodology-title" hidden>
    <div class="page-intro"><p class="eyebrow">Critérios financeiros do Income</p><h1 id="methodology-title">Ajuda e metodologia</h1><p>Entenda o que cada indicador da carteira representa e quais dados usamos nos cálculos.</p></div>
    <nav class="methodology-index" aria-label="Tópicos da metodologia">${methodologySections.map(section => `<a href="#ajuda-metodologia/${escapeConceptHtml(section.id)}" data-navigate>${escapeConceptHtml(section.title)}</a>`).join("")}</nav>
    ${sections}
  </section>`);
}

