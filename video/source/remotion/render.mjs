// Full render: node render.mjs out.mp4
import { bundle } from '@remotion/bundler';
import { renderMedia, selectComposition } from '@remotion/renderer';
import path from 'node:path';
const out = process.argv[2];
const serveUrl = await bundle({ entryPoint: path.resolve('src/index.ts'), publicDir: path.resolve('public') });
const composition = await selectComposition({ serveUrl, id: 'Bluefin' });
let last = -1;
const t0 = Date.now();
await renderMedia({
  composition, serveUrl, codec: 'h264', outputLocation: out, crf: 17, concurrency: 10, audioCodec: 'aac', audioBitrate: '320k',
  pixelFormat: 'yuv420p', x264Preset: 'medium',
  onProgress: ({ progress }) => { const p = Math.floor(progress * 20); if (p !== last) { last = p; console.log(`${(progress * 100).toFixed(0)}% ${((Date.now() - t0) / 1000).toFixed(0)}s`); } },
});
console.log('done', out, ((Date.now() - t0) / 1000).toFixed(0), 's');
