/** Fixed production API (Tuna tunnel). */
const API_BASE_URL = "https://llm-generator.ru.tuna.am/api/v1";

const storage = {
  fingerprint: "rpd_ui_fingerprint",
};

const STATE_LABELS = {
  idle: "Готово",
  uploading: "Разбор РПД…",
  resolving: "Загрузка PDF…",
  refreshing: "Обновление…",
  generating: "Генерация пакета…",
};

let currentFingerprint = null;
let currentSession = null;
let selectedSourceIds = new Set();
let currentState = "idle";
let activeButton = null;

function $(id) {
  return document.getElementById(id);
}

function setState(next) {
  currentState = next;
  const busy = ["uploading", "resolving", "refreshing", "generating"].includes(next);
  const hasFp = Boolean(currentFingerprint);

  const badge = $("stateBadge");
  if (badge) {
    badge.textContent = STATE_LABELS[next] || next;
    badge.className = "badge " + (busy ? "badge--busy" : hasFp ? "badge--ok" : "badge--idle");
  }

  $("btnUpload").disabled = busy;
  $("btnResolve").disabled = busy || !hasFp;
  $("btnRefresh").disabled = busy || !hasFp;
  if (window.updatePackageUiState) window.updatePackageUiState(hasFp, busy);
  $("btnSelectAllSources").disabled = busy || !hasFp;
  $("btnClearSourceSelection").disabled = busy || !hasFp;

  $("cardSession").classList.toggle("is-disabled", !hasFp);
  $("cardGenerate").classList.toggle("is-disabled", !hasFp);

  updateStepPills(hasFp);
  setButtonLoading(activeButton, busy);
}

function updateStepPills(hasFp) {
  const p1 = $("stepPill1");
  const p2 = $("stepPill2");
  const p3 = $("stepPill3");
  if (!p1 || !p2 || !p3) return;

  [p1, p2, p3].forEach((el) => el.classList.remove("is-active", "is-done"));

  if (hasFp) {
    p1.classList.add("is-done");
    p2.classList.add("is-active");
  } else {
    p1.classList.add("is-active");
  }
}

function setButtonLoading(btn, loading) {
  document.querySelectorAll(".btn.is-loading").forEach((b) => b.classList.remove("is-loading"));
  if (loading && btn) btn.classList.add("is-loading");
}

function hasSelectedTheme() {
  const sel = $("themeSelect");
  return Boolean(sel && sel.value);
}

function headersJson() {
  return { "Content-Type": "application/json" };
}

function headersEmpty() {
  return {};
}

function apiBase() {
  return API_BASE_URL;
}
window.apiBase = apiBase;
window.headersJson = headersJson;
window.parseJsonOrThrow = parseJsonOrThrow;
window.log = log;
window.setState = setState;
window.hasSelectedTheme = hasSelectedTheme;
window.setActiveButton = (btn) => {
  activeButton = btn;
};
Object.defineProperty(window, "currentFingerprint", {
  get() {
    return currentFingerprint;
  },
});

function log(obj) {
  const panel = document.querySelector(".log-panel");
  if (panel && !panel.open) panel.open = true;
  $("log").textContent = typeof obj === "string" ? obj : JSON.stringify(obj, null, 2);
}

function saveUiState() {
  if (currentFingerprint) {
    localStorage.setItem(storage.fingerprint, currentFingerprint);
  }
}

function restoreUiState() {
  const fp = localStorage.getItem(storage.fingerprint);
  if (fp) {
    currentFingerprint = fp;
    $("rpdId").textContent = fp;
  }
}

function setFingerprint(fp) {
  currentFingerprint = fp || null;
  $("rpdId").textContent = currentFingerprint || "—";
  if (currentFingerprint) localStorage.setItem(storage.fingerprint, currentFingerprint);
}

function renderCountsFromPayload(payload) {
  const status = payload.counts_by_status || {};
  const kinds = payload.counts_by_kind || {};
  const parts = [];
  if (Object.keys(status).length) {
    parts.push(
      Object.entries(status)
        .map(([k, v]) => `${k}: ${v}`)
        .join(" · ")
    );
  }
  if (Object.keys(kinds).length) {
    parts.push(
      Object.entries(kinds)
        .map(([k, v]) => `${k}: ${v}`)
        .join(" · ")
    );
  }
  $("sourceCounts").textContent = parts.length
    ? "Источники: " + parts.join(" | ")
    : "Источники: —";
}

function renderSession(data) {
  currentSession = data || null;
  const rd = data.request_data || {};
  setFingerprint(data.fingerprint || currentFingerprint);
  renderCountsFromPayload(data);

  const themes = rd.lecture_themes || [];
  const sel = $("themeSelect");
  const prev = sel.value;
  sel.innerHTML = "";
  const empty = document.createElement("option");
  empty.value = "";
  empty.textContent = themes.length ? "— выберите тему —" : "Темы не найдены";
  sel.appendChild(empty);
  themes.forEach((t) => {
    const opt = document.createElement("option");
    opt.value = t.title || "";
    opt.textContent = (t.order != null ? `${t.order}. ` : "") + (t.title || "");
    sel.appendChild(opt);
  });
  sel.value = prev && Array.from(sel.options).some((x) => x.value === prev) ? prev : "";

  const src = (rd.discovered_sources || []).filter((s) => s.kind === "direct_pdf");
  const validIds = new Set(src.map((s) => s.id));
  selectedSourceIds.forEach((id) => {
    if (!validIds.has(id)) selectedSourceIds.delete(id);
  });
  renderSourcesList(src);
  if (window.loadUserSources) window.loadUserSources();
  setState(currentState);
}

function statusTagClass(status) {
  const s = (status || "pending").toLowerCase();
  if (s === "ok" || s === "duplicate_ok") return "tag--status-ok";
  if (s === "failed") return "tag--status-failed";
  return "tag--status-skipped";
}

function renderSourcesList(src) {
  const wrap = $("sourcesWrap");
  const pdfSrc = src.filter((s) => s.kind === "direct_pdf");
  if (!pdfSrc.length) {
    wrap.innerHTML =
      '<p class="empty-state">В РПД не найдено прямых ссылок на PDF. Добавьте .pdf в список литературы.</p>';
    return;
  }
  src = pdfSrc;

  const list = document.createElement("div");
  list.className = "source-list";

  src.forEach((s) => {
    const item = document.createElement("label");
    item.className = "source-item";
    const url = s.normalized_url || s.url || "";
    const label = s.title_hint ? escapeHtml(s.title_hint) : escapeHtml(shortUrl(url));
    const checked = selectedSourceIds.has(s.id);

    item.innerHTML =
      `<input type="checkbox" data-source-id="${escapeHtml(s.id)}" ${checked ? "checked" : ""}>` +
      `<div class="source-item__body">` +
      `<p class="source-item__url">${label}</p>` +
      `<p class="source-item__link muted">${escapeHtml(shortUrl(url))}</p>` +
      `<div class="source-item__meta">` +
      `<span class="tag tag--kind">PDF</span>` +
      `<span class="tag ${statusTagClass(s.status)}">${escapeHtml(s.status || "pending")}</span>` +
      (s.book_id ? `<span class="tag tag--status-ok">${escapeHtml(s.book_id)}</span>` : "") +
      `</div>` +
      (s.error ? `<p class="source-item__error">${escapeHtml(s.error)}</p>` : "") +
      `</div>`;

    list.appendChild(item);
  });

  wrap.innerHTML = "";
  wrap.appendChild(list);

  wrap.querySelectorAll("input[type=checkbox][data-source-id]").forEach((cb) => {
    cb.addEventListener("change", (ev) => {
      const id = ev.target.getAttribute("data-source-id");
      if (!id) return;
      if (ev.target.checked) selectedSourceIds.add(id);
      else selectedSourceIds.delete(id);
      if (window.updatePackageUiState) {
        window.updatePackageUiState(Boolean(currentFingerprint), false);
      }
    });
  });
}

function shortUrl(url) {
  if (!url) return "—";
  try {
    const u = new URL(url);
    const path = u.pathname.length > 40 ? "…" + u.pathname.slice(-38) : u.pathname;
    return u.hostname + path;
  } catch {
    return url.length > 56 ? url.slice(0, 53) + "…" : url;
  }
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

async function parseJsonOrThrow(response) {
  const data = await response.json();
  if (!response.ok || data.success === false) {
    const detail = data.detail || data.message || data.error || JSON.stringify(data);
    throw new Error(`HTTP ${response.status}: ${detail}`);
  }
  return data;
}

function bindFileUploadUi() {
  const input = $("rpdFile");
  const zone = $("uploadZone");
  const nameEl = $("fileName");

  input.addEventListener("change", () => {
    const f = input.files[0];
    nameEl.textContent = f ? f.name : "";
  });

  ["dragenter", "dragover"].forEach((ev) => {
    zone.addEventListener(ev, (e) => {
      e.preventDefault();
      zone.classList.add("is-dragover");
    });
  });
  ["dragleave", "drop"].forEach((ev) => {
    zone.addEventListener(ev, (e) => {
      e.preventDefault();
      zone.classList.remove("is-dragover");
    });
  });
  zone.addEventListener("drop", (e) => {
    const file = e.dataTransfer.files[0];
    if (file) {
      input.files = e.dataTransfer.files;
      nameEl.textContent = file.name;
    }
  });
}

$("themeSelect").addEventListener("change", () => setState(currentState));

$("btnUpload").onclick = async () => {
  const f = $("rpdFile").files[0];
  if (!f) {
    alert("Выберите файл РПД");
    return;
  }
  activeButton = $("btnUpload");
  setState("uploading");
  const fd = new FormData();
  fd.append("file", f);
  try {
    const r = await fetch(`${apiBase()}/rpd/upload`, {
      method: "POST",
      headers: headersEmpty(),
      body: fd,
    });
    const j = await parseJsonOrThrow(r);
    log(j);
    selectedSourceIds = new Set();
    setFingerprint(j.rpd_id);
    saveUiState();
    if (j.extracted_data) {
      renderSession({
        success: true,
        fingerprint: j.rpd_id,
        request_data: j.extracted_data,
      });
    }
  } catch (e) {
    log(String(e));
  } finally {
    activeButton = null;
    setState("idle");
  }
};

$("btnResolve").onclick = async () => {
  if (!currentFingerprint) return;
  activeButton = $("btnResolve");
  setState("resolving");
  try {
    const body = { fingerprint: currentFingerprint };
    if (selectedSourceIds.size > 0) {
      body.source_ids = Array.from(selectedSourceIds);
    }
    const r = await fetch(`${apiBase()}/rpd/resolve-sources`, {
      method: "POST",
      headers: headersJson(),
      body: JSON.stringify(body),
    });
    const j = await parseJsonOrThrow(r);
    log(j);
    await refreshSession(false);
  } catch (e) {
    log(String(e));
  } finally {
    activeButton = null;
    setState("idle");
  }
};

$("btnSelectAllSources").onclick = () => {
  const src =
    (currentSession && currentSession.request_data && currentSession.request_data.discovered_sources) ||
    [];
  src.filter((s) => s.kind === "direct_pdf").forEach((s) => selectedSourceIds.add(s.id));
  renderSourcesList(src);
};

$("btnClearSourceSelection").onclick = () => {
  selectedSourceIds = new Set();
  const src =
    (currentSession && currentSession.request_data && currentSession.request_data.discovered_sources) ||
    [];
  renderSourcesList(src);
};

async function refreshSession(withState = true) {
  if (!currentFingerprint) return;
  if (withState) {
    activeButton = $("btnRefresh");
    setState("refreshing");
  }
  try {
    const r = await fetch(`${apiBase()}/rpd/session/${encodeURIComponent(currentFingerprint)}`, {
      headers: headersEmpty(),
    });
    const j = await parseJsonOrThrow(r);
    log(j);
    renderSession(j);
  } catch (e) {
    log(String(e));
  } finally {
    if (withState) {
      activeButton = null;
      setState("idle");
    }
  }
}

$("btnRefresh").onclick = () => refreshSession(true);

bindFileUploadUi();
restoreUiState();
setState("idle");
if (currentFingerprint) {
  refreshSession(true);
}
