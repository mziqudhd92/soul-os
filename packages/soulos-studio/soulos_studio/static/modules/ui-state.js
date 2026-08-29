/** Shared view/catalog flags for Studio navigation. */

export let activeTab = "studio";
export let docsCatalog = null;
export let soulpacksLoaded = false;
export let activeDocPath = null;

export function setSoulpacksLoaded(value) {
  soulpacksLoaded = value;
}

export function setDocsCatalog(value) {
  docsCatalog = value;
}

export function setActiveDocPath(value) {
  activeDocPath = value;
}
