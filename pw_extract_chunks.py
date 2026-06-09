"""Extract webcam chunk code from webpack runtime.
The runtime maps chunk IDs to hashes. We need chunks: 13726, 59299, 83465, 90225, 98131, 7542."""
import os, sys, json
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

    page.goto("https://github.com/settings/education/benefits", timeout=120000, wait_until="load")
    page.wait_for_timeout(5000)

    # Get the runtime JS URL
    runtime_url = page.evaluate('''() => {
        const scripts = Array.from(document.querySelectorAll('script[src]')).map(s => s.src);
        return scripts.find(s => s.includes('wp-runtime'));
    }''')
    print(f"Runtime: {runtime_url}")

    # Download runtime and extract full chunk mapping
    print("\n=== Extracting chunk hash mapping from runtime ===")
    chunk_urls = page.evaluate('''async (runtimeUrl) => {
        const r = await fetch(runtimeUrl);
        const text = await r.text();

        // The webpack runtime has a function like:
        // e.u = e => "assets/" + ({13726:"hash1", 59299:"hash2", ...}[e] || e) + ".js"
        // Or: e.u = function(e) { return "assets/" + ({...})[e] + "-" + {hash_obj}[e] + ".js" }
        // There may be multiple approaches. Let's extract all chunkId:hash pairs.

        // Strategy: Find all number:"hexhash" patterns in objects
        const allMaps = [];
        // Look for patterns like: {13726:"abc123def456",...}
        const mapRegex = /\{(\d+:"[a-f0-9]+"(?:,\d+:"[a-f0-9]+")*)\}/g;
        let m;
        while ((m = mapRegex.exec(text)) !== null) {
            const obj = m[1];
            const entries = obj.match(/(\d+):"([a-f0-9]+)"/g);
            if (entries && entries.length > 5) {
                const parsed = {};
                for (const entry of entries) {
                    const [, id, hash] = entry.match(/(\d+):"([a-f0-9]+)"/);
                    parsed[id] = hash;
                }
                allMaps.push({size: entries.length, sample: Object.entries(parsed).slice(0, 3)});

                // Check if this map has our target chunks
                const targets = ['13726', '59299', '83465', '90225', '98131', '7542'];
                const found = targets.filter(t => parsed[t]);
                if (found.length > 0) {
                    return {
                        type: 'direct_map',
                        found: found.map(id => ({id, hash: parsed[id]})),
                        totalEntries: entries.length,
                    };
                }
            }
        }

        // Alternative: look for two separate objects that together form the URL
        // Some webpack configs use: chunkId + "-" + chunkHash  where these are in separate objects
        // e.u = e => ({...}[e] || e) + "-" + {...}[e] + ".js"
        
        // Try to find the actual URL constructor function
        const urlFuncMatch = text.match(/e\.u\s*=\s*[^;]+/);
        const urlFunc = urlFuncMatch ? urlFuncMatch[0].substring(0, 500) : null;
        
        // Also try to find chunk IDs in different patterns
        // Pattern: e.p + "assets/" + e.u(chunkId)
        // May have: a.p="https://github.githubassets.com/assets/"
        
        // Try to grab ALL large objects (>20 entries)
        const largeObjects = [];
        const objRegex2 = /\{[^{}]*\b(\d{4,5})\s*:/g;
        let m2;
        const positions = new Set();
        while ((m2 = objRegex2.exec(text)) !== null) {
            const start = text.lastIndexOf('{', m2.index);
            if (!positions.has(start)) {
                positions.add(start);
                // Try to extract the full object
                let depth = 0;
                let end = start;
                for (let i = start; i < Math.min(text.length, start + 20000); i++) {
                    if (text[i] === '{') depth++;
                    else if (text[i] === '}') { depth--; if (depth === 0) { end = i + 1; break; } }
                }
                const objStr = text.substring(start, end);
                // Check for our target chunk IDs
                if (objStr.includes('13726') || objStr.includes('59299') || objStr.includes('83465')) {
                    const targets = ['13726', '59299', '83465', '90225', '98131', '7542'];
                    const foundInObj = targets.filter(t => {
                        const re = new RegExp('\\\\b' + t + '\\\\b');
                        return re.test(objStr) || objStr.includes(t + ':') || objStr.includes(t + '"');
                    });
                    if (foundInObj.length > 0) {
                        largeObjects.push({
                            pos: start,
                            len: end - start,
                            foundIds: foundInObj,
                            snippet: objStr.substring(0, 300),
                        });
                    }
                }
            }
        }

        return {
            type: 'search',
            allMaps: allMaps.map(m => ({size: m.size, sample: m.sample})),
            urlFunc,
            largeObjects: largeObjects.slice(0, 5),
            runtimeLen: text.length,
        };
    }''', runtime_url)
    print(json.dumps(chunk_urls, indent=2))

    # Also try: directly guess the chunk URLs by looking at the URL pattern
    # Known pattern: https://github.githubassets.com/assets/CHUNKID-HASH.js
    # We can try to load the chunks by trying well-known patterns
    
    # Another approach: trigger the webcam-upload lazy-load by inserting the element
    print("\n=== Attempting to trigger webcam lazy-load ===")
    lazy_result = page.evaluate('''async () => {
        // Insert a fake webcam-upload react-partial to trigger chunk loading
        const partial = document.createElement('react-partial');
        partial.setAttribute('partial-name', 'webcam-upload');
        partial.innerHTML = '<script type="application/json" data-target="react-partial.embeddedData">{"props":{"allowFileUpload":false,"formFieldId":"photo_proof"}}</script><div data-target="react-partial.reactRoot"></div>';
        document.body.appendChild(partial);
        
        // Wait for chunks to load
        await new Promise(r => setTimeout(r, 10000));
        
        // Check if any new scripts were loaded
        const newScripts = Array.from(document.querySelectorAll('script[src]'))
            .map(s => s.src.split('/').pop())
            .filter(s => s.match(/^(13726|59299|83465|90225|98131|7542)/));
        
        // Check if the react-partial rendered
        const root = partial.querySelector('[data-target="react-partial.reactRoot"]');
        const children = root ? root.childElementCount : 0;
        
        return {
            newScripts,
            children,
            rootHtml: root ? root.innerHTML.substring(0, 500) : null,
        };
    }''')
    print(f"Lazy load result: {json.dumps(lazy_result, indent=2)}")

    # If lazy load worked, look at what was loaded
    if lazy_result.get('newScripts'):
        base_url = runtime_url.rsplit('/', 1)[0] + '/'
        for script_name in lazy_result['newScripts']:
            url = base_url + script_name
            print(f"\n  Downloading {script_name}...")
            code = page.evaluate('''async (url) => {
                const r = await fetch(url);
                const text = await r.text();
                const terms = ['photo_proof', 'photoProof', 'formFieldId', 'formField',
                               'canvas', 'toDataURL', 'toBlob', 'capture', 'getUserMedia',
                               'hidden', 'value', 'querySelector', 'getElementById'];
                const snippets = [];
                for (const term of terms) {
                    let idx = text.indexOf(term);
                    while (idx !== -1 && snippets.length < 30) {
                        snippets.push({term, ctx: text.substring(Math.max(0, idx-100), idx+150)});
                        idx = text.indexOf(term, idx + 1);
                    }
                }
                return {size: text.length, snippets};
            }''', url)
            print(f"    Size: {code['size']}, Snippets: {len(code['snippets'])}")
            for s in code['snippets']:
                print(f"    [{s['term']}]: {s['ctx'][:200]}")

    # Also check all currently loaded script tags for new ones
    all_loaded = page.evaluate('''() => {
        return Array.from(document.querySelectorAll('script[src]'))
            .map(s => s.src.split('/').pop())
            .filter(s => !s.includes('wp-runtime') && !s.includes('environment'));
    }''')
    print(f"\n=== All loaded scripts ({len(all_loaded)}) ===")
    for s in all_loaded:
        print(f"  {s}")

    browser.close()
print("\nDone!")
