// Focus/hover clipping check for Flatcap TV on the THROWAWAY demo server.
//   node qa/focus-clip.mjs <css file | none> <out dir> [WxH,WxH] [desktop,tv]
// For the first and a middle card of the first portrait row, under hover and keyboard focus: the rect of the ring frame
// (`.cardScalable`, the ring is `::after{inset:0}`), the visible rect of every clipping ancestor, and whether the ring is inside all of them.
import fs from 'fs';
import { launch, login, BASE, setBrandingCss, items } from './lib.mjs';

const [cssFile, outDir = '/tmp/fc-fix1/shots', sizes = '1440x900,1920x1080', layouts = 'desktop,tv'] = process.argv.slice(2);
fs.mkdirSync(outDir, { recursive: true });
await setBrandingCss(cssFile === 'none' ? '' : fs.readFileSync(cssFile, 'utf8'));
const ctx = await items();
const { b, p } = await launch({ width: 1440, height: 900, scheme: 'dark' });
await login(p);
await p.evaluate(([u]) => localStorage.setItem(`${u}-appTheme`, 'dark'), [ctx.uid]);

const measure = () => p.evaluate(() => {
  const el = document.querySelector('.card.overflowPortraitCard:is(:hover,:focus-within,.show-focus:focus)');
  if (!el) return null;
  const R = (e) => { const r = e.getBoundingClientRect(); return { l: +r.left.toFixed(1), t: +r.top.toFixed(1), r: +r.right.toFixed(1), b: +r.bottom.toFixed(1) }; };
  const frame = el.querySelector('.cardScalable');
  const ring = R(frame);
  const vis = { l: 0, t: 0, r: innerWidth, b: innerHeight };
  const clips = [];
  for (let a = frame.parentElement; a && a !== document.documentElement; a = a.parentElement) {
    const cs = getComputedStyle(a);
    const paint = /paint|strict|content/.test(cs.contain);
    const x = cs.overflowX !== 'visible' || paint, y = cs.overflowY !== 'visible' || paint;
    if (x || y) {
      const r = a.getBoundingClientRect();
      clips.push({ cls: (a.className || a.tagName).toString().slice(0, 40), ox: cs.overflowX, oy: cs.overflowY, contain: cs.contain, ...R(a) });
      if (x) { vis.l = Math.max(vis.l, r.left); vis.r = Math.min(vis.r, r.right); }
      if (y) { vis.t = Math.max(vis.t, r.top); vis.b = Math.min(vis.b, r.bottom); }
    }
  }
  // the scroller's own box also counts as a clip (the row must not need room outside it)
  const sc = el.closest('.emby-scroller');
  if (sc) { const r = sc.getBoundingClientRect(); vis.l = Math.max(vis.l, r.left); vis.r = Math.min(vis.r, r.right); vis.t = Math.max(vis.t, r.top); vis.b = Math.min(vis.b, r.bottom); clips.push({ cls: 'SCROLLER ' + sc.className.slice(0, 30), ...R(sc) }); }
  const after = getComputedStyle(frame, '::after');
  const img = el.querySelector('.cardImageContainer');
  const text = el.querySelector('.cardText');
  const cx = (ring.l + ring.r) / 2, cy = (ring.t + ring.b) / 2;
  const hit = document.elementFromPoint(cx, cy);
  return {
    ring, visible: vis, clips, slot: R(el.querySelector('.cardBox')), text: text ? R(text) : null,
    insideAllClips: ring.l >= vis.l - 0.5 && ring.t >= vis.t - 0.5 && ring.r <= vis.r + 0.5 && ring.b <= vis.b + 0.5,
    margins: { l: +(ring.l - vis.l).toFixed(1), t: +(ring.t - vis.t).toFixed(1), r: +(vis.r - ring.r).toFixed(1), b: +(vis.b - ring.b).toFixed(1) },
    after: { opacity: after.opacity, border: after.borderTopWidth + ' ' + after.borderTopColor, outline: after.outlineWidth + ' ' + after.outlineColor + ' off ' + after.outlineOffset, radius: after.borderTopLeftRadius, z: after.zIndex, pe: after.pointerEvents },
    imgTransform: getComputedStyle(img).transform, frameOverflow: getComputedStyle(frame).overflow,
    hit: hit ? (hit.className || hit.tagName).toString().slice(0, 50) : null,
    cardBoxTransform: getComputedStyle(el.querySelector('.cardBox')).transform, cardBoxOutline: getComputedStyle(el.querySelector('.cardBox')).outlineStyle,
  };
});

const out = {};
for (const layout of layouts.split(',')) {
  await p.evaluate(([l]) => { if (l === 'tv') localStorage.setItem('layout', 'tv'); else localStorage.removeItem('layout'); }, [layout]);
  for (const size of sizes.split(',')) {
    const [w, h] = size.split('x').map(Number);
    await p.setViewportSize({ width: w, height: h });
    await p.goto(`${BASE}/web/#/home`); await p.reload(); await p.waitForTimeout(5500);
    const n = (await p.$$('.card.overflowPortraitCard')).length;
    const rect = (sel) => p.evaluate(([i, s]) => { const c = document.querySelectorAll('.card.overflowPortraitCard')[i]; const o = c.closest('.emby-scroller').getBoundingClientRect(); const r = c.querySelector(s).getBoundingClientRect(); return [r.left - o.left, r.top - o.top, r.right - o.left, r.bottom - o.top].map((x) => +x.toFixed(1)); }, [0, sel]);
    const rest = { frame: await rect('.cardScalable'), text: await rect('.cardText') };
    for (const [name, idx] of [['first', 0], ['middle', Math.min(3, n - 1)]]) {
      for (const mode of ['hover', 'focus']) {
        await p.mouse.move(2, 2); await p.evaluate(() => document.activeElement?.blur());
        await p.waitForTimeout(300);
        const el = (await p.$$('.card.overflowPortraitCard'))[idx];
        await el.scrollIntoViewIfNeeded();
        const key = `${layout}-${size}-${name}-${mode}`;
        if (mode === 'hover') {
          const bb = await (await el.$('.cardScalable')).boundingBox();
          await p.mouse.move(bb.x + bb.width * 0.5, bb.y + bb.height * 0.3);
        } else {
          await p.keyboard.press('Tab');
          await p.evaluate((i) => { const c = document.querySelectorAll('.card.overflowPortraitCard')[i]; (document.documentElement.classList.contains('layout-tv') ? c : c.querySelector('a.cardContent')).focus(); }, idx);
        }
        await p.waitForTimeout(700);
        const m = await measure();
        if (m && idx === 0) { m.restFrame = rest.frame; m.restText = rest.text; m.frameNowVsRest = (await rect('.cardScalable')); m.textNowVsRest = (await rect('.cardText')); }
        out[key] = m;
        await p.screenshot({ path: `${outDir}/${key}.png` });
        console.log(key, m ? JSON.stringify({ inside: m.insideAllClips, margins: m.margins, img: m.imgTransform, after: m.after.opacity, hit: m.hit }) : 'NO MATCH');
      }
    }
  }
}
fs.writeFileSync(`${outDir}/measure.json`, JSON.stringify(out, null, 1));
await b.close();
