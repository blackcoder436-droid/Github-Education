"""Wrapper to run script and capture output."""
import subprocess, sys
result = subprocess.run(
    [sys.executable, "pw_v4.py"],
    capture_output=True, text=True, encoding="utf-8", errors="replace",
    cwd=r"D:\Project\2026\github"
)
with open(r"D:\Project\2026\github\step2_result.txt", "w", encoding="utf-8") as f:
    f.write("=== STDOUT ===\n")
    f.write(result.stdout)
    f.write("\n=== STDERR ===\n")
    f.write(result.stderr)
    f.write(f"\n=== RETURN CODE: {result.returncode} ===\n")
print("Done writing step2_result.txt")
