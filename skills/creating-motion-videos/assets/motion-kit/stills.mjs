// Render several stills from ONE bundle (much faster than `remotion still` per frame).
//   COMP=MyVideo node scripts/stills.mjs 30 120 236 900          → draft (no motion blur/grain), 0.5x
//   COMP=MyVideo node scripts/stills.mjs --full 236 900           → full resolution with motion blur
// Optional: ENTRY (default src/index.ts), OUT (default out/stills). Needs @remotion/bundler and @remotion/renderer at the
// same version as remotion. The composition must accept a `draft` prop (see context.tsx).
import {bundle} from '@remotion/bundler';
import {getCompositions, renderStill, selectComposition} from '@remotion/renderer';
import fs from 'node:fs';
import path from 'node:path';

const args = process.argv.slice(2);
const full = args.includes('--full');
const frames = args.filter((a) => !a.startsWith('--')).map(Number);
if (!frames.length || frames.some((n) => !Number.isFinite(n) || n < 0)) {
  console.error('Pemakaian: COMP=<id> node scripts/stills.mjs [--full] <frame> [<frame> ...]');
  process.exit(2);
}
const entry = path.resolve(process.env.ENTRY || 'src/index.ts');
const outDir = path.resolve(process.env.OUT || 'out/stills');
const inputProps = {draft: !full};
const serveUrl = await bundle({entryPoint: entry, publicDir: path.resolve('public')});
const id = process.env.COMP;
if (!id) {
  const all = await getCompositions(serveUrl, {inputProps});
  console.error(`Set COMP=<id>. Komposisi tersedia: ${all.map((c) => c.id).join(', ')}`);
  process.exit(2);
}
const composition = await selectComposition({serveUrl, id, inputProps});
fs.mkdirSync(outDir, {recursive: true});
for (const frame of frames) {
  if (frame >= composition.durationInFrames) {
    console.error(`frame ${frame} di luar durasi ${composition.durationInFrames}, dilewati`);
    continue;
  }
  const output = path.join(outDir, `${id}_${String(frame).padStart(4, '0')}${full ? '_full' : ''}.jpg`);
  await renderStill({composition, serveUrl, output, frame, inputProps, imageFormat: 'jpeg', jpegQuality: 75, scale: full ? 1 : 0.5});
  console.log('still', output);
}
