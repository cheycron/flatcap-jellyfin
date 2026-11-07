// Flatcap TV screenshots at 1920x1080 on the THROWAWAY demo server: desktop layout and TV layout (`layout-tv`).
//   node qa/shoot-tv.mjs <css file | none> <out dir> [desktop,tv] [view,view,...] [--je]
// Views: home, library, detail, focus. The layout is chosen the way Jellyfin stores it (localStorage `layout`).
// --je injects a minimal stand-in for the Jellyfin Enhanced header row (only when the plugin is not installed).
import fs from 'fs';
import { launch, login, BASE, setBrandingCss, items } from './lib.mjs';

const args = process.argv.slice(2).filter((a) => !a.startsWith('--'));
const flags = process.argv.slice(2).filter((a) => a.startsWith('--'));
const [cssFile, outDir = '/tmp/fc-tv/shots', layouts = 'desktop,tv', only] = args;
fs.mkdirSync(outDir, { recursive: true });
await setBrandingCss(cssFile && cssFile !== 'none' ? fs.readFileSync(cssFile, 'utf8') : '');
const ctx = await items();
const { b, p } = await launch({ width: 1920, height: 1080, scheme: 'dark' });
await login(p);
await p.evaluate(([u, bd]) => { localStorage.setItem(`${u}-appTheme`, 'dark'); if (bd === 'false') localStorage.removeItem(`${u}-enableBackdrops`); else localStorage.setItem(`${u}-enableBackdrops`, bd); }, [ctx.uid, process.env.BACKDROPS || 'true']);

const go = async (hash, wait = 4500) => { await p.goto(`${BASE}/web/#/${hash}`); await p.reload(); await p.waitForTimeout(wait); };
const jeStandIn = async () => {
  if (!flags.includes('--je')) return;
  await p.evaluate(() => {
    const bar = document.querySelector('header.MuiAppBar-root');
    if (bar && !bar.querySelector('.je-header-actions-row')) {
      const row = document.createElement('div');
      row.className = 'je-header-actions-row';
      row.textContent = 'JE';
      bar.appendChild(row);
    }
  });
};
const V = {
  async home() {
    await go('home'); await jeStandIn();
    // TV layout is taller: scroll so Continue Watching and the Recently Added posters are whole (the tail of My Media stays above)
    if (await p.evaluate(() => document.documentElement.classList.contains('layout-tv'))) { await p.evaluate((y) => window.scrollTo(0, y), +(process.env.TV_HOME_SCROLL || 0)); await p.waitForTimeout(600); }
  },
  async library() { await go(`movies?topParentId=${ctx.views.Movies}&collectionType=movies`, 5500); },
  async detail() { await go(`details?id=${ctx.by[process.env.DETAIL_ITEM || 'Tears of Steel']}`, 5500); },
  async focus() {
    await go('home', 5000);
    const tv = await p.evaluate(() => document.documentElement.classList.contains('layout-tv'));
    // scroll the Recently Added rows into view, then focus a middle poster the way a keyboard / remote does (:focus-visible, TV layout .show-focus)
    await p.evaluate((y) => window.scrollTo(0, y), tv ? 1050 : 660);
    await p.waitForTimeout(500);
    await p.keyboard.press('Tab');
    await p.evaluate(([tv, n]) => {
      const row = [...document.querySelectorAll('.homePage:not(.hide) .verticalSection')].filter((s) => s.querySelector('.itemsContainer .card'))[2];
      const cards = row.querySelectorAll('.card');
      const c = cards[n]; (tv ? c : c.querySelector('a.cardContent') || c).focus({ preventScroll: true });
    }, [tv, +(process.env.FOCUS_CARD || 3)]);
    await p.waitForTimeout(900);
  },
};
for (const layout of layouts.split(',')) {
  await p.evaluate(([l]) => { if (l === 'tv') localStorage.setItem('layout', 'tv'); else localStorage.removeItem('layout'); }, [layout]);
  for (const k of (only ? only.split(',') : Object.keys(V))) {
    try { await V[k](); await p.screenshot({ path: `${outDir}/${k}-${layout}.png` }); console.log('ok', layout, k); } catch (e) { console.log('FAIL', layout, k, String(e).split('\n')[0]); }
  }
}
await b.close();
