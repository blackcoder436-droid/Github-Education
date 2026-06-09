"""Find webcam chunk URLs from webpack runtime, download them, search for photo_proof logic."""
import os, sys, json, re
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import pyotp
load_dotenv()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    page = context.new_page()

    # Login
    page.goto("https://github.com/login", timeout=60000, wait_until="load")
    page.wait_for_timeout(3000)
    if "login" in page.url:
        f = page.query_selector('#login_field')
        if f:
            f.fill(os.environ['GITHUB_USERNAME'])
            page.fill('#password', os.environ['GITHUB_PASSWORD'])
            page.wait_for_timeout(500)
            page.click('input[name="commit"]')
            page.wait_for_timeout(5000)
            if "two-factor" in page.url or "sessions" in page.url:
                otp = pyotp.TOTP("SFDHLAA7MDH2S7TN").now()
                for sel in ['#app_totp', 'input[name="otp"]']:
                    el = page.query_selector(sel)
                    if el: el.fill(otp); break
                page.wait_for_timeout(500)
                try: page.click('button[type="submit"]', timeout=5000)
                except: pass
                page.wait_for_load_state("load", timeout=30000)
                page.wait_for_timeout(3000)
    print(f"Logged in: {'login' not in page.url}")

    # Go to education page to get all scripts
    page.goto("https://github.com/settings/education/benefits", timeout=120000, wait_until="load")
    page.wait_for_timeout(5000)

    # 1. Get all script URLs to build the base URL pattern
    all_scripts = page.evaluate('''() => Array.from(document.querySelectorAll('script[src]')).map(s => s.src)''')
    
    # Find the assets base URL
    base_url = None
    for s in all_scripts:
        if 'githubassets.com/assets/' in s:
            base_url = s.rsplit('/', 1)[0] + '/'
            break
    print(f"Assets base: {base_url}")

    # 2. Extract webpack chunk mapping from the runtime
    print("\n=== Extracting webpack chunk map ===")
    chunk_map = page.evaluate('''() => {
        // The webpack runtime stores chunk-to-filename mappings
        // Try to find it via __webpack_require__ or similar
        try {
            // Method 1: Check for globalThis or window.__webpack_chunks__
            if (typeof self !== 'undefined' && self.webpackChunk_assets) {
                return {method: 'webpackChunk', found: true};
            }
        } catch(e) {}
        
        // Method 2: Look at all script tags for chunk ID patterns
        const scripts = Array.from(document.querySelectorAll('script[src]')).map(s => s.src);
        const chunkIds = {};
        for (const s of scripts) {
            const match = s.match(/\/(\d+)-([a-f0-9]+)\.js$/);
            if (match) {
                chunkIds[match[1]] = match[0].split('/').pop();
            }
        }
        return {method: 'regex', chunkIds};
    }''')
    print(f"Chunk map: {json.dumps(chunk_map, indent=2)}")

    # 3. Get the wp-runtime source and extract the full chunk mapping
    print("\n=== Extracting chunk mapping from runtime ===")
    runtime_url = [s for s in all_scripts if 'wp-runtime' in s]
    if runtime_url:
        print(f"Runtime: {runtime_url[0].split('/')[-1]}")
        chunk_data = page.evaluate('''async (url) => {
            const r = await fetch(url);
            const text = await r.text();
            
            // Find the chunk mapping object - usually looks like {13726:"hash",59299:"hash",...}
            // It's in a pattern like: e.u=e=>(({CHUNK_ID:"HASH",...})[e]||e)+".js"
            // Or: {13726:"abc123",59299:"def456",...}
            
            const results = [];
            // Look for chunk ID patterns for our target chunks
            const targetChunks = ['13726', '59299', '83465', '90225', '98131', '7542'];
            
            for (const chunkId of targetChunks) {
                const patterns = [
                    new RegExp(chunkId + ':"([a-f0-9]+)"'),
                    new RegExp(chunkId + ':"([^"]+)"'),
                ];
                for (const re of patterns) {
                    const m = text.match(re);
                    if (m) {
                        results.push({chunkId, hash: m[1], filename: chunkId + '-' + m[1] + '.js'});
                        break;
                    }
                }
            }
            
            // Also find the general pattern
            const bigMapMatch = text.match(/\{(\d+:"[a-f0-9]+"(?:,\d+:"[a-f0-9]+")*)\}/g);
            let mapCount = 0;
            if (bigMapMatch) {
                for (const m of bigMapMatch) {
                    const entries = m.match(/\d+:"[a-f0-9]+"/g);
                    if (entries && entries.length > 20) {
                        mapCount = entries.length;
                    }
                }
            }
            
            return {results, runtimeSize: text.length, mapCount};
        }''', runtime_url[0])
        print(f"Found chunks: {json.dumps(chunk_data, indent=2)}")
    
    # 4. Now download the target chunk files and search for webcam code
    print("\n=== Downloading and inspecting webcam chunks ===")
    
    # Build URLs from what we found
    chunks_to_check = []
    if chunk_data and chunk_data.get('results'):
        for r in chunk_data['results']:
            chunks_to_check.append(base_url + r['filename'])
    
    # Also try to find them via brute-force from all loaded scripts
    # Check if any of the already-loaded scripts contain these chunk IDs
    for s in all_scripts:
        name = s.split('/')[-1]
        for cid in ['13726', '59299', '83465', '90225', '98131', '7542']:
            if name.startswith(cid + '-'):
                chunks_to_check.append(s)
    
    print(f"Chunks to download: {len(chunks_to_check)}")
    
    # Save all webcam-related JS for analysis
    all_webcam_code = ""
    
    for chunk_url in chunks_to_check:
        chunk_name = chunk_url.split('/')[-1]
        print(f"\n  Downloading {chunk_name}...")
        result = page.evaluate('''async (url) => {
            try {
                const r = await fetch(url);
                if (!r.ok) return {error: r.status};
                const text = await r.text();
                
                // Search for key patterns
                const searches = [
                    'photo_proof', 'photoProof', 'formFieldId', 'webcam',
                    'canvas', 'toDataURL', 'toBlob', 'captureImage', 'takePhoto',
                    'getImageData', 'drawImage', 'getUserMedia', 'MediaStream',
                    'upload', 'presign', 'signed_url', 'put_url',
                    'allowFileUpload', 'fileUpload', 'blob', 'Blob',
                    'createElement', 'hidden', 'FormData', 'append',
                    'data:image', 'image/jpeg', 'image/png',
                    'onCapture', 'onPhoto', 'setPhoto', 'photoData',
                    'inputElement', 'hiddenInput', 'formField',
                ];
                
                const snippets = [];
                for (const term of searches) {
                    let idx = text.indexOf(term);
                    let count = 0;
                    while (idx !== -1 && count < 3) {
                        snippets.push({
                            term,
                            context: text.substring(Math.max(0, idx - 100), Math.min(text.length, idx + 150))
                        });
                        idx = text.indexOf(term, idx + 1);
                        count++;
                    }
                }
                
                return {size: text.length, snippetCount: snippets.length, snippets: snippets.slice(0, 30)};
            } catch(e) {
                return {error: e.message};
            }
        }''', chunk_url)
        
        if result.get('error'):
            print(f"    Error: {result['error']}")
        else:
            print(f"    Size: {result['size']}, Snippets: {result['snippetCount']}")
            for s in result.get('snippets', []):
                print(f"    [{s['term']}]: ...{s['context'][:200]}...")
            
            # If this chunk has webcam code, save the full text
            if result['snippetCount'] > 5:
                full_text = page.evaluate('''async (url) => {
                    const r = await fetch(url);
                    return await r.text();
                }''', chunk_url)
                all_webcam_code += f"\n\n// === {chunk_name} ===\n" + full_text
    
    # 5. Save all webcam code for offline analysis
    if all_webcam_code:
        with open("webcam_chunks.js", "w", encoding="utf-8") as f:
            f.write(all_webcam_code)
        print(f"\nSaved webcam code to webcam_chunks.js ({len(all_webcam_code)} chars)")
    
    # 6. Also try a different approach: look at React SSR data for webcam-upload
    print("\n=== React partial data for webcam-upload ===")
    partial_data = page.evaluate('''() => {
        const partial = document.querySelector('react-partial[partial-name="webcam-upload"]');
        if (!partial) return {found: false};
        
        const data = partial.querySelector('script[data-target="react-partial.embeddedData"]');
        const ssrData = data ? data.textContent : null;
        
        return {
            found: true,
            data: ssrData ? ssrData.substring(0, 2000) : null,
            attrs: Object.fromEntries(Array.from(partial.attributes).map(a => [a.name, a.value])),
        };
    }''')
    print(f"Webcam partial data: {json.dumps(partial_data, indent=2)}")
    
    browser.close()

print("\nDone!")
