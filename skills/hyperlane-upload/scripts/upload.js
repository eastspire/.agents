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
 * After a successful merge, performs a verification step: GET the returned
 * URL, download the body, and compare both its size and MD5 against the
 * original. This catches silent server-side failures (e.g. merge succeeded
 * but file is empty/corrupted, or CDN propagation hasn't caught up).
 * Pass --no-verify to skip.
 *
 * Usage: node upload.js [--no-verify] <file-path> [file-path2 ...]
 *
 * Output: JSON array of { name, url, size, md5, verified, verifiedSize,
 *                         verifiedMd5, verifiedAt, error? } for each upload.
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

// Download a URL into a Buffer. Used for verification after upload.
// Returns { status, buffer, contentType, contentLength } or throws on network error.
function downloadBuffer(rawUrl) {
  return new Promise((resolve, reject) => {
    const u = new URL(rawUrl);
    const lib = u.protocol === 'https:' ? https : http;
    const req = lib.request({
      method: 'GET',
      hostname: u.hostname,
      port: u.port || 443,
      path: u.pathname + u.search,
      headers: { 'User-Agent': 'ltpp-upload-verify/1.0' }
    }, (res) => {
      const chunks = [];
      res.on('data', (c) => chunks.push(c));
      res.on('end', () => {
        resolve({
          status: res.statusCode,
          buffer: Buffer.concat(chunks),
          contentType: res.headers['content-type'] || '',
          contentLength: parseInt(res.headers['content-length'] || '0', 10)
        });
      });
    });
    req.on('error', reject);
    req.setTimeout(60000, () => {
      req.destroy(new Error('verification download timed out after 60s'));
    });
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

  return {
    name: fileName,
    url: fullUrl,
    size: fileSize,
    md5: fileHash,
    verified: null,        // filled in by verifyUpload() below
    verifiedSize: null,
    verifiedMd5: null,
    verifiedAt: null,
    contentType: null,
    error: null,
  };
}

// Verify a previously uploaded file by GETting the URL and comparing the
// downloaded body against expected size + md5. Returns a result object with
// `verified: true|false` plus diagnostic fields. Never throws — any error
// is captured in `error` so the upload pipeline can still report a result.
async function verifyUpload(uploadResult) {
  if (!uploadResult || !uploadResult.url) return uploadResult;
  const url = uploadResult.url;
  const expectedSize = uploadResult.size;
  const expectedMd5 = uploadResult.md5;

  // Brief delay: ltpp CDN can take a moment to propagate the merged file.
  await new Promise((r) => setTimeout(r, 800));

  // Try up to 3 times with backoff. First attempt may 404 if propagation is slow.
  let lastErr = null;
  for (let attempt = 1; attempt <= 3; attempt++) {
    try {
      const res = await downloadBuffer(url);
      if (res.status !== 200) {
        lastErr = `HTTP ${res.status}`;
        console.error(`  verify attempt ${attempt}/3: ${lastErr}`);
        await new Promise((r) => setTimeout(r, 1500 * attempt));
        continue;
      }
      const downloadedMd5 = crypto.createHash('md5').update(res.buffer).digest('hex');
      const sizeOk = res.buffer.length === expectedSize;
      const md5Ok = downloadedMd5 === expectedMd5;
      const verified = sizeOk && md5Ok;
      const verifiedAt = new Date().toISOString();
      console.log(`  verify attempt ${attempt}: size ${res.buffer.length}/${expectedSize}, md5 ${verified ? 'OK' : 'MISMATCH'}`);
      return {
        ...uploadResult,
        verified,
        verifiedSize: res.buffer.length,
        verifiedMd5: downloadedMd5,
        verifiedAt,
        contentType: res.contentType,
        error: verified ? null : (sizeOk ? `md5 mismatch: expected ${expectedMd5} got ${downloadedMd5}` : `size mismatch: expected ${expectedSize} got ${res.buffer.length}`),
      };
    } catch (e) {
      lastErr = e.message;
      console.error(`  verify attempt ${attempt}/3 failed: ${e.message}`);
      await new Promise((r) => setTimeout(r, 1500 * attempt));
    }
  }
  return {
    ...uploadResult,
    verified: false,
    verifiedAt: new Date().toISOString(),
    error: `verification failed after 3 attempts: ${lastErr}`,
  };
}

(async () => {
  const args = process.argv.slice(2);
  if (args.length === 0 || args[0] === '--help' || args[0] === '-h') {
    console.log('Usage: node upload.js [--no-verify] [--parallel N | --serial] <file-path> [file-path2 ...]');
    console.log('Uploads files to ltpp.vip/upload via direct REST API.');
    console.log('After each upload, GETs the returned URL to verify size + md5 match the source.');
    console.log('');
    console.log('Options:');
    console.log('  --no-verify            Skip post-upload verification (size + md5 check).');
    console.log('  --parallel N           Upload up to N files concurrently (default: 4, max: 20).');
    console.log('  --serial               Force serial uploads (equivalent to --parallel 1).');
    console.log('');
    console.log('Files are assumed to be independent — this script does not scan for internal');
    console.log('references. The SKILL.md dependency-scan step is responsible for ordering files');
    console.log('into tiers and calling this script per tier. Within a single invocation, files');
    console.log('run in parallel regardless of any logical relationship between them.');
    console.log('');
    console.log('Output: JSON array with { name, url, size, md5, verified, verifiedSize,');
    console.log('         verifiedMd5, verifiedAt, contentType, error } per file.');
    process.exit(args.length === 0 ? 1 : 0);
  }

  // Parse flags
  let verify = true;
  let parallel = 4;
  const fileArgs = [];
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a === '--no-verify') verify = false;
    else if (a === '--verify') verify = true;
    else if (a === '--serial') parallel = 1;
    else if (a === '--parallel') {
      const n = parseInt(args[++i], 10);
      if (isNaN(n) || n < 1) {
        console.error('--parallel requires a positive integer');
        process.exit(1);
      }
      parallel = Math.min(20, n);
    } else if (a.startsWith('--parallel=')) {
      const n = parseInt(a.split('=')[1], 10);
      if (isNaN(n) || n < 1) {
        console.error('--parallel=N requires a positive integer');
        process.exit(1);
      }
      parallel = Math.min(20, n);
    } else {
      fileArgs.push(a);
    }
  }

  if (fileArgs.length === 0) {
    console.error('No file paths given. Use --help for usage.');
    process.exit(1);
  }

  // Process a single file end-to-end (upload + verify) and return a finalized result.
  // Errors are captured in the result object, never thrown, so callers can use
  // Promise.allSettled without try/catch.
  async function processFile(filePath) {
    const uploaded = await uploadOne(filePath);
    if (!uploaded) {
      return { name: path.basename(filePath), url: null, size: 0, md5: null, verified: false, error: 'upload failed (see stderr above)' };
    }
    const final = verify ? await verifyUpload(uploaded) : { ...uploaded, verified: null, error: 'verification skipped (--no-verify)' };
    if (final.verified === false) {
      console.error(`  ✗ VERIFICATION FAILED: ${path.basename(filePath)} — ${final.error}`);
    } else if (final.verified === true) {
      console.log(`  ✓ Verified: ${path.basename(filePath)} (${final.verifiedSize} bytes, md5 OK)`);
    }
    return final;
  }

  // Worker pool: at most `parallel` concurrent uploads, processing files in input order
  // (results are placed at their original index so output order matches argv order).
  const results = new Array(fileArgs.length);
  let nextIdx = 0;
  let inFlight = 0;
  let done = 0;

  console.log(`Uploading ${fileArgs.length} file(s) with concurrency=${parallel}, verify=${verify}...`);

  await new Promise((resolveAll) => {
    function pumpNext() {
      while (inFlight < parallel && nextIdx < fileArgs.length) {
        const myIdx = nextIdx++;
        inFlight++;
        processFile(fileArgs[myIdx])
          .then((r) => { results[myIdx] = r; })
          .catch((e) => {
            // processFile never throws, but be defensive.
            results[myIdx] = { name: path.basename(fileArgs[myIdx]), url: null, size: 0, md5: null, verified: false, error: `unexpected: ${e.message}` };
          })
          .finally(() => {
            inFlight--;
            done++;
            if (done === fileArgs.length) {
              resolveAll();
            } else {
              pumpNext();
            }
          });
      }
    }
    pumpNext();
  });

  console.log('\n=== RESULTS ===');
  console.log(JSON.stringify(results, null, 2));

  // Exit non-zero if any verification failed — lets callers/CI detect issues
  const anyFailed = results.some((r) => r.verified === false);
  process.exit(anyFailed ? 2 : 0);
})();
