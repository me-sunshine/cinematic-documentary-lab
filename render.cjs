// Renders film.html to numbered frames by stepping every animation to an exact time, so the video is
// identical on every run. Usage: node render.cjs [fps] [seconds] ; then encode with ffmpeg (see README).
const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');

const here = __dirname;
const fps = Number(process.argv[2] || 30);
const seconds = Number(process.argv[3] || 45);
const only = process.argv[4] ? process.argv[4].split(',').map(Number) : null; // optional: still frames at these times
const out = path.join(here, 'out', only ? 'stills' : 'frames');
fs.rmSync(out, { recursive: true, force: true });
fs.mkdirSync(out, { recursive: true });

(async () => {
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
await page.goto('file://' + path.join(here, 'film.html') + '#raw');
await page.evaluate(() => document.fonts.ready);
await page.evaluate(() => document.getAnimations().forEach((a) => a.pause()));

// Seek every animation, then wait two animation frames so the compositor has painted the new state.
const seek = (ms) => page.evaluate((t) => new Promise((done) => {
  document.getAnimations().forEach((a) => { a.currentTime = t; });
  document.body.getBoundingClientRect();
  requestAnimationFrame(() => requestAnimationFrame(done));
}), ms);
if (only) {
  for (const t of only) { await seek(t * 1000); await page.screenshot({ path: path.join(out, `t${String(t).replace('.', '_')}.png`) }); }
} else {
  const total = Math.round(fps * seconds);
  for (let i = 0; i < total; i++) {
    await seek((i * 1000) / fps);
    await page.screenshot({ path: path.join(out, `f${String(i).padStart(5, '0')}.png`) });
  }
  console.log(`${total} frames written to ${out}`);
}
await browser.close();
})();
