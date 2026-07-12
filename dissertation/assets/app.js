const state = {
  screen: 1,
  currentDoc: 'title',
  navigation: null,
  references: new Map(),
  documents: new Map(),
  scrollPositions: new Map(),
  activeSections: [],
  citationPopups: new Map(),
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
  bindBibliographyLinks();
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
    if (group.part) section.append(part);
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
  document.body.classList.toggle('title-page-active', slug === 'title');
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
  if (state.citationPopups.has(target)) return;
  const ids = (target.dataset.refIds || '').split(',').filter(Boolean);
  const popup = document.createElement('div');
  popup.className = 'citation-popup';
  popup.setAttribute('role', 'dialog');
  popup.setAttribute('aria-label', 'Citation details');
  target.classList.add('selected');
  state.citationPopups.set(target, popup);
  el.readerContent.append(popup);
  const connector = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  connector.classList.add('citation-connector');
  connector.setAttribute('aria-hidden', 'true');
  popup.append(connector);
  const buttons = [];
  ids.forEach(id => {
    const ref = state.references.get(id);
    if (!ref) return;
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = ref.display;
    button.addEventListener('click', () => openReference(id));
    popup.append(button);
    buttons.push(button);
  });
  if (!buttons.length) {
    target.classList.remove('selected');
    state.citationPopups.delete(target);
    popup.remove();
    return;
  }
  popup.classList.add('visible');
  const rect = target.getBoundingClientRect();
  const contentRect = el.readerContent.getBoundingClientRect();
  const anchor = {
    left: rect.left - contentRect.left,
    right: rect.right - contentRect.left,
    y: rect.top - contentRect.top + rect.height / 2,
  };
  const fragments = [...target.getClientRects()].map(fragment => ({
    left: fragment.left - contentRect.left,
    right: fragment.right - contentRect.left,
    top: fragment.top - contentRect.top,
    bottom: fragment.bottom - contentRect.top,
  }));
  const firstFragment = fragments[0] || { left: anchor.left, right: anchor.right, top: anchor.y, bottom: anchor.y };
  const lastFragment = fragments[fragments.length - 1] || firstFragment;
  const labelWidth = Math.min(320, innerWidth - 32);
  const minGap = innerWidth <= 899 ? 28 : 46;
  const rightFits = contentRect.left + anchor.right + minGap + labelWidth <= innerWidth - 16;
  const leftFits = contentRect.left + anchor.left - minGap - labelWidth >= 16;
  const referenceCenter = contentRect.left + (anchor.left + anchor.right) / 2;
  const preferRight = referenceCenter >= innerWidth / 2;
  const routes = [
    { side: 'right', corner: 'top', bend: -1 },
    { side: 'left', corner: 'bottom', bend: 1 },
    { side: 'right', corner: 'bottom', bend: 1 },
    { side: 'left', corner: 'top', bend: -1 },
  ];
  const seededFraction = seed => {
    let hash = 2166136261;
    for (const character of seed) hash = Math.imul(hash ^ character.charCodeAt(0), 16777619);
    return (hash >>> 0) / 4294967295;
  };

  buttons.forEach((button, index) => {
    const route = routes[index % routes.length];
    const seed = `${state.currentDoc}:${target.textContent}:${ids[index]}:${index}`;
    const distanceVariation = seededFraction(`${seed}:distance`);
    const heightVariation = seededFraction(`${seed}:height`);
    const curveVariation = seededFraction(`${seed}:curve`);
    const preferredSide = preferRight ? 'right' : 'left';
    const alternateSide = preferRight ? 'left' : 'right';
    let side = buttons.length > 1 && index % 2 === 1 ? alternateSide : preferredSide;
    if (side === 'right' && !rightFits && leftFits) side = 'left';
    if (side === 'left' && !leftFits && rightFits) side = 'right';
    const gap = minGap + distanceVariation * (innerWidth <= 899 ? 22 : 54);
    const verticalDistance = 54 + heightVariation * 58 + Math.floor(index / 4) * 18;
    const x = side === 'right' ? anchor.right + gap : anchor.left - gap - labelWidth;
    button.style.left = `${x}px`;
    button.style.top = `${anchor.y + route.bend * verticalDistance}px`;
    requestAnimationFrame(() => {
      const buttonY = parseFloat(button.style.top) - button.offsetHeight / 2;
      button.style.top = `${buttonY}px`;
      const endX = side === 'right' ? x : x + button.offsetWidth;
      const endY = buttonY + button.offsetHeight / 2;
      const sourceFragment = route.corner === 'top' ? firstFragment : lastFragment;
      const startX = side === 'right' ? sourceFragment.right : sourceFragment.left;
      const startY = route.corner === 'top' ? sourceFragment.top : sourceFragment.bottom;
      const dx = endX - startX;
      const dy = endY - startY;
      const referenceTightness = .42 + curveVariation * .24;
      const bubbleTightness = .34 + (1 - curveVariation) * .24;
      const control1X = startX + dx * referenceTightness;
      const control1Y = startY;
      const control2X = endX - dx * bubbleTightness;
      const control2Y = endY;
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('d', `M ${startX} ${startY} C ${control1X} ${control1Y}, ${control2X} ${control2Y}, ${endX} ${endY}`);
      path.setAttribute('fill', 'none');
      path.setAttribute('stroke', '#000');
      path.setAttribute('stroke-width', '2');
      path.setAttribute('vector-effect', 'non-scaling-stroke');
      connector.append(path);
    });
  });
}

function closeCitationPopup() {
  state.citationPopups.forEach((popup, target) => {
    target.classList.remove('selected');
    popup.remove();
  });
  state.citationPopups.clear();
}

function bindBibliographyLinks() {
  const visited = new Set(JSON.parse(localStorage.getItem('bibliography-links') || '[]'));
  el.bibliographyContent.querySelectorAll('a[href]').forEach(link => {
    if (visited.has(link.href)) link.classList.add('was-visited');
    link.addEventListener('click', () => {
      link.classList.add('was-visited');
      visited.add(link.href);
      localStorage.setItem('bibliography-links', JSON.stringify([...visited]));
    });
  });
}

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

function getCurrentSectionIndex() {
  const headings = state.activeSections;
  if (!headings.length) return -1;
  const y = el.readerScroll.scrollTop + 140;
  let idx = 0;
  headings.forEach((h, i) => { if (h.offsetTop <= y) idx = i; });
  return idx;
}

function updateFooterSection() {
  const headings = state.activeSections;
  const idx = getCurrentSectionIndex();
  if (idx < 0) {
    el.footerSection.textContent = '';
    el.footerSection.disabled = true;
    return;
  }
  el.footerSection.disabled = false;
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
  el.footerChapter.addEventListener('click', () => { el.readerScroll.scrollTop = 0; });
  el.footerSection.addEventListener('click', () => {
    const index = getCurrentSectionIndex();
    if (index < 0) return;
    const heading = state.activeSections[index];
    el.readerScroll.scrollTop = Math.max(0, el.readerContent.offsetTop + heading.offsetTop - 24);
  });
  el.leftArrow.addEventListener('click', () => setScreen(state.screen === 2 ? 1 : 0));
  el.rightArrow.addEventListener('click', () => setScreen(state.screen === 0 ? 1 : 2));
  el.tocNav.addEventListener('click', async e => {
    const button = e.target.closest('[data-doc]');
    if (!button) return;
    await loadDocument(button.dataset.doc);
    setScreen(1);
  });
  el.readerScroll.addEventListener('scroll', updateProgress, {passive: true});
  el.readerContent.addEventListener('click', e => { if (!e.target.closest('.citation-popup, .citation-callout')) closeCitationPopup(); });
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
