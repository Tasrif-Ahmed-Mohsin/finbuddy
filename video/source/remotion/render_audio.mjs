// Audio only: node render_audio.mjs out.wav
import { bundle } from '@remotion/bundler';
import { renderMedia, selectComposition } from '@remotion/renderer';
import path from 'node:path';
const out = process.argv[2];
const serveUrl = await bundle({ entryPoint: path.resolve('src/index.ts'), publicDir: path.resolve('public') });
const composition = await selectComposition({ serveUrl, id: 'Bluefin' });
const t0 = Date.now();
await renderMedia({ composition, serveUrl, codec: 'wav', outputLocation: out, concurrency: 10 });
console.log('done', out, ((Date.now() - t0) / 1000).toFixed(0), 's');
