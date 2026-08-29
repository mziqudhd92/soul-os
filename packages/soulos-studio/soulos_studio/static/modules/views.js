import { $ } from "./state.js";
import { docsCatalog, soulpacksLoaded } from "./ui-state.js";

export function switchView(view) {
  document.querySelectorAll(".btn.nav").forEach((el) => {
    const match = el.dataset.view === view;
    el.classList.toggle("active", match);
    if (el.id === "nav-studio") {
      el.classList.toggle("primary", view !== "studio");
    }
  });
  document.querySelectorAll(".view").forEach((el) => {
    const id = el.id.replace("view-", "");
    el.classList.toggle("view-active", id === view);
    el.classList.toggle("hidden", id !== view);
  });

  const studioToolbar = $("studio-toolbar");
  const toolbarDivider = $("toolbar-divider");
  const onStudio = view === "studio";
  if (studioToolbar) studioToolbar.classList.toggle("hidden", !onStudio);
  if (toolbarDivider) toolbarDivider.classList.toggle("hidden", !onStudio);

  if (view === "docs" && !docsCatalog) {
    import("./docs-tutorials.js").then((m) => m.loadDocsCatalog());
  }
  if (view === "tutorial" && !document.getElementById("tutorial-grid").children.length) {
    import("./docs-tutorials.js").then((m) => m.loadTutorials());
  }
  if (view === "soulpacks" && !soulpacksLoaded) {
    import("./soulpacks.js").then((m) => m.loadSoulPacksCatalog());
  }
}
