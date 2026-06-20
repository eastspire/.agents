const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

/**
 * Upload a file to ltpp.vip/upload via the Hyperlane web component.
 *
 * Usage: node upload.js <file-path> [file-path2 ...]
 *
 * The Hyperlane upload page uses custom Web Components with Shadow DOM,
 * which prevents standard file input manipulation. This script bypasses
 * the UI by calling the page's internal uploadFile() function directly.
 *
 * Output: JSON array of { name, url, size } for each uploaded file.
 */

(async () => {
  const args = process.argv.slice(2);
  if (args.length === 0 || args[0] === '--help') {
    console.log('Usage: node upload.js <file-path> [file-path2 ...]');
    console.log('Uploads files to ltpp.vip/upload and outputs JSON with URLs.');
    process.exit(args.length === 0 ? 1 : 0);
  }

  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });
  const page = await browser.newPage();

  try {
    await page.goto('https://ltpp.vip/upload', { timeout: 30000, waitUntil: 'networkidle2' });

    // Verify the page loaded and uploadFile is available
    const ready = await page.evaluate(() => typeof uploadFile === 'function');
    if (!ready) throw new Error('uploadFile function not found on page');

    const results = [];

    for (const filePath of args) {
      const resolved = path.resolve(filePath);
      if (!fs.existsSync(resolved)) {
        console.error(`File not found: ${resolved}`);
        continue;
      }

      const fileBuffer = fs.readFileSync(resolved);
      const base64 = fileBuffer.toString('base64');
      const fileName = path.basename(resolved);
      const fileSize = fileBuffer.length;

      console.log(`Uploading: ${fileName} (${fileSize} bytes)...`);

      const result = await page.evaluate(async (b64, fname, fsize) => {
        const binary = atob(b64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
        const blob = new Blob([bytes], { type: 'application/octet-stream' });
        const file = new File([blob], fname, { type: 'application/octet-stream' });

        const fileId = 'upload_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        await uploadFile(file, fileId);

        const files = await getAllFiles();
        const uploaded = files.find(f => f.id === fileId);
        return { fileId, url: uploaded?.url || null, name: fname, size: fsize };
      }, base64, fileName, fileSize);

      if (result.url) {
        results.push({
          name: result.name,
          url: `https://ltpp.vip${result.url}`,
          size: result.size
        });
        console.log(`  OK: https://ltpp.vip${result.url}`);
      } else {
        console.error(`  FAILED: ${fileName}`);
      }

      // Small delay between uploads
      await new Promise(r => setTimeout(r, 1000));
    }

    console.log('\n=== RESULTS ===');
    console.log(JSON.stringify(results, null, 2));

  } catch (e) {
    console.error('Error:', e.message);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
