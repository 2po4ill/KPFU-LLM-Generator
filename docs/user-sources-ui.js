/**
 * User-attached priority sources (bypass TOC, boosted RAG).
 */
(function () {
  let userSources = [];

  function $u(id) {
    return document.getElementById(id);
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function hasUserSources() {
    return userSources.length > 0;
  }

  window.getUserSourcesPayload = function () {
    return userSources.map((s) => ({
      id: s.id,
      title: s.title,
      text: s.text,
    }));
  };

  window.hasUserSources = hasUserSources;

  function renderList() {
    const list = $u("userSourcesList");
    if (!list) return;
    if (!userSources.length) {
      list.innerHTML = '<li class="muted">Нет вложений — можно добавить конспект, статью или выдержки</li>';
      return;
    }
    list.innerHTML = userSources
      .map(
        (s) =>
          `<li class="user-source-item">` +
          `<div class="user-source-item__head">` +
          `<strong>${escapeHtml(s.title)}</strong>` +
          `<button type="button" class="btn btn--ghost btn--tiny" data-del="${escapeHtml(s.id)}">Удалить</button>` +
          `</div>` +
          `<p class="user-source-item__preview">${escapeHtml((s.text || "").slice(0, 180))}${(s.text || "").length > 180 ? "…" : ""}</p>` +
          `</li>`
      )
      .join("");
    list.querySelectorAll("[data-del]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = btn.getAttribute("data-del");
        userSources = userSources.filter((x) => x.id !== id);
        renderList();
        saveUserSources();
        window.updatePackageUiState?.(Boolean(window.currentFingerprint), false);
      });
    });
  }

  async function loadUserSources() {
    if (!window.currentFingerprint) return;
    const theme = $u("themeSelect")?.value;
    if (!theme) {
      userSources = [];
      renderList();
      return;
    }
    try {
      const q = new URLSearchParams({
        fingerprint: window.currentFingerprint,
        theme_title: theme,
      });
      const r = await fetch(`${window.apiBase()}/rpd/user-sources?${q}`, {
        headers: window.headersEmpty(),
      });
      const j = await r.json();
      userSources = j.success && Array.isArray(j.sources) ? j.sources : [];
    } catch {
      userSources = [];
    }
    renderList();
    window.updatePackageUiState?.(Boolean(window.currentFingerprint), false);
  }

  async function saveUserSources() {
    if (!window.currentFingerprint) return;
    const theme = $u("themeSelect")?.value;
    if (!theme) return;
    try {
      await fetch(`${window.apiBase()}/rpd/user-sources`, {
        method: "PUT",
        headers: window.headersJson(),
        body: JSON.stringify({
          fingerprint: window.currentFingerprint,
          theme_title: theme,
          sources: window.getUserSourcesPayload(),
        }),
      });
    } catch {
      /* ignore */
    }
  }

  function addUserSource() {
    const title = ($u("userSourceTitle")?.value || "").trim() || "Дополнительный источник";
    const text = ($u("userSourceText")?.value || "").trim();
    if (!text) {
      alert("Вставьте текст источника");
      return;
    }
    const id = "usr_" + Date.now().toString(36);
    userSources.push({ id, title, text });
    if ($u("userSourceText")) $u("userSourceText").value = "";
    if ($u("userSourceTitle")) $u("userSourceTitle").value = "";
    renderList();
    saveUserSources();
    window.updatePackageUiState?.(Boolean(window.currentFingerprint), false);
  }

  function bind() {
    $u("btnAddUserSource")?.addEventListener("click", addUserSource);
    $u("themeSelect")?.addEventListener("change", () => loadUserSources());
  }

  bind();
  window.loadUserSources = loadUserSources;
})();
