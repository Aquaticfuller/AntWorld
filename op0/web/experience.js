"use strict";

// Purely presentational, opt-in focus mode for observing an individual colony.
// No Core command, archive write, or biological state change is issued.
(() => {
  function init() {
    const header = document.querySelector(".space .panel-head");
    if (!header || document.getElementById("focus-view")) return;

    const button = document.createElement("button");
    button.id = "focus-view";
    button.type = "button";
    button.setAttribute("aria-pressed", "false");
    button.setAttribute("aria-keyshortcuts", "F");
    button.className = "focus-view-toggle";

    const refresh = () => {
      const active = document.body.classList.contains("focus-view");
      const chinese = document.documentElement.lang === "zh-CN";
      button.textContent = active
        ? (chinese ? "退出专注观察" : "Exit focus")
        : (chinese ? "专注观察" : "Focus on colony");
      button.setAttribute("aria-pressed", String(active));
      button.title = chinese ? "按 F 切换，Esc 退出" : "Press F to toggle, Esc to exit";
    };

    const toggle = force => {
      const current = document.body.classList.contains("focus-view");
      document.body.classList.toggle("focus-view", force === undefined ? !current : force);
      refresh();
      window.dispatchEvent(new Event("resize"));
    };
    button.addEventListener("click", () => toggle());
    header.append(button);

    document.addEventListener("keydown", event => {
      const tag = event.target?.tagName?.toLowerCase();
      if (["input", "select", "textarea"].includes(tag) ||
          event.target?.isContentEditable || event.altKey || event.metaKey || event.ctrlKey) return;
      if (event.key === "Escape" && document.body.classList.contains("focus-view")) {
        toggle(false);
      } else if (event.key.toLowerCase() === "f" && !event.repeat) {
        toggle();
        event.preventDefault();
      }
    });

    const mutation = new MutationObserver(refresh);
    mutation.observe(document.documentElement, {attributes:true, attributeFilter:["lang"]});
    refresh();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, {once:true});
  else init();
})();
