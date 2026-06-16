"""Anki note model templates and styling.

This module contains only static Anki card layout data. Keeping the HTML/CSS
outside the API client makes the Anki client easier to read and lets the card
layout evolve independently from AnkiConnect request logic.
"""

MODEL_NAME = "AI Vocabulary Light Card"

MODEL_FIELDS = [
        "Word",
        "Language",
        "PartOfSpeech",
        "TranslationPL",
        "Definition",
        "Example",
        "ExamplePL",
        "Synonyms",
        "Collocations",
        "GrammarNote",
    ]

LEGACY_MODEL_NAME = "AI Vocabulary Light Card · Migrated"

LEGACY_MODEL_FIELDS = ["Front", "Back"]

FRONT_TEMPLATE = """
<div class="vocab-card front">
  <div class="language-badge">{{Language}} · {{PartOfSpeech}}</div>
  <div class="word">{{Word}}</div>
  <div class="prompt">Show answer</div>
</div>
""".strip()

BACK_TEMPLATE = """
<div class="vocab-card back">
  <div class="language-badge">{{Language}} · {{PartOfSpeech}}</div>
  <div class="word small">{{Word}}</div>
  {{#TranslationPL}}<div class="translation">{{TranslationPL}}</div>{{/TranslationPL}}

  <section class="section definition">
    <div class="label">Definition</div>
    <div class="content">{{Definition}}</div>
  </section>

  <section class="section example">
    <div class="label">Example</div>
    <div class="sentence">{{Example}}</div>
    {{#ExamplePL}}<div class="translation-example">{{ExamplePL}}</div>{{/ExamplePL}}
  </section>

  <section class="section">
    <div class="label">Useful phrases</div>
    <div class="chips">{{Collocations}}</div>
  </section>

  <section class="section">
    <div class="label">Similar words</div>
    <div class="chips secondary">{{Synonyms}}</div>
  </section>

  {{#GrammarNote}}
  <section class="section grammar">
    <div class="label">Grammar / usage</div>
    <div class="content">{{GrammarNote}}</div>
  </section>
  {{/GrammarNote}}
</div>
""".strip()

LEGACY_FRONT_TEMPLATE = """
<div class="vocab-card front">
  <div id="legacy-front-source" class="hidden-source">{{Front}}</div>
  <div id="legacy-front-badge" class="language-badge"></div>
  <div id="legacy-front-word" class="word"></div>
  <div class="prompt">Show answer</div>
</div>
<script>
(function () {
  const source = document.getElementById("legacy-front-source");
  const word = source.querySelector("b");
  const badge = source.querySelector("i");
  document.getElementById("legacy-front-word").innerHTML =
    word ? word.innerHTML : source.innerHTML;
  document.getElementById("legacy-front-badge").innerHTML =
    badge ? badge.innerHTML : "Vocabulary";
})();
</script>
""".strip()

LEGACY_BACK_TEMPLATE = r"""
<div class="vocab-card back">
  <div id="legacy-back-front" class="hidden-source">{{Front}}</div>
  <div id="legacy-back-source" class="hidden-source">{{Back}}</div>

  <div id="legacy-back-badge" class="language-badge"></div>
  <div id="legacy-back-word" class="word small"></div>
  <div id="legacy-translation" class="translation"></div>

  <section class="section definition">
    <div class="label">Definition</div>
    <div id="legacy-definition" class="content"></div>
  </section>

  <section class="section example">
    <div class="label">Example</div>
    <div id="legacy-example" class="content"></div>
  </section>

  <section class="section">
    <div class="label">Useful phrases</div>
    <div id="legacy-collocations" class="chips"></div>
  </section>

  <section class="section">
    <div class="label">Similar words</div>
    <div id="legacy-synonyms" class="chips secondary"></div>
  </section>

  <section class="section grammar">
    <div class="label">Grammar / usage</div>
    <div id="legacy-grammar" class="content"></div>
  </section>
</div>
<script>
(function () {
  const front = document.getElementById("legacy-back-front");
  const word = front.querySelector("b");
  const badge = front.querySelector("i");
  document.getElementById("legacy-back-word").innerHTML =
    word ? word.innerHTML : front.innerHTML;
  document.getElementById("legacy-back-badge").innerHTML =
    badge ? badge.innerHTML : "Vocabulary";

  const html = document.getElementById("legacy-back-source").innerHTML;
  const labels = [
    "Definition:", "PL:", "Example:", "Synonyms / alternatives:",
    "Collocations / usage:", "Grammar note:"
  ];

  function section(label, nextLabel) {
    const startMarker = "<b>" + label + "</b>";
    const start = html.indexOf(startMarker);
    if (start < 0) return "";
    const contentStart = start + startMarker.length;
    const endMarker = nextLabel ? "<b>" + nextLabel + "</b>" : null;
    const end = endMarker ? html.indexOf(endMarker, contentStart) : html.length;
    return html.slice(contentStart, end < 0 ? html.length : end)
      .replace(/^(\s|<br\s*\/?\s*>)+/gi, "")
      .replace(/(\s|<br\s*\/?\s*>)+$/gi, "")
      .trim();
  }

  function chipsFromHtml(raw, mode) {
    const wrapper = document.createElement("div");
    wrapper.innerHTML = raw.replace(/<br\s*\/?\s*>/gi, "\n");
    const text = wrapper.textContent || "";
    const parts = mode === "comma"
      ? text.split(",")
      : text.split(/\n|•/);
    return parts.map(function (item) { return item.trim(); })
      .filter(Boolean)
      .map(function (item) {
        const span = document.createElement("span");
        span.className = "chip";
        span.textContent = item;
        return span.outerHTML;
      }).join(" ");
  }

  document.getElementById("legacy-definition").innerHTML =
    section(labels[0], labels[1]);
  document.getElementById("legacy-translation").innerHTML =
    section(labels[1], labels[2]);
  document.getElementById("legacy-example").innerHTML =
    section(labels[2], labels[3]);
  document.getElementById("legacy-synonyms").innerHTML =
    chipsFromHtml(section(labels[3], labels[4]), "comma");
  document.getElementById("legacy-collocations").innerHTML =
    chipsFromHtml(section(labels[4], labels[5]), "bullets");
  document.getElementById("legacy-grammar").innerHTML =
    section(labels[5], null);
})();
</script>
""".strip()

CARD_CSS = """
/* This card deliberately stays light, also in Anki night mode. */
.card,
.nightMode.card,
.night_mode.card {
  color: #24324a !important;
  background: #f5f7fb !important;
}

.card {
  font-family: "Segoe UI", "Inter", Arial, sans-serif;
  color: #24324a !important;
  background: #f5f7fb !important;
  text-align: left;
  padding: 18px;
}

.hidden-source {
  display: none;
}

.vocab-card {
  max-width: 620px;
  margin: 0 auto;
  padding: 32px;
  border-radius: 24px;
  color: #24324a !important;
  background: #ffffff !important;
  border: 1px solid #e7edf5;
  box-shadow: 0 10px 30px rgba(31, 55, 88, 0.08);
}

.front {
  min-height: 260px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.language-badge {
  display: inline-block;
  padding: 7px 13px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: #2463c5 !important;
  background: #eaf2ff !important;
}

.word {
  margin: 30px 0 24px;
  font-size: 44px;
  line-height: 1.16;
  font-weight: 700;
  color: #17253c !important;
  text-align: center;
}

.word.small {
  margin: 20px 0 4px;
  font-size: 36px;
  text-align: left;
}

.translation {
  margin-bottom: 28px;
  color: #2463c5 !important;
  font-size: 22px;
  font-weight: 600;
}

.prompt {
  padding-top: 18px;
  color: #8492a8 !important;
  font-size: 13px;
  font-weight: 500;
}

.section {
  margin-top: 15px;
  padding: 16px 18px;
  border: 1px solid #ebf0f7;
  border-radius: 15px;
  color: #24324a !important;
  background: #fbfcff !important;
}

.section.example {
  background: #eff6ff !important;
  border-color: #dceafe;
}

.section.grammar {
  background: #f8fafc !important;
}

.label {
  margin-bottom: 8px;
  color: #6d7e96 !important;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.content,
.sentence {
  font-size: 16px;
  line-height: 1.45;
}

.sentence {
  font-weight: 600;
}

.translation-example {
  margin-top: 7px;
  color: #66758b !important;
  font-size: 14px;
  font-style: italic;
}

.chip {
  display: inline-block;
  margin: 4px 5px 2px 0;
  padding: 7px 11px;
  border-radius: 999px;
  background: #eaf2ff !important;
  color: #245db5 !important;
  font-size: 13px;
  font-weight: 500;
}

.secondary .chip {
  background: #edf1f6 !important;
  color: #4c5c73 !important;
}

.mobile .card {
  padding: 10px;
}

.mobile .vocab-card {
  padding: 23px 20px;
}

.mobile .word {
  font-size: 35px;
}
""".strip()



GRAMMAR_MODEL_NAME = "AI Grammar Light Card"

GRAMMAR_MODEL_FIELDS = [
    "Sentence",
    "Language",
    "Meaning",
    "Structure",
    "Breakdown",
    "Usage",
    "ContextExample",
    "Contrasts",
    "CommonMistakes",
]

GRAMMAR_FRONT_TEMPLATE = """
<div class="vocab-card front grammar-front">
  <div class="language-badge">{{Language}} · grammar structure</div>
  <div class="word grammar-sentence">{{Sentence}}</div>
  <div class="prompt">Show explanation</div>
</div>
""".strip()

GRAMMAR_BACK_TEMPLATE = """
<div class="vocab-card back">
  <div class="language-badge">{{Language}} · grammar structure</div>
  <div class="word small grammar-sentence-small">{{Sentence}}</div>
  <div class="translation grammar-meaning">{{Meaning}}</div>

  <section class="section grammar">
    <div class="label">Structure</div>
    <div class="structure-pill">{{Structure}}</div>
  </section>

  <section class="section">
    <div class="label">How it works</div>
    <div class="grammar-list">{{Breakdown}}</div>
  </section>

  <section class="section">
    <div class="label">When to use it</div>
    <div class="content">{{Usage}}</div>
  </section>

  <section class="section example">
    <div class="label">Natural context</div>
    <div class="sentence">{{ContextExample}}</div>
  </section>

  <section class="section">
    <div class="label">Contrast</div>
    <div class="grammar-list">{{Contrasts}}</div>
  </section>

  <section class="section grammar-warning">
    <div class="label">Common mistakes</div>
    <div class="grammar-list">{{CommonMistakes}}</div>
  </section>
</div>
""".strip()

GRAMMAR_CARD_CSS = CARD_CSS + """

.grammar-sentence {
  max-width: 540px;
  font-size: 38px;
}

.grammar-sentence-small {
  font-size: 30px;
  line-height: 1.25;
}

.grammar-meaning {
  font-size: 20px;
  line-height: 1.45;
}

.structure-pill {
  display: inline-block;
  padding: 7px 11px;
  border-radius: 999px;
  background: #eaf2ff !important;
  color: #245db5 !important;
  font-size: 14px;
  font-weight: 600;
}

.grammar-list-item {
  margin-top: 8px;
  padding: 10px 12px;
  border-radius: 11px;
  background: #ffffff !important;
  border: 1px solid #edf1f6;
  font-size: 15px;
  line-height: 1.45;
}

.grammar-list-item:first-child {
  margin-top: 0;
}

.grammar-warning {
  background: #fff8f1 !important;
  border-color: #f6dfc6;
}
""".strip()
