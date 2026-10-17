import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import sharp from 'sharp';

const root = path.dirname(fileURLToPath(import.meta.url));
const svgPath = path.join(root, 'outputs', 'government_bond_yields_2020_latest.svg');
const pngPath = path.join(root, 'outputs', 'government_bond_yields_2020_latest.png');
await fs.mkdir(path.dirname(pngPath), { recursive: true });
await sharp(svgPath, { density: 144 })
  .resize({ width: 3840, height: 2160, fit: 'fill' })
  .png({ compressionLevel: 9 })
  .toFile(pngPath);
console.log(`Wrote ${pngPath} at 3840 × 2160.`);
