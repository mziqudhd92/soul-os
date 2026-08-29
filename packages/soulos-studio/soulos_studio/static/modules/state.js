/* SoulOS Studio — vanilla JS, no build step */

export const state = {
  meta: null,
  form: null,
  soul: null,
  avatarId: null,
  valid: true,
  lastPrepare: null,
  kernelUrl: "http://localhost:8000",
};

export const wizard = {
  step: 0,
  form: null,
  steps: [],
};

export const ATTACHMENT_HINTS = {
  Secure: "Warm and consistent — connects without anxiety or avoidance.",
  "Anxious-Preoccupied": "Sensitive to rejection — seeks reassurance in relationships.",
  "Dismissive-Avoidant": "Values independence — may appear emotionally distant.",
};

export const THEME_KEY = "soulos-studio-theme";

export const $ = (id) => document.getElementById(id);
