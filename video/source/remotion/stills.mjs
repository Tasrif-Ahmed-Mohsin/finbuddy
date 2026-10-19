// Render chosen frames of the film as PNGs (one bundle, many stills): node stills.mjs out_dir frame1 frame2 ...
import { bundle } from '@remotion/bundler';
import { renderStill, selectComposition, ensureBrowser } from '@remotion/renderer';
import path from 'node:path';
import fs from 'node:fs';

const [outDir, ...frames] = process.argv.slice(2);
fs.mkdirSync(outDir, { recursive: true });
await ensureBrowser();
const serveUrl = await bundle({ entryPoint: path.resolve('src/index.ts'), publicDir: path.resolve('public') });
const composition = await selectComposition({ serveUrl, id: 'Bluefin' });
for (const fr of frames) {
  const frame = Number(fr);
  await renderStill({ composition, serveUrl, frame, output: path.join(outDir, `f${String(frame).padStart(5, '0')}.png`), scale: 0.5 });
  console.log('still', frame);
}
