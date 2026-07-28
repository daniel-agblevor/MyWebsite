export function youtubeId(url) {
  if (!url) return null;
  try {
    const parsed = new URL(url);
    if (parsed.hostname.endsWith("youtu.be")) return parsed.pathname.split("/").filter(Boolean)[0] || null;
    if (parsed.pathname.startsWith("/shorts/") || parsed.pathname.startsWith("/embed/")) return parsed.pathname.split("/")[2] || null;
    return parsed.searchParams.get("v");
  } catch (_error) { return null; }
}

export function activateFacade(button, url, title = "YouTube video") {
  const id = youtubeId(url);
  if (!button || !id) return;
  button.hidden = false;
  button.addEventListener("click", () => {
    const iframe = document.createElement("iframe");
    iframe.className = "video-frame";
    iframe.title = title;
    iframe.allow = "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share";
    iframe.allowFullscreen = true;
    iframe.src = `https://www.youtube-nocookie.com/embed/${encodeURIComponent(id)}?autoplay=1`;
    button.replaceWith(iframe);
  }, { once: true });
}

export function createVideoFacade(url, label = "Watch project video") {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "video-facade";
  const play = document.createElement("span"); play.className = "play-button"; play.ariaHidden = "true"; play.textContent = "▶";
  const text = document.createElement("span");
  const strong = document.createElement("strong"); strong.textContent = label;
  const small = document.createElement("small"); small.textContent = "Loads YouTube when selected";
  text.append(strong, small); button.append(play, text);
  activateFacade(button, url, label);
  return button;
}

