/**
 * PowerPoint-style slide carousel: one slide, arrows, keyboard, inline edit.
 */
(function () {
  let slides = [];
  let index = 0;
  let imageCache = new Map();
  let onChange = null;
  let resolveImageFn = null;
  let onImageUpload = null;
  let onImageClear = null;
  let bound = false;

  function $(id) {
    return document.getElementById(id);
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function clampIndex(i) {
    if (!slides.length) return 0;
    return Math.max(0, Math.min(slides.length - 1, i));
  }

  function currentSlide() {
    return slides[index] || null;
  }

  function hasDisplayableImage(s) {
    if (!s) return false;
    const kind = String(s.image_kind || "").toLowerCase();
    if (kind === "none" || kind === "placeholder" || kind === "page_snapshot") return false;
    return Boolean(s.image_url);
  }

  function assignFigureNumbers(list) {
    let n = 0;
    for (const s of list) {
      if (String(s.layout || "").toLowerCase() === "title") {
        s.figure_number = null;
        continue;
      }
      if (hasDisplayableImage(s)) {
        n += 1;
        s.figure_number = n;
      } else {
        s.figure_number = null;
      }
    }
  }

  function formatFigureCaption(s) {
    const note = String(s.image_caption || "").trim();
    const num = s.figure_number;
    if (!num && !note) return "";
    if (!num) return note;
  if (!note) return `Рис. ${num}`;
  return `Рис. ${num} - ${note}`;
  }

  function syncEditForm() {
    const s = currentSlide();
    const titleEl = $("slideEditTitle");
    const subEl = $("slideEditSubtitle");
    const bulletsEl = $("slideEditBullets");
    const capEl = $("slideEditCaption");
    const subWrap = $("slideEditSubtitleWrap");
    const bulWrap = $("slideEditBulletsWrap");
    const imgBlock = $("slideEditImageBlock");
    const imgInput = $("slideEditImage");
    if (!s || !titleEl) return;

    const isTitle = String(s.layout || "").toLowerCase() === "title";
    titleEl.value = s.title || "";
    if (subEl) subEl.value = s.subtitle || "";
    if (bulletsEl) bulletsEl.value = (s.bullets || []).join("\n");
    if (capEl) capEl.value = s.image_caption || "";
    if (subWrap) subWrap.classList.toggle("hidden", !isTitle);
    if (bulWrap) bulWrap.classList.toggle("hidden", isTitle);
    if (imgBlock) imgBlock.classList.toggle("hidden", isTitle);
    if (imgInput) imgInput.value = "";
  }

  function applyEditForm() {
    const s = currentSlide();
    if (!s) return;
    const titleEl = $("slideEditTitle");
    const subEl = $("slideEditSubtitle");
    const bulletsEl = $("slideEditBullets");
    const capEl = $("slideEditCaption");
    if (titleEl) s.title = titleEl.value;
    if (subEl) s.subtitle = subEl.value;
    if (bulletsEl) {
      s.bullets = bulletsEl.value
        .split("\n")
        .map((l) => l.trim())
        .filter(Boolean);
    }
    if (capEl) s.image_caption = capEl.value.trim();
    assignFigureNumbers(slides);
    if (typeof onChange === "function") onChange(slides);
    renderThumbs();
    renderStage();
  }

  function updateCounter() {
    const el = $("slideCarouselCounter");
    if (el) el.textContent = slides.length ? `${index + 1} / ${slides.length}` : "—";
    const prev = $("slidePrev");
    const next = $("slideNext");
    if (prev) prev.disabled = index <= 0;
    if (next) next.disabled = index >= slides.length - 1;
  }

  async function imageForSlide(slide) {
    if (!resolveImageFn) return "";
    return (await resolveImageFn(slide)) || "";
  }

  function buildStageHtml(s, imgSrc) {
    const layout = String(s.layout || "content").toLowerCase();
    if (layout === "title") {
      return (
        `<div class="ppt-slide ppt-slide--title">` +
        `<div class="ppt-slide__inner">` +
        `<h2 class="ppt-slide__title">${escapeHtml(s.title || "")}</h2>` +
        (s.subtitle ? `<p class="ppt-slide__subtitle">${escapeHtml(s.subtitle)}</p>` : "") +
        `</div></div>`
      );
    }
    const bullets = (s.bullets || [])
      .filter((b) => String(b).trim())
      .map((b) => `<li>${escapeHtml(String(b))}</li>`)
      .join("");
    const cap = formatFigureCaption(s);
    let img = "";
    if (imgSrc) {
      img =
        `<div class="ppt-slide__media">` +
        `<img src="${imgSrc}" alt="" />` +
        (cap ? `<p class="ppt-slide__figcap">${escapeHtml(cap)}</p>` : "") +
        `</div>`;
    }
    return (
      `<div class="ppt-slide ppt-slide--content${imgSrc ? "" : " ppt-slide--text-only"}">` +
      `<div class="ppt-slide__body">` +
      `<div class="ppt-slide__text">` +
      `<h2 class="ppt-slide__heading">${escapeHtml(s.title || "")}</h2>` +
      (bullets ? `<ul class="ppt-slide__bullets">${bullets}</ul>` : "") +
      `</div>` +
      img +
      `</div></div>`
    );
  }

  async function renderStage() {
    const stage = $("slideCarouselStage");
    if (!stage) return;
    const s = currentSlide();
    if (!s) {
      stage.innerHTML = '<p class="empty-state">Нет слайдов</p>';
      updateCounter();
      return;
    }
    stage.innerHTML = '<p class="muted ppt-slide__loading">Загрузка…</p>';
    const imgSrc = hasDisplayableImage(s) ? await imageForSlide(s) : "";
    stage.innerHTML = buildStageHtml(s, imgSrc);
    updateCounter();
  }

  function renderThumbs() {
    const wrap = $("slideThumbs");
    if (!wrap) return;
    wrap.innerHTML = slides
      .map((s, i) => {
        const active = i === index ? " is-active" : "";
        const label = escapeHtml((s.title || `Слайд ${i + 1}`).slice(0, 42));
        return (
          `<button type="button" class="ppt-thumb${active}" data-idx="${i}" title="${label}">` +
          `<span class="ppt-thumb__num">${i + 1}</span>` +
          `<span class="ppt-thumb__label">${label}</span>` +
          `</button>`
        );
      })
      .join("");
    wrap.querySelectorAll(".ppt-thumb").forEach((btn) => {
      btn.addEventListener("click", () => {
        goTo(parseInt(btn.getAttribute("data-idx"), 10));
      });
    });
    const activeBtn = wrap.querySelector(".ppt-thumb.is-active");
    if (activeBtn) activeBtn.scrollIntoView({ block: "nearest", inline: "center", behavior: "smooth" });
  }

  function goTo(i) {
    index = clampIndex(i);
    syncEditForm();
    renderThumbs();
    renderStage();
    const root = $("slideCarousel");
    if (root) root.focus();
  }

  function goPrev() {
    goTo(index - 1);
  }

  function goNext() {
    goTo(index + 1);
  }

  async function handleImageFile(file) {
    if (!file || typeof onImageUpload !== "function") return;
    const result = await onImageUpload(index, file);
    const s = currentSlide();
    if (!s || !result) return;
    if (result.image_url) s.image_url = result.image_url;
    if (result.image_kind) s.image_kind = result.image_kind;
    if (result.figure_number != null) s.figure_number = result.figure_number;
    assignFigureNumbers(slides);
    if (typeof onChange === "function") onChange(slides);
    renderThumbs();
    renderStage();
    syncEditForm();
  }

  async function handleImageClear() {
    if (typeof onImageClear === "function") {
      await onImageClear(index);
    }
    const s = currentSlide();
    if (!s) return;
    s.image_url = null;
    s.image_kind = "none";
    s.figure_number = null;
    assignFigureNumbers(slides);
    if (typeof onChange === "function") onChange(slides);
    renderThumbs();
    renderStage();
    syncEditForm();
  }

  function bindOnce() {
    if (bound) return;
    bound = true;
    $("slidePrev")?.addEventListener("click", goPrev);
    $("slideNext")?.addEventListener("click", goNext);
    $("slideEditTitle")?.addEventListener("input", applyEditForm);
    $("slideEditSubtitle")?.addEventListener("input", applyEditForm);
    $("slideEditBullets")?.addEventListener("input", applyEditForm);
    $("slideEditCaption")?.addEventListener("input", applyEditForm);
    $("slideEditImage")?.addEventListener("change", (ev) => {
      const file = ev.target.files && ev.target.files[0];
      if (file) handleImageFile(file);
    });
    $("slideEditImageClear")?.addEventListener("click", () => handleImageClear());

    const root = $("slideCarousel");
    root?.addEventListener("keydown", (e) => {
      if (e.key === "ArrowRight" || e.key === "PageDown") {
        e.preventDefault();
        goNext();
      } else if (e.key === "ArrowLeft" || e.key === "PageUp") {
        e.preventDefault();
        goPrev();
      } else if (e.key === "Home") {
        e.preventDefault();
        goTo(0);
      } else if (e.key === "End") {
        e.preventDefault();
        goTo(slides.length - 1);
      }
    });
  }

  function normalizeSlide(s) {
    return {
      layout: s.layout || "content",
      title: s.title || "",
      subtitle: s.subtitle || "",
      bullets: Array.isArray(s.bullets) ? s.bullets.map(String) : [],
      image_url: s.image_url || null,
      image_kind: s.image_kind || null,
      image_caption: s.image_caption || "",
      figure_number: s.figure_number != null ? s.figure_number : null,
    };
  }

  window.SlidesCarousel = {
    setSlides(list, startIndex) {
      slides = (list || []).map(normalizeSlide);
      assignFigureNumbers(slides);
      index = clampIndex(startIndex || 0);
      bindOnce();
      syncEditForm();
      renderThumbs();
      renderStage();
      $("slideCarousel")?.focus();
    },

    getSlides() {
      return slides;
    },

    configure(opts) {
      onChange = opts.onChange || null;
      resolveImageFn = opts.resolveImage || null;
      onImageUpload = opts.onImageUpload || null;
      onImageClear = opts.onImageClear || null;
      if (opts.clearCache) {
        imageCache.forEach((u) => {
          if (String(u).startsWith("blob:")) URL.revokeObjectURL(u);
        });
        imageCache = new Map();
      }
    },

    refresh() {
      assignFigureNumbers(slides);
      renderThumbs();
      renderStage();
      syncEditForm();
    },

    goTo,
    goPrev,
    goNext,
  };
})();
