import { api } from "./api.js";
import { initContactForm } from "./contact.js";
import { initBlogDialog, openBlogDialog } from "./modal.js";
import { initMotion } from "./motion.js";
import { initNavigation, showFeature } from "./navigation.js";
import { initSlideshow } from "./slideshow.js";
import { initTheme } from "./theme.js";
import { activateFacade, createVideoFacade } from "./youtube.js";

const qs = (selector, root = document) => root.querySelector(selector);
const make = (tag, className, text) => { const node = document.createElement(tag); if (className) node.className = className; if (text !== undefined) node.textContent = text; return node; };
const appendText = (parent, tag, className, text) => { const node = make(tag, className, text); parent.append(node); return node; };

function renderProfile(profile) {
  if (!profile) return;
  if (profile.display_name) {
    document.querySelectorAll("[data-brand-name]").forEach((node) => { node.textContent = profile.display_name; });
    document.querySelectorAll(".brand-lockup").forEach((node) => { node.setAttribute("aria-label", `${profile.display_name} home`); });
    document.title = `${profile.display_name} · HR Systems & Automation Consultant`;
  }
  if (profile.location) {
    qs("[data-profile-location]").textContent = `Based in ${profile.location} · Supporting organizations across Ghana and West Africa`;
    const shortLocation = qs("[data-profile-location-short]");
    if (shortLocation) shortLocation.textContent = profile.location;
  }
  if (profile.phone) {
    const telephone = profile.phone.replace(/[^+\d]/g, "");
    document.querySelectorAll("[data-profile-phone]").forEach((node) => { node.textContent = profile.phone; node.href = `tel:${telephone}`; });
  }
  if (profile.email) {
    document.querySelectorAll("[data-profile-email]").forEach((node) => { node.textContent = profile.email; node.href = `mailto:${profile.email}`; });
  }
  const image = qs("[data-profile-image]");
  if (profile.profile_photo_url) { image.src = profile.profile_photo_url; image.alt = profile.display_name ? `Portrait of ${profile.display_name}` : "Consultant portrait"; image.hidden = false; qs("[data-profile-fallback]").hidden = true; }
  if (profile.intro_video_url) activateFacade(qs("[data-intro-video]"), profile.intro_video_url, "Consultant introduction");
}

function renderContent(key, block) {
  if (!block) return;
  if (key === "hero") {
    if (block.data?.eyebrow) qs("[data-hero-eyebrow]").textContent = block.data.eyebrow;
    if (block.title) qs("[data-hero-title]").textContent = block.title;
    if (block.body) qs("[data-hero-body]").textContent = block.body;
  } else if (key === "kpis" && Array.isArray(block.data?.items) && block.data.items.length) {
    const grid = qs("[data-kpi-grid]"); grid.replaceChildren();
    block.data.items.slice(0, 4).forEach((item) => { const card = make("article", "kpi-card"); appendText(card, "span", "kpi-value", item.value); appendText(card, "span", "kpi-label", item.label); if (item.context) appendText(card, "small", "kpi-context", item.context); grid.append(card); });
    qs("[data-kpi-section]").hidden = false;
  } else if (key === "about") {
    if (block.body) qs("[data-about-body]").textContent = block.body;
    const credentials = qs("[data-credentials]"); credentials.replaceChildren();
    (block.data?.credentials || []).forEach((value) => appendText(credentials, "span", "credential", value));
    if (Array.isArray(block.data?.approach) && block.data.approach.length) {
      const list = qs("[data-approach-list]"); list.replaceChildren();
      block.data.approach.slice(0, 4).forEach((step, index) => { const li = make("li"); appendText(li, "span", "", String(index + 1).padStart(2, "0")); const div = make("div"); appendText(div, "h3", "", step.title); appendText(div, "p", "", step.description); li.append(div); list.append(li); });
    }
  } else if (key === "contact") {
    if (block.title) qs("[data-contact-title]").textContent = block.title;
    if (block.body) qs("[data-contact-body]").textContent = block.body;
  }
}

function renderServices(items) {
  const grid = qs("[data-services-grid]"); grid.replaceChildren();
  items.forEach((item, index) => {
    const card = make("article", `content-card service-card${item.is_featured ? " featured" : ""}`);
    appendText(card, "span", "card-index", String(index + 1).padStart(2, "0")); appendText(card, "h3", "", item.title); appendText(card, "p", "", item.client_problem); appendText(card, "p", "", item.solution);
    const list = make("ul", "capability-list"); item.capabilities.forEach((value) => appendText(list, "li", "", value)); card.append(list);
    const link = appendText(card, "a", "text-link", `${item.cta_label} →`); link.href = "#contact"; link.dataset.serviceInterest = item.cta_context; card.append(link); grid.append(card);
  });
}

function renderPortfolio(items) {
  const grid = qs("[data-portfolio-grid]"); grid.replaceChildren();
  items.forEach((item, index) => {
    const card = make("article", "content-card"); appendText(card, "span", "card-index", String(index + 1).padStart(2, "0")); appendText(card, "h3", "", item.title); appendText(card, "p", "", item.description);
    const pills = make("div", "pill-row"); item.tech_pills.forEach((value) => appendText(pills, "span", "pill", value)); card.append(pills);
    if (item.youtube_video_url) card.append(createVideoFacade(item.youtube_video_url));
    if (item.external_link) { const link = appendText(card, "a", "text-link", "View hosted project ↗"); link.href = item.external_link; link.target = "_blank"; link.rel = "noopener noreferrer"; link.setAttribute("aria-label", `${item.title} (opens external site)`); card.append(link); }
    grid.append(card);
  });
}

function renderCaseStudies(items) {
  const grid = qs("[data-case-study-grid]"); grid.replaceChildren();
  items.forEach((item, index) => {
    const link = make("a", "case-card"); link.href = `case-studies/?slug=${encodeURIComponent(item.slug)}`; appendText(link, "span", "case-number", String(index + 1).padStart(2, "0")); const content = make("div"); appendText(content, "h3", "", item.title); appendText(content, "p", "", item.summary); link.append(content); appendText(link, "span", "", "Read case study →"); grid.append(link);
  });
}

function renderTestimonials(items) {
  const grid = qs("[data-testimonial-grid]"); grid.replaceChildren();
  items.forEach((item) => { const card = make("article", "content-card testimonial-card"); const quote = appendText(card, "blockquote", "", `“${item.quote}”`); const footer = make("footer"); appendText(footer, "strong", "", item.client_name); appendText(footer, "p", "", item.company); if (item.rating) appendText(footer, "span", "sr-only", `${item.rating} out of 5 stars`); card.append(quote, footer); grid.append(card); });
}

function renderBlog(items) {
  const grid = qs("[data-blog-grid]"); grid.replaceChildren();
  items.forEach((item) => { const card = make("article", "content-card"); if (item.published_at) appendText(card, "time", "card-index", new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(item.published_at))); appendText(card, "h3", "", item.title); appendText(card, "p", "", item.excerpt); const actions = make("div", "card-actions"); const button = appendText(actions, "button", "text-link", "Read more →"); button.type = "button"; button.addEventListener("click", () => openBlogDialog(item, button)); if (item.linkedin_url) { const link = appendText(actions, "a", "text-link", "LinkedIn ↗"); link.href = item.linkedin_url; link.target = "_blank"; link.rel = "noopener noreferrer"; } card.append(actions); grid.append(card); });
}

async function loadOptionalSections(features) {
  const loaders = {
    services: ["/api/services", renderServices], portfolio: ["/api/portfolio", renderPortfolio], case_studies: ["/api/case-studies", renderCaseStudies], testimonials: ["/api/testimonials", renderTestimonials], blog: ["/api/blog", renderBlog]
  };
  await Promise.all(Object.entries(loaders).map(async ([name, [path, render]]) => {
    if (!features[name]) { showFeature(name, false); return; }
    try { const result = await api(path); if (result.data.length) { render(result.data); showFeature(name, true); } else showFeature(name, false); } catch (_error) { showFeature(name, false); }
  }));
  const secondary = qs("[data-secondary-cta]");
  if (features.portfolio && !qs('[data-feature-section="portfolio"]').hidden) { secondary.href = "#portfolio"; secondary.textContent = "View selected work"; }
}

async function start() {
  initTheme(); initNavigation(); initBlogDialog(); initContactForm(); qs("[data-current-year]").textContent = new Date().getFullYear();
  const core = await Promise.allSettled([api("/api/profile"), api("/api/content/hero"), api("/api/content/kpis"), api("/api/content/about"), api("/api/content/contact"), api("/api/slideshow")]);
  if (core[0].status === "fulfilled") renderProfile(core[0].value.data);
  ["hero", "kpis", "about", "contact"].forEach((key, index) => { if (core[index + 1].status === "fulfilled") renderContent(key, core[index + 1].value.data); });
  if (core[5].status === "fulfilled") initSlideshow(core[5].value.data);
  try { const features = (await api("/api/features")).data; await loadOptionalSections(features); } catch (_error) { ["services", "portfolio", "case_studies", "testimonials", "blog"].forEach((name) => showFeature(name, false)); }
  requestAnimationFrame(initMotion);
}

start();


