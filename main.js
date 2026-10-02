// Theme toggle: follows the OS until the visitor picks a theme, then remembers it.
(() => {
  const root = document.documentElement;
  const button = document.querySelector(".theme-toggle");
  const systemDark = window.matchMedia("(prefers-color-scheme: dark)");

  const current = () => root.dataset.theme || (systemDark.matches ? "dark" : "light");

  button?.addEventListener("click", () => {
    const next = current() === "dark" ? "light" : "dark";
    root.dataset.theme = next;
    try { localStorage.setItem("theme", next); } catch (_) { /* private mode: keep it for this visit only */ }
  });

  // Show the CollabEdit screenshot only once it has loaded, so a missing file never leaves a broken frame.
  const shot = document.getElementById("collabedit-shot");
  const img = shot?.querySelector("img");
  if (img) {
    const reveal = () => { shot.hidden = false; };
    if (img.complete && img.naturalWidth) reveal();
    else img.addEventListener("load", reveal, { once: true });
  }
})();
