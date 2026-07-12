const state = {
  screen: 1,
  currentDoc: 'title',
  navigation: null,
  references: new Map(),
  documents: new Map(),
  scrollPositions: new Map(),
  activeSections: [],
};

const el = {};

async function init() {
  Object.assign(el, {
    track: document.getElementById('screenTrack'),
    viewport: document.getElementById('viewport'),
    readerScroll: document.getElementById('readerScroll'),
    readerContent: document.getElementById('readerContent'),
    bibliographyScroll: document.getElementById('bibliographyScroll'),
    bibliographyContent: document.getElementById('bibliographyContent'),
    tocNav: document.getElementById('tocNav'),
    footer: document.getElementById('readerFooter'),
    footerChapter: document.getElementById('footerChapter'),
    footerSection: document.getElementById('footerSection'),
    leftArrow: document.getElementById('leftArrow'),
    rightArrow: document.getElementById('rightArrow'),
    homeTitle: document.getElementById('homeTitle'),
    popup: document.getElementById('citationPopup'),
    progressControl: document.getElementById('progressControl'),
    progressRail: document.getElementById('progressRail'),
    progressDot: document.getElementById('progressDot'),
    figureDialog: document.getElementById('figureDialog'),
    figureImage: document.getElementById('figureDialogImage'),
    figureCaption: document.getElementById('figureDialogCaption'),
    closeFigure: document.getElementById('closeFigure'),
  });

  const [navData, refs, bibHtml] = await Promise.all([
    fetch('data/navigation.json').then(r => r.json()),
    fetch('data/references.json').then(r => r.json()),
    fetch('content/html/bibliography.html').then(r => r.text()),
  ]);
  state.navigation = navData;
  navData.documents.forEach(d => state.documents.set(d.slug, d));
  refs.forEach(r => state.references.set(r.id, r));
  el.bibliographyContent.innerHTML = bibHtml;
  buildToc(navData.toc);
  bindEvents();

  const hash = location.hash.replace(/^#/, '');
  const initial = state.documents.has(hash) ? hash : 'title';
  await loadDocument(initial, false);
  setScreen(1, false);
}

function buildToc(groups) {
  el.tocNav.innerHTML = '';
  groups.forEach(group => {
    const section = document.createElement('section');
    section.className = 'toc-group';
    const part = document.createElement('div');
    part.className = 'toc-part';
    part.textContent = group.part;
    section.append(part);
    group.items.forEach(item => {
      const button = document.createElement('button');
      button.className = 'toc-item';
      button.dataset.doc = item.slug;
      button.textContent = item.label;
      section.append(button);
    });
    el.tocNav.append(section);
  });
}

async function loadDocument(slug, pushHistory = true) {
  if (!state.documents.has(slug)) return;
  if (state.currentDoc) state.scrollPositions.set(state.currentDoc, el.readerScroll.scrollTop);
  closeCitationPopup();
  const html = await fetch(`content/html/${slug}.html`).then(r => r.text());
  state.currentDoc = slug;
  el.readerContent.innerHTML = html;
  const doc = state.documents.get(slug);
  el.footerChapter.textContent = doc.title;
  state.activeSections = [...el.readerContent.querySelectorAll('h2, h3')];
  updateFooterSection();
  updateTocActive();
  bindDynamicContent();
  const saved = state.scrollPositions.get(slug) || 0;
  requestAnimationFrame(() => {
    el.readerScroll.scrollTop = saved;
    updateProgress();
    updateFooterVisibility();
  });
  if (pushHistory) history.pushState({doc: slug}, '', `#${slug}`);
}

function bindDynamicContent() {
  el.readerContent.querySelectorAll('[data-doc]').forEach(button => {
    button.addEventListener('click', async () => {
      await loadDocument(button.dataset.doc);
      setScreen(1);
    });
  });
  el.readerContent.querySelectorAll('.citation-callout').forEach(c => {
    c.addEventListener('click', e => { e.stopPropagation(); openCitationPopup(c); });
    c.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openCitationPopup(c); } });
  });
  el.readerContent.querySelectorAll('.figure-link').forEach(link => {
    link.addEventListener('click', e => {
      e.preventDefault();
      el.figureImage.src = link.dataset.figureSrc;
      el.figureImage.alt = link.dataset.figureCaption || '';
      el.figureCaption.textContent = `${link.dataset.figureNumber} ${link.dataset.figureCaption}`;
      el.figureDialog.showModal();
    });
  });
}

function openCitationPopup(target) {
  const ids = (target.dataset.refIds || '').split(',').filter(Boolean);
  el.popup.innerHTML = '';
  ids.forEach(id => {
    const ref = state.references.get(id);
    if (!ref) return;
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = ref.display;
    button.addEventListener('click', () => openReference(id));
    el.popup.append(button);
  });
  if (!el.popup.children.length) return;
  el.popup.classList.add('visible');
  const rect = target.getBoundingClientRect();
  const popRect = el.popup.getBoundingClientRect();
  let left = rect.left;
  let top = rect.bottom + 8;
  if (left + popRect.width > innerWidth - 12) left = innerWidth - popRect.width - 12;
  if (left < 12) left = 12;
  if (top + popRect.height > innerHeight - 12) top = rect.top - popRect.height - 8;
  el.popup.style.left = `${left}px`;
  el.popup.style.top = `${Math.max(12, top)}px`;
}

function closeCitationPopup() { el.popup.classList.remove('visible'); }

function openReference(id) {
  closeCitationPopup();
  setScreen(2);
  requestAnimationFrame(() => {
    const entry = document.getElementById(`entry-${id}`);
    if (!entry) return;
    document.querySelectorAll('.bibliography-entry.highlighted').forEach(x => x.classList.remove('highlighted'));
    entry.classList.add('highlighted');
    const containerRect = el.bibliographyScroll.getBoundingClientRect();
    const entryRect = entry.getBoundingClientRect();
    const targetTop = Math.max(0, el.bibliographyScroll.scrollTop + entryRect.top - containerRect.top - (el.bibliographyScroll.clientHeight - entryRect.height) / 2);
    el.bibliographyScroll.scrollTop = targetTop;
    setTimeout(() => entry.classList.remove('highlighted'), 3200);
  });
}

function setScreen(index, animate = true) {
  state.screen = Math.max(0, Math.min(2, index));
  if (!animate) el.track.style.transition = 'none';
  el.track.style.transform = `translate3d(${-state.screen * 33.333333}%,0,0)`;
  if (!animate) requestAnimationFrame(() => el.track.style.transition = '');
  updateArrows();
  updateFooterVisibility();
  closeCitationPopup();
}

function updateArrows() {
  el.leftArrow.classList.toggle('hidden', state.screen === 0);
  el.rightArrow.classList.toggle('hidden', state.screen === 2);
  el.leftArrow.setAttribute('aria-label', state.screen === 2 ? 'Return to reading' : 'Open table of contents');
  el.rightArrow.setAttribute('aria-label', state.screen === 0 ? 'Return to reading' : 'Open bibliography');
}

function updateFooterVisibility() {
  const hidden = state.screen !== 1 || state.currentDoc === 'title';
  el.footer.classList.toggle('hidden', hidden);
  el.progressControl.classList.toggle('hidden', hidden);
}

function updateTocActive() {
  document.querySelectorAll('.toc-item').forEach(x => x.classList.toggle('active', x.dataset.doc === state.currentDoc));
}

function updateFooterSection() {
  const headings = state.activeSections;
  if (!headings.length) { el.footerSection.textContent = ''; return; }
  const y = el.readerScroll.scrollTop + 140;
  let idx = 0;
  headings.forEach((h, i) => { if (h.offsetTop <= y) idx = i; });
  el.footerSection.textContent = `Section ${idx + 1} / ${headings.length}`;
}

function updateProgress() {
  const max = el.readerScroll.scrollHeight - el.readerScroll.clientHeight;
  const ratio = max > 0 ? el.readerScroll.scrollTop / max : 0;
  el.progressDot.style.top = `${ratio * 100}%`;
  updateFooterSection();
}

function bindProgressDrag() {
  let dragging = false;
  const setFromClientY = y => {
    const r = el.progressRail.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (y - r.top) / r.height));
    const max = el.readerScroll.scrollHeight - el.readerScroll.clientHeight;
    el.readerScroll.scrollTop = ratio * Math.max(0, max);
  };
  el.progressRail.addEventListener('pointerdown', e => { dragging = true; el.progressRail.setPointerCapture(e.pointerId); setFromClientY(e.clientY); });
  el.progressRail.addEventListener('pointermove', e => { if (dragging) setFromClientY(e.clientY); });
  el.progressRail.addEventListener('pointerup', () => dragging = false);
  el.progressRail.addEventListener('pointercancel', () => dragging = false);
}

function bindSwipe() {
  let startX = 0, startY = 0, active = false;
  el.viewport.addEventListener('pointerdown', e => {
    if (e.target.closest('button, a, .citation-callout, input, dialog')) return;
    startX = e.clientX; startY = e.clientY; active = true;
  });
  el.viewport.addEventListener('pointerup', e => {
    if (!active) return;
    active = false;
    const dx = e.clientX - startX, dy = e.clientY - startY;
    if (Math.abs(dx) > 70 && Math.abs(dx) > Math.abs(dy) * 1.25) setScreen(state.screen + (dx < 0 ? 1 : -1));
  });
  el.viewport.addEventListener('wheel', e => {
    if (Math.abs(e.deltaX) > 50 && Math.abs(e.deltaX) > Math.abs(e.deltaY) * 1.4) {
      e.preventDefault();
      setScreen(state.screen + (e.deltaX > 0 ? 1 : -1));
    }
  }, {passive: false});
}

function bindEvents() {
  el.homeTitle.addEventListener('click', async () => { await loadDocument('title'); setScreen(1); });
  el.leftArrow.addEventListener('click', () => setScreen(state.screen === 2 ? 1 : 0));
  el.rightArrow.addEventListener('click', () => setScreen(state.screen === 0 ? 1 : 2));
  el.tocNav.addEventListener('click', async e => {
    const button = e.target.closest('[data-doc]');
    if (!button) return;
    await loadDocument(button.dataset.doc);
    setScreen(1);
  });
  el.readerScroll.addEventListener('scroll', updateProgress, {passive: true});
  document.addEventListener('click', e => { if (!e.target.closest('.citation-popup, .citation-callout')) closeCitationPopup(); });
  el.closeFigure.addEventListener('click', () => el.figureDialog.close());
  el.figureDialog.addEventListener('click', e => { if (e.target === el.figureDialog) el.figureDialog.close(); });
  addEventListener('keydown', e => { if (e.key === 'Escape') closeCitationPopup(); });
  addEventListener('popstate', async () => { const slug = location.hash.replace(/^#/, '') || 'title'; if (state.documents.has(slug)) { await loadDocument(slug, false); setScreen(1); } });
  bindProgressDrag();
  bindSwipe();
}

init().catch(err => {
  console.error(err);
  document.body.innerHTML = `<pre style="padding:2rem">The dissertation site could not load. ${String(err)}</pre>`;
});
