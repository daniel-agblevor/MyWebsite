export function initMotion() {
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduced || !window.gsap || !window.ScrollTrigger) return;
  window.gsap.registerPlugin(window.ScrollTrigger);
  const hero = window.gsap.timeline({ defaults: { duration: .65, ease: "power3.out" } });
  hero.from("[data-header]", { y: -22, opacity: 0 }).from("[data-hero-copy] > *", { y: 24, opacity: 0, stagger: .08 }, "-=.35").from("[data-hero-media]", { y: 30, scale: .97, opacity: 0 }, "-=.45").from("[data-kpi-section]:not([hidden])", { y: 20, opacity: 0 }, "-=.3");
  window.gsap.utils.toArray(".reveal, .content-card, .case-card").forEach((element) => {
    window.gsap.from(element, { scrollTrigger: { trigger: element, start: "top 90%", once: true }, y: 28, opacity: 0, duration: .62, ease: "power3.out" });
  });
  if (window.Lenis) {
    const lenis = new window.Lenis({ duration: 1.05, smoothWheel: true });
    lenis.on("scroll", window.ScrollTrigger.update);
    window.gsap.ticker.add((time) => lenis.raf(time * 1000));
    window.gsap.ticker.lagSmoothing(0);
  }
  window.ScrollTrigger.refresh();
}

