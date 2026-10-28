// Deterministic vector product icon; no external image, font, or network dependency.
const fs = require('node:fs');
const path = require('node:path');
const sharp = require('sharp');
const folder = path.resolve(__dirname, '../extension/icons');
fs.mkdirSync(folder, { recursive: true });
const svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128"><rect x="16" y="16" width="96" height="96" rx="24" fill="#235c50"/><path d="M36 53h54l-5-15H41z" fill="#dcebe3"/><path d="M39 59v29h42V59" fill="none" stroke="#fff" stroke-width="6" stroke-linejoin="round"/><path d="M53 87V70h14v17" fill="none" stroke="#fff" stroke-width="5"/><path d="m79 69 20 17-10 2-5 11z" fill="#f1cb80" stroke="#235c50" stroke-width="3" stroke-linejoin="round"/></svg>';
(async () => { for (const size of [16,32,48,128]) await sharp(Buffer.from(svg)).resize(size,size).png().toFile(path.join(folder,`icon${size}.png`)); })().catch(error => { console.error(error); process.exitCode=1; });
