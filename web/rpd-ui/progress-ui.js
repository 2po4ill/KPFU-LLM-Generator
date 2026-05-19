/**
 * Generation progress hotbar (SSE steps from /generate-package/stream).
 */
(function () {
  const PACKAGE_STEPS = [
    { id: "init", label: "Старт" },
    { id: "step1_user_sources", label: "Ваши источники" },
    { id: "step1_pages", label: "Страницы учебника" },
    { id: "step2_rag", label: "RAG / лекция" },
    { id: "step2_facets", label: "Разделы лекции" },
    { id: "step3_validate", label: "Проверка" },
    { id: "step3_pptx", label: "Презентация" },
    { id: "done", label: "Готово" },
  ];

  let stepState = {};
  let lastDetail = "";

  function $p(id) {
    return document.getElementById(id);
  }

  function reset() {
    stepState = {};
    lastDetail = "";
    PACKAGE_STEPS.forEach((s) => {
      stepState[s.id] = "pending";
    });
    render();
    $p("progressDetail")?.replaceChildren();
    const bar = $p("progressBarFill");
    if (bar) bar.style.width = "0%";
    const pct = $p("progressPct");
    if (pct) pct.textContent = "";
    const feed = $p("progressFeed");
    if (feed) feed.innerHTML = "";
    $p("progressPanel")?.classList.add("hidden");
  }

  function show() {
    $p("progressPanel")?.classList.remove("hidden");
  }

  function render() {
    const list = $p("progressSteps");
    if (!list) return;
    list.innerHTML = PACKAGE_STEPS.map((s) => {
      const st = stepState[s.id] || "pending";
      const icon =
        st === "done" ? "✓" : st === "active" ? "●" : st === "error" ? "!" : "○";
      return (
        `<li class="progress-step progress-step--${st}" data-step="${s.id}">` +
        `<span class="progress-step__icon" aria-hidden="true">${icon}</span>` +
        `<span class="progress-step__label">${s.label}</span>` +
        `</li>`
      );
    }).join("");
  }

  function appendFeed(message, detail) {
    const feed = $p("progressFeed");
    if (!feed) return;
    const line = document.createElement("div");
    line.className = "progress-feed__line";
    const t = new Date().toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    line.textContent = `[${t}] ${message}${detail ? " — " + detail : ""}`;
    feed.appendChild(line);
    feed.scrollTop = feed.scrollHeight;
    while (feed.children.length > 40) feed.removeChild(feed.firstChild);
  }

  function applyEvent(ev) {
    const stepId = ev.step_id || "";
    const status = ev.status || "active";
    const pct = typeof ev.pct === "number" ? ev.pct : null;

    if (stepId === "error") {
      stepState.done = "error";
      PACKAGE_STEPS.forEach((s) => {
        if (stepState[s.id] === "active") stepState[s.id] = "error";
      });
    } else if (stepId) {
      const idx = PACKAGE_STEPS.findIndex((s) => s.id === stepId);
      if (idx >= 0) {
        for (let i = 0; i < idx; i++) {
          if (stepState[PACKAGE_STEPS[i].id] !== "error") {
            stepState[PACKAGE_STEPS[i].id] = "done";
          }
        }
        stepState[stepId] = status === "done" ? "done" : status === "error" ? "error" : "active";
        if (status === "done") stepState[stepId] = "done";
      }
    }

    const msg = ev.message || stepId;
    const detail = ev.detail || "";
    lastDetail = detail || lastDetail;
    const detailEl = $p("progressDetail");
    if (detailEl) {
      detailEl.textContent = [msg, detail].filter(Boolean).join(" · ");
    }
    appendFeed(msg, detail);

    if (pct != null) {
      const bar = $p("progressBarFill");
      if (bar) bar.style.width = `${Math.min(100, Math.max(0, pct))}%`;
      const pctEl = $p("progressPct");
      if (pctEl) pctEl.textContent = `${Math.round(pct)}%`;
    }
    render();
  }

  async function streamGeneratePackage(url, body, headers) {
    const res = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || `HTTP ${res.status}`);
    }
    if (!res.body) throw new Error("Streaming not supported");

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let finalResult = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const chunks = buffer.split("\n\n");
      buffer = chunks.pop() || "";
      for (const chunk of chunks) {
        for (const line of chunk.split("\n")) {
          if (!line.startsWith("data: ")) continue;
          let data;
          try {
            data = JSON.parse(line.slice(6));
          } catch {
            continue;
          }
          if (data.type === "progress") applyEvent(data);
          else if (data.type === "done") finalResult = data.result;
          else if (data.type === "error") throw new Error(data.message || "Ошибка генерации");
        }
      }
    }

    if (!finalResult) throw new Error("Поток завершился без результата");
    return finalResult;
  }

  window.ProgressUI = {
    PACKAGE_STEPS,
    reset,
    show,
    applyEvent,
    streamGeneratePackage,
  };
})();
