import { build } from 'vite';
import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

await build({ configFile: fileURLToPath(new URL('../vite.config.js', import.meta.url)) });
const notices = await Promise.all(['react', 'react-dom', 'scheduler'].map(async name =>
  `${name}\n${await readFile(new URL(`../node_modules/${name}/LICENSE`, import.meta.url), 'utf8')}`));
await writeFile(new URL('../../src/tripmate/portal/static/portal-queue.LICENSE.txt', import.meta.url),
  notices.join('\n\n'));
