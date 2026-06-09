# GitHub Profile Updater CLI

ဒီ project က GitHub အကောင့်ကို အလိုအလျောက် update လုပ်ဖို့ Python CLI tool တစ်ခုဖြစ်ပါတယ်။

- အလုပ်လုပ်နိုင်စေမယ့် အချက်အလက်များ
  - အကောင့်အမည် (Full name) set/update
  - Avatar (profile photo) upload — Face Studio API သို့မဟုတ် fallback `randomuser.me`
  - Billing information update
  - Two-Factor Authentication (2FA) setup (TOTP) — secret နှင့် recovery codes export
  - Education Benefits submission (Playwright ကို အသုံးပြု၍ automated submission)

**တိကျသော ဖိုင်များ**
- `main.py` — CLI မျဉ်းစည်းချက်နှင့် အစပြု runner
- `client.py` — GitHub အတွက် HTTP client, cookie/session helpers
- `steps.py` — ProfileUpdater (name, avatar, billing, 2FA, education)
- `data.py` — Myanmar-based sample profile generator

## လိုအပ်ချက်များ (Prerequisites)

- Python 3.10+ (3.11 ကို recommend)
- Git, PowerShell (Windows) သို့မဟုတ် bash (Linux/macOS)
- အောက်ပါ Python packages (requirements.txt မှတစ်ဆင့် install လုပ်နိုင်သည်):
  - `requests`
  - `beautifulsoup4`
  - `pyotp`
  - `playwright` (Education step အတွက်)

## စတင်ဖို့ (Quick Start)

PowerShell (Windows) အတွက် အကြံပြုချက် — virtual environment ဖန်တီးပြီး dependency များ install လုပ်ပါ။

```powershell
cd path\to\Github-Education
python -m venv .venv
. .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
# Playwright ကို install ပြီး browser binaries ထည့်ရန်
python -m pip install playwright
python -m playwright install chromium
```

Linux/macOS (bash) အတွက်
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install playwright
python -m playwright install chromium
```

မှတ်ချက်: network/proxy အပြဿနာများရှိပါက `playwright install` မှာ download error တက်နိုင်ပါတယ် — proxy သတ်မှတ်ပြီး ပြန်စမ်းပါ။

Proxy သတ်မှတ်ရန် (PowerShell) — ဥပမာ:
```powershell
$env:HTTP_PROXY='http://user:pass@proxy:port'
$env:HTTPS_PROXY=$env:HTTP_PROXY
python -m playwright install chromium
```

## အသုံးပြုပုံ (Usage)

```powershell
cd path\to\Github-Education
$env:FACESTUDIO_API_KEY='YOUR_FACESTUDIO_API_KEY'
python main.py
```

CLI က chạy ပြီး `Choice (1-2):` ကို တွင်းပါ —
- `1` → Username & Password login (အကယ်၍ 2FA ရှိလျှင် TOTP secret ထည့်ပါ)
- `2` → Cookie: Browser ထဲက Cookie header string (dotcom_user, _gh_sess အပါအဝင်) ကို paste လုပ်ပြီး Enter

နောက်တစ်ချက် — `main.py` က account age (min 3 days) ကို စစ်ဆေးပြီး 2FA, profile, avatar, billing, education steps ကို ပြုလုပ်ပါသည်။

## Environment variables (အသုံးပြုနိုင်သော option များ)

- `FACESTUDIO_API_KEY` — Face Studio API key (avatar ဖန်တီးရန်)
- `GITHUB_EDU_SCHOOL_NAME` — Education step တွင် အသုံးပြုမည့် trường/ကျောင်းအမည်
- `GITHUB_EDU_SCHOOL_EMAIL` — School contact email
- `GITHUB_EDU_LATITUDE`, `GITHUB_EDU_LONGITUDE` — location metadata
- `GITHUB_EDU_PROOF_TYPE` — Education proof type override

## Security Notice

- စိတ်မချရသော secret/data များကို git သို့ commit မလုပ်ပါနဲ့။ ကျွန်တော် ဒီ repo အတွက် sensititve JSON ဖိုင်တစ်ခုကို HEAD မှ ရှင်းထုတ်ပေးပြီး `.gitignore` ထည့်ပေးထားပါတယ် — သင့်အကောင့်အတွက် 2FA secret exposed ဖြစ်ထားခဲ့ရင် ချက်ချင်း rotate လုပ်ပါ (GitHub သို့ ဝင်ပြီး 2FA ပြန်ပြင်ပါ)။
- ရှင်းဖို့ ပြီးနောက် git history ကိုလည်း purge လုပ်ရန် (BFG/git-filter-repo) ကို အသုံးပြုရန် အကြံပြုပါတယ် — example:

```bash
# တကယ် sensitive file ကို history ကနေ ဖယ်ရှားချင်ရင် (သတိပါ)
git filter-repo --path github_account_kokoaung96787aa_20260609_052745.json --invert-paths
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push --force
```

## Troubleshooting

- Playwright browser downloads fail with `ECONNRESET` / `ETIMEDOUT` → network/proxy issue. Proxy သတ်မှတ်ပြီး retry လုပ်ပါ။
- Playwright 설치 မလိုချင်ရင် Education step ကို skip လုပ်နိုင်ပါတယ် — `steps.py` ရဲ့ `steps` list ထဲမှ `("Education Benefits", self.step_education)` ကို comment out လုပ်ပါ။
- အကယ်၍ system-installed Chrome/Chromium ကို အသုံးချချင်ရင် `step_education` ထဲမှာ `p.chromium.launch(...)` ကို `executable_path` နဲ့ပြောင်းလိုက်ပြီး local Chrome path ထည့်နိုင်ပါတယ်။

## Development notes

- အဓိက logic များ: `client.py` (session, form extraction, token extraction), `steps.py` (update flows), `data.py` (profile generator)
- Playwright ကို အသုံးပြုတဲ့ education flow သည် cookie-transfer မှတဆင့် သင်၏ session ကို browser ကိုပို့ပြီး automated form-filling လုပ်သည်။

## Contact / Next steps

လိုအပ်ပါက Education step ကို skip ဖို့ patch ထည့်ပေးနိုင်ပါတယ်၊ ဒါမှမဟုတ် Face Studio fallback ကို ပြောင်းပေးနိုင်ပါတယ် — ညွှန်ကြားချက်ပေးပါ။

---

Generated on 2026-06-09 — created by repository maintainer automation.
