"""Optional browser-use entry point. The deterministic Playwright adapter is the baseline."""
import sys
print("browser-use is optional; run: npx tsx browser/hkex_download_playwright.ts", file=sys.stderr)

