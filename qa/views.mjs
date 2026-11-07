// The views the QA scripts visit on the throwaway demo server (1440x900). Each view navigates and leaves the page ready.
import { BASE } from './lib.mjs';

export function views(p, { by, views: vw, uid }, { hold = true } = {}) {
  const go = async (hash, wait = 4000) => { await p.goto(`${BASE}/web/#/${hash}`); await p.reload(); await p.waitForTimeout(wait); };
  return {
    async home() { await go('home'); },
    async library() { await go(`movies?topParentId=${vw.Movies}&collectionType=movies`, 5000); },
    async detail() { await go(`details?id=${by['Tears of Steel']}`, 5000); },
    async actionsheet() {
      await go(`details?id=${by['Sintel']}`, 4000);
      await p.click('.btnMoreCommands:visible'); await p.waitForTimeout(1200);
    },
    async player() {
      await go(`details?id=${by['Sintel']}`, 4000);
      await p.click('.btnResume:visible, .btnPlay:visible'); await p.waitForTimeout(7000);
      await p.mouse.move(700, 500); await p.mouse.move(720, 520); await p.waitForTimeout(800);
    },
    async dashboard() { await go('dashboard', 5000); },
    async settings() { await go(`mypreferencesdisplay?userId=${uid}`, 5000); },
    async login() { await go('login', 3000); },
  };
}
