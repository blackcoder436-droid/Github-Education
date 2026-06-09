"""Wrapper that runs target script as a subprocess."""
import subprocess, sys
result = subprocess.run(
    [sys.executable, "test_edu.py"],
    cwd=r"d:\Project\2026\github",
    capture_output=True, text=True, timeout=300
)
with open(r"d:\Project\2026\github\step2_result.txt", "w", encoding="utf-8") as f:
    f.write("=== STDOUT ===\n")
    f.write(result.stdout)
    f.write("\n=== STDERR ===\n")
    f.write(result.stderr)
    f.write(f"\n=== RETURN CODE: {result.returncode} ===\n")
print("Done writing step2_result.txt")
