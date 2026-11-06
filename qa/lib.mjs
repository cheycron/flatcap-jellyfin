// Shared helpers for the Flatcap Jellyfin QA scripts (throwaway server only).
// Needs `playwright-core` (npm i playwright-core) and a Chromium binary: CHROME=/path/to/chrome.
import { chromium } from 'playwright-core';
import fs from 'fs';

export const BASE = process.env.JF || 'http://127.0.0.1:18096';
export const CHROME = process.env.CHROME || `${process.env.HOME}/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome`;
export const USER = 'ada', PASS = 'Demo-pass-2026!';
const AUTH = 'MediaBrowser Client="Flatcap QA", Device="qa", DeviceId="flatcap-qa", Version="1.0"';
const hdr = (token) => ({ 'Content-Type': 'application/json', Authorization: token ? `${AUTH}, Token="${token}"` : AUTH });

export async function api(method, path, body, token) {
  const r = await fetch(BASE + path, { method, headers: hdr(token), body: body === undefined ? undefined : JSON.stringify(body) });
  const t = await r.text();
  if (!r.ok) throw new Error(`${method} ${path} -> ${r.status} ${t.slice(0, 200)}`);
  return t ? JSON.parse(t) : null;
}

export async function admin() {
  const a = await api('POST', '/Users/AuthenticateByName', { Username: USER, Pw: PASS });
  return { token: a.AccessToken, uid: a.User.Id };
}

export async function setBrandingCss(css) {
  const { token } = await admin();
  const cfg = await api('GET', '/System/Configuration/branding', undefined, token);
  cfg.CustomCss = css;
  await api('POST', '/System/Configuration/branding', cfg, token);
}

export async function items() {
  const { token, uid } = await admin();
  const r = await api('GET', `/Items?userId=${uid}&Recursive=true&IncludeItemTypes=Movie,Series,Episode`, undefined, token);
  const views = await api('GET', `/UserViews?userId=${uid}`, undefined, token);
  return {
    by: Object.fromEntries(r.Items.map((i) => [i.Name, i.Id])),
    views: Object.fromEntries(views.Items.map((v) => [v.Name, v.Id])), uid, token,
  };
}

export async function launch({ scheme = 'dark', width = 1440, height = 900, forcedColors, reducedMotion } = {}) {
  const b = await chromium.launch({ executablePath: CHROME, args: ['--no-sandbox', '--autoplay-policy=no-user-gesture-required'] });
  const ctx = await b.newContext({ viewport: { width, height }, colorScheme: scheme, locale: 'en-US', forcedColors, reducedMotion });
  const p = await ctx.newPage();
  return { b, ctx, p };
}

export async function login(p) {
  await p.goto(`${BASE}/web/#/login.html`);
  await p.waitForFunction(() => location.hash.startsWith('#/login?'), null, { timeout: 20000 });
  await p.waitForSelector('#txtManualName', { state: 'visible' });
  await p.waitForTimeout(1000);
  await p.fill('#txtManualName', USER);
  await p.fill('#txtManualPassword', PASS);
  await p.click('.button-submit');
  await p.waitForTimeout(3000);
  await p.goto(`${BASE}/web/#/home.html`);
  await p.waitForFunction(() => location.hash.startsWith('#/home'), null, { timeout: 30000 });
  await p.waitForTimeout(2000);
}

export const save = (name, o) => fs.writeFileSync(name, JSON.stringify(o, null, 1));
