/**
 * Package generation, expert editor, slides preview, draft save, export.
 */
(function () {
  const packageDraft = {
    theme: "",
    lecture: "",
    lectureProvenance: "",
    lectureStudent: "",
    lab: "",
    selfcheck: "",
    moodleXml: "",
    pptxBase64: "",
    slidesJson: "",
    presentationPreview: null,
    slides: [],
    approved: false,
  };

  const slideImageCache = new Map();
  let editorTab = "lecture";
  let saveDraftTimer = null;
  let showProvenance = true;

  function $p(id) {
    return document.getElementById(id);
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function getGenOptions() {
    return {
      generate_presentation: Boolean($p("optPresentation")?.checked),
      generate_lab: Boolean($p("optLab")?.checked),
      generate_selfcheck: Boolean($p("optSelfcheck")?.checked),
      pipeline_mode: "facet_rag",
    };
  }

  function lectureForEditor() {
    if (showProvenance && packageDraft.lectureProvenance) {
      return packageDraft.lectureProvenance;
    }
    return packageDraft.lectureStudent || packageDraft.lecture;
  }

  function tabContent(tab) {
    if (tab === "lab") return packageDraft.lab;
    if (tab === "selfcheck") return packageDraft.selfcheck;
    return lectureForEditor();
  }

  function setTabContent(tab, text) {
    if (tab === "lab") packageDraft.lab = text;
    else if (tab === "selfcheck") packageDraft.selfcheck = text;
    else if (showProvenance) packageDraft.lectureProvenance = text;
    else packageDraft.lecture = text;
    packageDraft.approved = false;
    updateReviewBadge();
    updateExportButtons();
    scheduleSaveDraft();
  }

  function renderEditorPreview() {
    const src = tabContent(editorTab);
    const prev = $p("editorPreview");
    if (!prev) return;
    if (window.marked && src) {
      prev.innerHTML = marked.parse(src, { breaks: true });
    } else {
      prev.textContent = src || "—";
    }
  }

  function previewSlidesList() {
    const prev = packageDraft.presentationPreview;
    if (prev && Array.isArray(prev.slides) && prev.slides.length) {
      return prev.slides;
    }
    try {
      const data = JSON.parse(packageDraft.slidesJson || "{}");
      const slides = data.slides || data;
      return Array.isArray(slides) ? slides : [];
    } catch {
      return [];
    }
  }

  function slideImageUrl(slide) {
    if (!slide.image_url) return "";
    const rel = String(slide.image_url);
    if (rel.startsWith("http")) return rel;
    return `${window.apiBase()}${rel.startsWith("/") ? rel : "/" + rel}`;
  }

  async function resolveSlideImage(slide) {
    const url = slideImageUrl(slide);
    if (!url) return "";
    const cacheKey = `${url}::${slide.image_caption || ""}`;
    if (slideImageCache.has(cacheKey)) return slideImageCache.get(cacheKey);
    try {
      const r = await fetch(url, { headers: window.headersEmpty() });
      if (!r.ok) return "";
      const blob = await r.blob();
      const obj = URL.createObjectURL(blob);
      slideImageCache.set(cacheKey, obj);
      return obj;
    } catch {
      return "";
    }
  }

  function invalidateSlideImageCache() {
    slideImageCache.forEach((u) => {
      if (String(u).startsWith("blob:")) URL.revokeObjectURL(u);
    });
    slideImageCache.clear();
  }

  async function uploadSlideImage(slideIndex, file) {
    if (!window.currentFingerprint || !packageDraft.theme) {
      alert("Сначала загрузите РПД и выберите тему");
      return null;
    }
    const q = new URLSearchParams({
      fingerprint: window.currentFingerprint,
      theme_title: packageDraft.theme,
      slide_index: String(slideIndex),
    });
    const fd = new FormData();
    fd.append("file", file);
    const r = await fetch(`${window.apiBase()}/rpd/presentation-preview/slide-image?${q}`, {
      method: "POST",
      headers: window.headersEmpty(),
      body: fd,
    });
    const j = await window.parseJsonOrThrow(r);
    invalidateSlideImageCache();
    return j;
  }

  async function clearSlideImage(slideIndex) {
    if (!window.currentFingerprint || !packageDraft.theme) return;
    const q = new URLSearchParams({
      fingerprint: window.currentFingerprint,
      theme_title: packageDraft.theme,
      slide_index: String(slideIndex),
    });
    await fetch(`${window.apiBase()}/rpd/presentation-preview/slide-image?${q}`, {
      method: "DELETE",
      headers: window.headersEmpty(),
    });
    invalidateSlideImageCache();
  }


  function syncSlidesJson() {
    packageDraft.slidesJson = JSON.stringify({ slides: packageDraft.slides }, null, 2);
    packageDraft.approved = false;
    updateReviewBadge();
    updateExportButtons();
    scheduleSaveDraft();
  }

  function openSlidesCarousel() {
    const list = previewSlidesList();
    if (!list.length) {
      const stage = $p("slideCarouselStage");
      if (stage) {
        stage.innerHTML =
          '<p class="empty-state">Нет слайдов — включите «Презентация» при генерации</p>';
      }
      return;
    }
    if (!packageDraft.slides.length) {
      packageDraft.slides = list.map((s) => ({
        layout: s.layout || "content",
        title: s.title || "",
        subtitle: s.subtitle || "",
        bullets: Array.isArray(s.bullets) ? [...s.bullets] : [],
        image_url: s.image_url || null,
        image_kind: s.image_kind || null,
        image_caption: s.image_caption || "",
        figure_number: s.figure_number != null ? s.figure_number : null,
      }));
    }
    if (!window.SlidesCarousel) return;
    window.SlidesCarousel.configure({
      clearCache: false,
      resolveImage: resolveSlideImage,
      onChange(slides) {
        packageDraft.slides = slides;
        syncSlidesJson();
      },
      onImageUpload: uploadSlideImage,
      onImageClear: clearSlideImage,
    });
    window.SlidesCarousel.setSlides(packageDraft.slides, 0);
  }

  function showEditorPane(tab) {
    const isSlides = tab === "slides";
    $p("slidesPreviewPane")?.classList.toggle("hidden", !isSlides);
    $p("editorSplit")?.classList.toggle("hidden", isSlides);
    $p("optShowProvenance")?.closest("label")?.classList.toggle("hidden", isSlides);
    document.querySelector(".app")?.classList.toggle("app--wide", isSlides);
  }

  function loadEditorTab(tab) {
    editorTab = tab;
    document.querySelectorAll(".editor-tab").forEach((btn) => {
      btn.classList.toggle("is-active", btn.getAttribute("data-tab") === tab);
    });
    showEditorPane(tab);
    if (tab === "slides") {
      openSlidesCarousel();
      return;
    }
    const ta = $p("editorSource");
    if (ta) ta.value = tabContent(tab);
    renderEditorPreview();
  }

  function draftPayload() {
    return {
      fingerprint: window.currentFingerprint,
      theme_title: packageDraft.theme,
      lecture_md: lectureForEditor() || packageDraft.lecture,
      lab_md: packageDraft.lab,
      selfcheck_md: packageDraft.selfcheck,
      moodle_questions_xml: packageDraft.moodleXml,
      presentation_pptx_base64: packageDraft.pptxBase64,
      presentation_slides_json:
        packageDraft.slides.length > 0
          ? JSON.stringify({ slides: packageDraft.slides })
          : packageDraft.slidesJson,
      approved: packageDraft.approved,
    };
  }

  async function saveDraftToServer() {
    if (!window.currentFingerprint || !packageDraft.lecture) return;
    const hint = $p("draftHint");
    try {
      const r = await fetch(`${window.apiBase()}/rpd/package-draft`, {
        method: "PUT",
        headers: window.headersJson(),
        body: JSON.stringify(draftPayload()),
      });
      const j = await window.parseJsonOrThrow(r);
      if (hint) hint.textContent = "Черновик сохранён: " + (j.updated_at || "сейчас");
    } catch (e) {
      if (hint) hint.textContent = "Ошибка сохранения: " + e.message;
    }
  }

  function scheduleSaveDraft() {
    clearTimeout(saveDraftTimer);
    saveDraftTimer = setTimeout(saveDraftToServer, 1500);
  }

  async function loadDraftFromServer() {
    if (!window.currentFingerprint) return;
    const theme = $p("themeSelect")?.value;
    if (!theme) return;
    try {
      const q = new URLSearchParams({
        fingerprint: window.currentFingerprint,
        theme_title: theme,
      });
      const r = await fetch(`${window.apiBase()}/rpd/package-draft?${q}`, {
        headers: window.headersEmpty(),
      });
      const j = await r.json();
      if (!j.success) return;
      packageDraft.theme = j.theme_title || theme;
      packageDraft.lecture = j.lecture_md || "";
      packageDraft.lab = j.lab_md || "";
      packageDraft.selfcheck = j.selfcheck_md || "";
      packageDraft.moodleXml = j.moodle_questions_xml || "";
      packageDraft.pptxBase64 = j.presentation_pptx_base64 || "";
      packageDraft.slidesJson = j.presentation_slides_json || "";
      packageDraft.slides = [];
      try {
        const parsed = JSON.parse(packageDraft.slidesJson || "{}");
        if (Array.isArray(parsed.slides)) packageDraft.slides = parsed.slides;
      } catch {
        /* ignore */
      }
      packageDraft.approved = Boolean(j.approved);
      $p("cardEditor")?.classList.remove("is-disabled");
      loadEditorTab(editorTab === "slides" ? "slides" : "lecture");
      updateReviewBadge();
      updateExportButtons();
      const hint = $p("draftHint");
      if (hint) hint.textContent = "Загружен черновик: " + (j.updated_at || "");
      window.updateStepPillsExtended?.(
        true,
        true,
        packageDraft.approved
      );
    } catch {
      /* no draft */
    }
  }

  function applyPackageToEditor(data) {
    packageDraft.theme = data.theme_title || "";
    packageDraft.lecture = data.lecture_content || "";
    packageDraft.lectureProvenance =
      data.lecture_content_provenance || data.lecture_content || "";
    packageDraft.lectureStudent = data.lecture_content || "";
    packageDraft.lab = data.lab_content || "";
    packageDraft.selfcheck = data.selfcheck_content || "";
    packageDraft.moodleXml = data.moodle_questions_xml || "";
    packageDraft.pptxBase64 = data.presentation_pptx_base64 || "";
    packageDraft.slidesJson = data.presentation_slides_json || "";
    packageDraft.presentationPreview = data.presentation_preview || null;
    packageDraft.slides = [];
    packageDraft.approved = false;
    slideImageCache.forEach((url) => URL.revokeObjectURL(url));
    slideImageCache.clear();
    window.SlidesCarousel?.configure?.({ clearCache: true });

    $p("cardEditor")?.classList.remove("is-disabled");
    $p("btnSaveDraft")?.removeAttribute("disabled");
    loadEditorTab("lecture");
    updateReviewBadge();
    updateExportButtons();
    window.updateStepPillsExtended?.(Boolean(window.currentFingerprint), true);
    saveDraftToServer();
  }

  function updateReviewBadge() {
    const b = $p("reviewBadge");
    if (!b) return;
    if (packageDraft.approved) {
      b.textContent = "Утверждено экспертом";
      b.className = "badge badge--ok";
    } else if (packageDraft.lecture) {
      b.textContent = "Требуется проверка";
      b.className = "badge badge--busy";
    } else {
      b.textContent = "Не проверено";
      b.className = "badge badge--idle";
    }
    $p("btnApprove")?.toggleAttribute("disabled", !packageDraft.lecture);
  }

  function updateExportButtons() {
    const ok = packageDraft.approved;
    ["btnExportScorm", "btnExportPdfAll", "btnExportPptx", "btnExportPresPdf"].forEach((id) => {
      const el = $p(id);
      if (el) el.disabled = !ok;
    });
    if ($p("btnExportPptx") && !packageDraft.pptxBase64 && !packageDraft.slides.length && !packageDraft.slidesJson) {
      $p("btnExportPptx").disabled = true;
    }
    if ($p("btnExportPresPdf") && !packageDraft.slidesJson) {
      $p("btnExportPresPdf").disabled = true;
    }
    $p("cardExport")?.classList.toggle("is-disabled", !packageDraft.lecture);
  }

  async function postExport(format) {
    const body = {
      fingerprint: window.currentFingerprint || "",
      theme_title: packageDraft.theme || "Course",
      lecture_md: lectureForEditor() || packageDraft.lecture,
      lab_md: packageDraft.lab,
      selfcheck_md: packageDraft.selfcheck,
      moodle_questions_xml: packageDraft.moodleXml,
      presentation_pptx_base64: packageDraft.pptxBase64,
      presentation_slides_json:
        packageDraft.slides.length > 0
          ? JSON.stringify({ slides: packageDraft.slides })
          : packageDraft.slidesJson,
      export_format: format,
    };
    const r = await fetch(`${window.apiBase()}/rpd/export-package`, {
      method: "POST",
      headers: window.headersJson(),
      body: JSON.stringify(body),
    });
    if (!r.ok) {
      const err = await r.text();
      throw new Error(err || `HTTP ${r.status}`);
    }
    return r;
  }

  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function runGeneratePackage(lectureOnly) {
    if (!window.currentFingerprint) return;
    const theme = $p("themeSelect")?.value;
    if (!theme) {
      alert("Выберите тему");
      return;
    }
    const opts = getGenOptions();
    if (lectureOnly) {
      opts.generate_presentation = false;
      opts.generate_lab = false;
      opts.generate_selfcheck = false;
    }
    const btn = lectureOnly ? $p("btnGenerateLectureOnly") : $p("btnGeneratePackage");
    if (window.setActiveButton) window.setActiveButton(btn);
    window.setState("generating");
    window.ProgressUI?.reset();
    window.ProgressUI?.show();
    const body = {
      fingerprint: window.currentFingerprint,
      theme_title: theme,
      options: opts,
      user_sources: window.getUserSourcesPayload?.() || [],
    };
    try {
      let j;
      if (window.ProgressUI?.streamGeneratePackage) {
        j = await window.ProgressUI.streamGeneratePackage(
          `${window.apiBase()}/rpd/generate-package/stream`,
          body,
          window.headersJson()
        );
      } else {
        const r = await fetch(`${window.apiBase()}/rpd/generate-package`, {
          method: "POST",
          headers: window.headersJson(),
          body: JSON.stringify(body),
        });
        j = await window.parseJsonOrThrow(r);
      }
      window.log(j);
      if (j.success) applyPackageToEditor(j);
      else if (j.message) window.log(j.message);
    } catch (e) {
      window.log(String(e));
      window.ProgressUI?.applyEvent?.({
        step_id: "error",
        message: String(e),
        status: "error",
      });
    } finally {
      if (window.setActiveButton) window.setActiveButton(null);
      window.setState("idle");
    }
  }

  function bindEditor() {
    document.querySelectorAll(".editor-tab").forEach((btn) => {
      btn.addEventListener("click", () => loadEditorTab(btn.getAttribute("data-tab")));
    });
    $p("optShowProvenance")?.addEventListener("change", (ev) => {
      showProvenance = Boolean(ev.target.checked);
      if (editorTab === "lecture") {
        const ta = $p("editorSource");
        if (ta) ta.value = lectureForEditor();
        renderEditorPreview();
      }
    });
    $p("editorSource")?.addEventListener("input", (ev) => {
      setTabContent(editorTab, ev.target.value);
      renderEditorPreview();
    });
    $p("btnApprove")?.addEventListener("click", async () => {
      packageDraft.approved = true;
      updateReviewBadge();
      updateExportButtons();
      await saveDraftToServer();
      window.updateStepPillsExtended?.(Boolean(window.currentFingerprint), true, true);
    });
    $p("btnSaveDraft")?.addEventListener("click", () => saveDraftToServer());
    $p("themeSelect")?.addEventListener("change", () => loadDraftFromServer());
  }

  function bindExport() {
    $p("btnExportScorm")?.addEventListener("click", async () => {
      try {
        const r = await postExport("scorm");
        downloadBlob(await r.blob(), `${packageDraft.theme || "course"}_scorm.zip`);
      } catch (e) {
        window.log(String(e));
      }
    });
    $p("btnExportPdfAll")?.addEventListener("click", async () => {
      try {
        const r = await postExport("pdf_all");
        const native = r.headers.get("X-Pdf-Native") === "1";
        downloadBlob(await r.blob(), `${packageDraft.theme || "course"}_pdf.zip`);
        if (!native) {
          alert("Установите на сервере: pip install xhtml2pdf — тогда в ZIP будут настоящие .pdf");
        }
      } catch (e) {
        window.log(String(e));
      }
    });
    $p("btnExportPptx")?.addEventListener("click", async () => {
      try {
        const r = await postExport("pptx");
        downloadBlob(await r.blob(), `${packageDraft.theme || "presentation"}.pptx`);
      } catch (e) {
        window.log(String(e));
      }
    });
    $p("btnExportPresPdf")?.addEventListener("click", async () => {
      try {
        const r = await postExport("presentation_pdf");
        downloadBlob(await r.blob(), `${packageDraft.theme || "slides"}_presentation.pdf`);
      } catch (e) {
        window.log(String(e));
      }
    });
  }

  window.updatePackageUiState = function (hasFp, busy) {
    const hasPdf = Boolean(document.querySelector("#sourcesWrap .source-item input:checked"));
    const canGen =
      hasFp && window.hasSelectedTheme?.() && (window.hasUserSources?.() || hasPdf);
    $p("btnGeneratePackage")?.toggleAttribute("disabled", busy || !canGen);
    $p("btnGenerateLectureOnly")?.toggleAttribute("disabled", busy || !canGen);
    $p("btnAddUserSource")?.toggleAttribute("disabled", busy || !hasFp || !window.hasSelectedTheme?.());
  };

  window.updateStepPillsExtended = function (hasFp, hasPackage, approved) {
    const p4 = $p("stepPill4");
    if (!p4) return;
    p4.classList.remove("is-active", "is-done");
    if (approved) p4.classList.add("is-done");
    else if (hasPackage) p4.classList.add("is-active");
  };

  bindEditor();
  bindExport();
  $p("btnGeneratePackage")?.addEventListener("click", () => runGeneratePackage(false));
  $p("btnGenerateLectureOnly")?.addEventListener("click", () => runGeneratePackage(true));
  updateExportButtons();
})();
