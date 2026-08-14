const path = require('path');
const fs = require('fs');
const https = require('https');
const http = require('http');
const { URL } = require('url');
const crypto = require('crypto');

/**
 * Upload a file to ltpp.vip/upload via the direct REST API.
 *
 * Bypasses puppeteer (which is unavailable / slow in this env) by calling
 * the three upload endpoints directly:
 *   POST /api/upload/register  (X-File-Id, X-File-Name, X-Total-Chunks)
 *   POST /api/upload/save      (X-File-Id, X-Chunk-Index, X-Chunk-Size, X-File-Name) — body = raw bytes
 *   POST /api/upload/merge     (X-File-Id, X-File-Name) — JSON body
 *
 * Usage: node upload.js <file-path> [file-path2 ...]
 *
 * Output: JSON array of { name, url, size } for each uploaded file.
 */

const HOST = 'ltpp.vip';
const BASE = 'https://' + HOST;
const CHUNK_SIZE = 5 * 1024 * 1024; // 5MB

function request(method, urlPath, headers, body) {
  return new Promise((resolve, reject) => {
    const u = new URL(BASE + urlPath);
    const opts = {
      method,
      hostname: u.hostname,
      port: u.port || 443,
      path: u.pathname + u.search,
      headers: { ...headers }
    };
    if (body && !opts.headers['Content-Length']) {
      opts.headers['Content-Length'] = Buffer.byteLength(body);
    }
    const lib = u.protocol === 'https:' ? https : http;
    const req = lib.request(opts, (res) => {
      let data = '';
      res.on('data', (c) => (data += c));
      res.on('end', () => resolve({ status: res.statusCode, body: data }));
    });
    req.on('error', reject);
    if (body) req.write(body);
    req.end();
  });
}

async function uploadOne(filePath) {
  const resolved = path.resolve(filePath);
  if (!fs.existsSync(resolved)) {
    console.error(`File not found: ${resolved}`);
    return null;
  }
  const fileBuffer = fs.readFileSync(resolved);
  const fileName = path.basename(resolved);
  const fileSize = fileBuffer.length;
  const fileHash = crypto.createHash('md5').update(fileBuffer).digest('hex');
  const fileId = 'upload_' + Date.now() + '_' + crypto.randomBytes(4).toString('hex');
  const totalChunks = Math.max(1, Math.ceil(fileSize / CHUNK_SIZE));

  console.log(`Uploading: ${fileName} (${fileSize} bytes, ${totalChunks} chunk(s))...`);

  // 1. register
  const reg = await request('POST', '/api/upload/register', {
    'Content-Type': 'application/json',
    'X-File-Id': fileId,
    'X-File-Name': fileName,
    'X-Total-Chunks': String(totalChunks)
  }, JSON.stringify({
    fileName, fileSize, fileHash, chunkSize: CHUNK_SIZE, totalChunks
  }));
  let regJson;
  try { regJson = JSON.parse(reg.body); } catch { regJson = {}; }
  if (regJson.code !== 200) {
    console.error(`  register failed: ${reg.body}`);
    return null;
  }

  // 2. save chunks
  for (let i = 0; i < totalChunks; i++) {
    const start = i * CHUNK_SIZE;
    const end = Math.min(fileSize, start + CHUNK_SIZE);
    const chunk = fileBuffer.slice(start, end);
    const save = await request('POST', '/api/upload/save', {
      'Content-Type': 'application/octet-stream',
      'X-File-Id': fileId,
      'X-File-Name': fileName,
      'X-Chunk-Index': String(i),
      'X-Chunk-Size': String(chunk.length)
    }, chunk);
    let saveJson;
    try { saveJson = JSON.parse(save.body); } catch { saveJson = {}; }
    if (saveJson.code !== 200) {
      console.error(`  save chunk ${i} failed: ${save.body}`);
      return null;
    }
  }

  // 3. merge
  const merge = await request('POST', '/api/upload/merge', {
    'Content-Type': 'application/json',
    'X-File-Id': fileId,
    'X-File-Name': fileName
  }, JSON.stringify({
    fileName, fileHash, totalChunks
  }));
  let mergeJson;
  try { mergeJson = JSON.parse(merge.body); } catch { mergeJson = {}; }
  if (mergeJson.code !== 200 || !mergeJson.url) {
    console.error(`  merge failed: ${merge.body}`);
    return null;
  }

  const fullUrl = 'https://ltpp.vip' + mergeJson.url;
  console.log(`  OK: ${fullUrl}`);
  return { name: fileName, url: fullUrl, size: fileSize };
}

(async () => {
  const args = process.argv.slice(2);
  if (args.length === 0 || args[0] === '--help') {
    console.log('Usage: node upload.js <file-path> [file-path2 ...]');
    console.log('Uploads files to ltpp.vip/upload via direct REST API and outputs JSON with URLs.');
    process.exit(args.length === 0 ? 1 : 0);
  }

  const results = [];
  for (const fp of args) {
    const r = await uploadOne(fp);
    if (r) results.push(r);
  }

  console.log('\n=== RESULTS ===');
  console.log(JSON.stringify(results, null, 2));
})();
