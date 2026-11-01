/* Mock exam site engine. Static: reads catalog.json + exams/<subject>/<lesson>/set-<v>.json.
   All content is inserted as text (never innerHTML) so exam JSON can't inject markup. */
(function () {
  "use strict";

  const app = document.getElementById("app");
  const page = document.body.dataset.page;
  const params = new URLSearchParams(location.search);

  // ---------- tiny DOM helper ----------
  function h(tag, attrs, ...kids) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === null || v === undefined || v === false) continue;
      if (k === "class") el.className = v;
      else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? "" : v);
    }
    for (const kid of kids.flat(Infinity)) {
      if (kid === null || kid === undefined || kid === false) continue;
      el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
    }
    return el;
  }

  function mount(...kids) {
    app.replaceChildren(...kids.flat(Infinity).filter((k) => k !== null && k !== undefined && k !== false));
  }

  // ---------- storage (per-browser attempt history; optional) ----------
  const store = {
    get(key) { try { return JSON.parse(localStorage.getItem(key) || "null"); } catch (e) { return null; } },
    set(key, val) { try { localStorage.setItem(key, JSON.stringify(val)); } catch (e) { /* ignore */ } },
  };
  const histKey = (s, l, v) => `mx:hist:${s}/${l}/${v}`;

  async function getJSON(url) {
    const r = await fetch(url, { cache: "no-cache" });
    if (!r.ok) throw new Error(`${url} → ${r.status}`);
    return r.json();
  }

  function masthead(site, crumbs) {
    document.title = crumbs && crumbs.length ? `${crumbs[crumbs.length - 1].text} · ${site.title}` : site.title;
    return [
      crumbs && crumbs.length
        ? h("div", { class: "crumbs" }, crumbs.map((c, i) => [i ? " / " : "", c.href ? h("a", { href: c.href }, c.text) : c.text]))
        : null,
      h("h1", {}, site.title),
      h("p", { class: "tagline" }, site.tagline),
    ];
  }

  function footer(site) {
    return h("footer", {}, `${site.title} — attempts are stored only in this browser.`);
  }

  function sourceLabel(type, owner) {
    if (type === "official") return "Official Notes";
    if (type === "personal") return `${owner || "My"}'s Personal Notes`;
    if (type === "lecturer") return "Lecturer's Words";
    return type;
  }

  function letter(pct) {
    if (pct >= 80) return "A";
    if (pct >= 70) return "B";
    if (pct >= 60) return "C";
    if (pct >= 50) return "D";
    return "F";
  }

  function fail(err) {
    mount(h("p", { class: "empty" }, "Couldn't load this page: " + err.message));
  }

  // ---------- pages ----------
  async function renderIndex() {
    const cat = await getJSON("catalog.json");
    const subjects = cat.subjects || [];
    mount(
      ...masthead(cat.site),
      h("div", { class: "label" }, "Subjects & lecture series"),
      subjects.length
        ? h("ul", { class: "index" }, subjects.map((s) => {
            const n = (s.lessons || []).length;
            return h("li", {},
              h("div", {}, h("h2", {}, h("a", { href: `subject.html?s=${encodeURIComponent(s.slug)}` }, s.title)),
                s.description ? h("div", { class: "meta" }, s.description) : null),
              h("div", { class: "meta" }, `${n} mock exam${n === 1 ? "" : "s"}`));
          }))
        : h("p", { class: "empty" }, "No mock exams yet."),
      footer(cat.site)
    );
  }

  async function renderSubject() {
    const cat = await getJSON("catalog.json");
    const s = (cat.subjects || []).find((x) => x.slug === params.get("s"));
    if (!s) throw new Error("subject not found");
    const lessons = [...(s.lessons || [])].sort((a, b) => String(a.date || "").localeCompare(String(b.date || "")));
    mount(
      ...masthead(cat.site, [{ text: "Home", href: "index.html" }, { text: s.title }]),
      h("div", { class: "label" }, "Subject"),
      h("h2", {}, s.title),
      s.description ? h("p", { class: "muted" }, s.description) : null,
      h("div", { class: "label" }, "Mock exams"),
      lessons.length
        ? h("ul", { class: "index" }, lessons.map((l) => h("li", {},
            h("div", {},
              h("h3", {}, l.title),
              h("div", { class: "meta" }, [l.date, l.focus ? `focus: ${l.focus}` : null].filter(Boolean).join(" · ")),
              h("div", { class: "history" }, (l.variants || []).map((v) => {
                const hist = store.get(histKey(s.slug, l.slug, v)) || [];
                return hist.length ? `Set ${v.toUpperCase()}: best ${Math.max(...hist.map((x) => x.pct))}% (${hist.length}×)  ` : "";
              }).join("") || null)),
            h("div", { class: "sets" }, (l.variants || []).map((v) =>
              h("a", { href: `exam.html?s=${encodeURIComponent(s.slug)}&l=${encodeURIComponent(l.slug)}&v=${encodeURIComponent(v)}` }, `Set ${v.toUpperCase()}`))))))
        : h("p", { class: "empty" }, "No mock exams for this subject yet."),
      footer(cat.site)
    );
  }

  async function renderExam() {
    const s = params.get("s"), l = params.get("l"), v = params.get("v");
    const [cat, exam] = await Promise.all([
      getJSON("catalog.json"),
      getJSON(`exams/${encodeURIComponent(s)}/${encodeURIComponent(l)}/set-${encodeURIComponent(v)}.json`),
    ]);
    const owner = cat.site.owner;
    const srcById = Object.fromEntries((exam.sources || []).map((x) => [x.id, x]));
    const state = exam.sections.map((sec) => ({ submitted: false, marks: sec.questions.map(() => null), answers: [] }));

    const resultsBox = h("div");
    const resultsBtn = h("button", { class: "primary", disabled: true, onclick: showResults }, "See results");

    function refreshResultsBtn() {
      resultsBtn.disabled = !state.every((st) => st.submitted && st.marks.every((m) => m !== null));
    }

    function renderSection(sec, si) {
      const st = state[si];
      const qEls = sec.questions.map((q, qi) => {
        const num = h("span", { class: "q-num" }, `${qi + 1}.`);
        let input;
        if (sec.type === "mcq") {
          input = h("div", {}, q.options.map((opt, oi) =>
            h("label", { class: "opt" }, h("input", { type: "radio", name: `s${si}q${qi}`, value: oi }), h("span", {}, `${"ABCDEFGH"[oi]}. ${opt}`))));
        } else {
          input = h("textarea", { class: sec.type === "open" ? "open" : "", placeholder: sec.type === "open" ? "Write your answer…" : "Short answer…" });
        }
        const after = h("div");
        return { q, qi, input, after, el: h("div", { class: "q" }, h("div", { class: "q-prompt" }, num, q.prompt), input, after) };
      });

      const submit = h("button", { class: "primary" }, "Submit section");
      const status = h("span", { class: "small muted" });

      submit.addEventListener("click", () => {
        st.submitted = true;
        submit.disabled = true;
        qEls.forEach(({ q, qi, input, after }) => {
          if (sec.type === "mcq") {
            const picked = input.querySelector("input:checked");
            const pv = picked ? Number(picked.value) : null;
            st.answers[qi] = pv === null ? "(no answer)" : `${"ABCDEFGH"[pv]}. ${q.options[pv]}`;
            input.querySelectorAll("input").forEach((r) => (r.disabled = true));
            input.querySelectorAll(".opt").forEach((lab, oi) => {
              if (oi === q.answer) lab.classList.add("correct");
              else if (oi === pv) lab.classList.add("wrong");
            });
            st.marks[qi] = pv === q.answer ? 1 : 0;
            if (q.explanation) after.append(h("div", { class: "reveal" }, q.explanation));
          } else {
            st.answers[qi] = input.value.trim() || "(no answer)";
            input.disabled = true;
            const markRow = h("div", { class: "mark" });
            [["Correct", 1], ["Partial", 0.5], ["Wrong", 0]].forEach(([txt, val]) => {
              const b = h("button", { "data-v": val }, txt);
              b.addEventListener("click", () => {
                st.marks[qi] = val;
                markRow.querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === b));
                refreshStatus();
                refreshResultsBtn();
              });
              markRow.append(b);
            });
            after.append(h("div", { class: "reveal" },
              h("strong", {}, "Model answer: "), q.model_answer || "",
              q.key_points && q.key_points.length ? [h("div", { class: "small muted", style: "margin-top:8px" }, "Key points to look for:"), h("ul", {}, q.key_points.map((k) => h("li", {}, k)))] : null,
              h("div", { class: "small muted", style: "margin-top:8px" }, "Mark yourself honestly:"),
              markRow));
          }
        });
        refreshStatus();
        refreshResultsBtn();
      });

      function refreshStatus() {
        const pending = st.marks.filter((m) => m === null).length;
        status.textContent = pending ? `${pending} left to self-mark` : "section marked";
      }

      return h("section", { class: "section" },
        h("div", { class: "section-head" }, h("h2", {}, sec.title), h("span", { class: "small muted" }, `${sec.questions.length} question${sec.questions.length === 1 ? "" : "s"}`)),
        qEls.map((x) => x.el),
        h("div", { class: "actions" }, submit, status));
    }

    function showResults() {
      let got = 0, total = 0;
      const secRows = [], misses = [];
      exam.sections.forEach((sec, si) => {
        const st = state[si];
        const sGot = st.marks.reduce((a, b) => a + b, 0);
        got += sGot; total += sec.questions.length;
        const sp = Math.round((sGot / sec.questions.length) * 100);
        secRows.push(h("div", {},
          h("div", { class: "sec-score" }, h("span", {}, sec.title), h("span", {}, `${sGot}/${sec.questions.length}`)),
          h("div", { class: `bar${sp < 50 ? " low" : ""}` }, h("div", { style: `width:${sp}%` }))));
        sec.questions.forEach((q, qi) => {
          if (st.marks[qi] === 1) return;
          const c = q.citation || {};
          const src = srcById[c.source] || {};
          const correct = sec.type === "mcq" ? `${"ABCDEFGH"[q.answer]}. ${q.options[q.answer]}` : q.model_answer;
          misses.push(h("div", { class: "miss" },
            h("div", { class: `tag${st.marks[qi] === 0.5 ? " partial" : ""}` }, `${sec.title} · Q${qi + 1} · ${st.marks[qi] === 0.5 ? "partial" : "wrong"}`),
            h("p", { style: "font-weight:600;margin:4px 0" }, q.prompt),
            h("div", {}, h("span", { class: "muted" }, "Your answer: "), st.answers[qi]),
            h("div", {}, h("span", { class: "muted" }, "Correct answer: "), correct),
            q.explanation ? h("div", { style: "margin-top:6px" }, h("span", { class: "muted" }, "Why: "), q.explanation) : null,
            c.quote ? h("blockquote", {}, `From the notes: "${c.quote}"`,
              h("span", { class: "src" }, `— ${sourceLabel(src.type, owner)}${src.label ? ` (${src.label}${c.locator ? `, ${c.locator}` : ""})` : ""}`)) : null));
        });
      });
      const pct = Math.round((got / total) * 100);
      const hist = store.get(histKey(s, l, v)) || [];
      hist.push({ pct, at: new Date().toISOString() });
      store.set(histKey(s, l, v), hist);

      resultsBox.replaceChildren(h("div", { class: "results" },
        h("div", { class: "label", style: "margin-top:0" }, "Result"),
        h("div", { class: "grade" }, h("span", { class: "letter" }, letter(pct)), h("span", { class: "pct" }, `${pct}%`), h("span", { class: "muted small" }, `${got} / ${total} marks`)),
        h("div", { class: "label" }, "By section"), secRows,
        h("div", { class: "label" }, misses.length ? `Review (${misses.length})` : "Review"),
        misses.length ? misses : h("p", {}, "Full marks — nothing to review."),
        h("div", { class: "actions" }, h("button", { onclick: () => location.reload() }, "Retake"),
          h("a", { href: `subject.html?s=${encodeURIComponent(s)}` }, "Back to subject"))));
      resultsBtn.disabled = true;
      resultsBox.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    const subj = (cat.subjects || []).find((x) => x.slug === s) || { title: exam.subject.title };
    mount(
      ...masthead(cat.site, [{ text: "Home", href: "index.html" }, { text: subj.title, href: `subject.html?s=${encodeURIComponent(s)}` }, { text: `${exam.lesson.title} · Set ${String(v).toUpperCase()}` }]),
      h("div", { class: "label" }, `Mock exam · Set ${String(v).toUpperCase()}`),
      h("h2", {}, exam.lesson.title),
      h("p", { class: "muted small" }, `${exam.sections.reduce((a, x) => a + x.questions.length, 0)} questions · ${exam.sections.length} section${exam.sections.length === 1 ? "" : "s"}. MCQ is auto-marked; written answers are self-marked against a model answer.`),
      exam.focus ? h("div", { class: "focus" }, `Focus: ${exam.focus}`) : null,
      exam.sections.map(renderSection),
      h("hr", { class: "dither" }),
      h("div", { class: "actions" }, resultsBtn, h("span", { class: "small muted" }, "Submit and mark every section to unlock results.")),
      resultsBox,
      footer(cat.site)
    );
  }

  const run = { index: renderIndex, subject: renderSubject, exam: renderExam }[page];
  if (run) run().catch(fail);
})();
