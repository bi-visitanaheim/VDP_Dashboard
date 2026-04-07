"""
Headless CoStar/STR export downloader.
Downloads Daily and Monthly STR data exports → data/str/str_daily.xlsx + str_monthly.xlsx
"""

import asyncio
import os
import shutil
from pathlib import Path
from playwright.async_api import async_playwright, Page, TimeoutError as PWTimeout

USERNAME  = os.getenv("COSTAR_USER", "")
PASSWORD  = os.getenv("COSTAR_PASS", "")
LOGIN_URL = "https://product.costar.com"
DL_DIR    = Path("downloads")
STR_DIR   = Path("data/str")


def log(msg: str) -> None:
    import datetime
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


async def screenshot(page: Page, name: str) -> None:
    p = Path("logs") / f"{name}.png"
    p.parent.mkdir(exist_ok=True)
    await page.screenshot(path=str(p), full_page=True)
    log(f"  Screenshot → {p}")


async def login(page: Page) -> bool:
    log("[1/5] Navigating to CoStar login...")
    await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30_000)
    await page.wait_for_timeout(2000)
    await screenshot(page, "01_landing")

    # CoStar login can be multi-step: email → continue → password
    # Try filling email
    try:
        email_sel = "input[type='email'], input[name='username'], input[name='email'], input[placeholder*='email' i], input[placeholder*='user' i]"
        await page.wait_for_selector(email_sel, timeout=10_000)
        await page.fill(email_sel, USERNAME)
        log(f"  Filled email: {USERNAME}")

        # Click continue/next if present before password field appears
        try:
            next_btn = page.locator("button[type='submit'], button:has-text('Continue'), button:has-text('Next')").first
            await next_btn.wait_for(state="visible", timeout=5_000)
            await next_btn.click()
            await page.wait_for_timeout(2000)
            log("  Clicked Continue/Next")
        except PWTimeout:
            pass

        # Now fill password
        pw_sel = "input[type='password']"
        await page.wait_for_selector(pw_sel, timeout=10_000)
        await page.fill(pw_sel, PASSWORD)
        log("  Filled password")

        await screenshot(page, "02_credentials_filled")

        # Submit
        submit = page.locator("button[type='submit']").last
        await submit.click()
        log("  Clicked login submit")

        # Wait for post-login indicator (broad set of possible selectors)
        post_login = "[role='tab'], nav, .dashboard, [class*='dashboard'], [class*='nav']"
        await page.wait_for_selector(post_login, timeout=30_000)
        await page.wait_for_timeout(2000)
        await screenshot(page, "03_post_login")
        log("  ✓ Logged in")
        return True

    except Exception as exc:
        await screenshot(page, "02_login_error")
        log(f"  ✗ Login failed: {exc}")
        return False


async def find_str_section(page: Page) -> bool:
    """Navigate to the STR/Analytics data section."""
    log("[2/5] Looking for STR / Analytics section...")
    await screenshot(page, "04_after_login")

    # Try clicking top-level tabs that might contain STR data
    for label in ["Properties", "Analytics", "STR", "Reports", "Data"]:
        try:
            btn = page.locator(f"[role='tab']:has-text('{label}'), a:has-text('{label}'), button:has-text('{label}')").first
            if await btn.count() > 0:
                await btn.click()
                await page.wait_for_timeout(1500)
                log(f"  Clicked '{label}' tab")
                break
        except Exception:
            continue

    await screenshot(page, "05_section_navigated")

    # Try to find and click "VDP Select" saved search
    try:
        vdp = page.locator("a:has-text('VDP Select'), [class*='survey']:has-text('VDP Select'), span:has-text('VDP Select')").first
        await vdp.wait_for(state="visible", timeout=8_000)
        await vdp.click()
        await page.wait_for_timeout(2000)
        log("  ✓ VDP Select loaded")
        await screenshot(page, "06_vdp_select")
    except PWTimeout:
        log("  – VDP Select not found by direct click, continuing...")

    # Dismiss any popup
    for popup_text in ["Okay, got it", "Got it", "Dismiss", "OK"]:
        try:
            btn = page.locator(f"button:has-text('{popup_text}')").first
            await btn.wait_for(state="visible", timeout=3_000)
            await btn.click()
            log(f"  Dismissed popup: '{popup_text}'")
        except PWTimeout:
            pass

    # Click Analytics sub-tab
    try:
        await page.locator("[role='tab']:has-text('Analytics')").first.click()
        await page.wait_for_timeout(1500)
        log("  ✓ Analytics tab clicked")
    except Exception:
        pass

    # Click Data sub-tab
    try:
        await page.locator("[role='tab']:has-text('Data')").first.click()
        await page.wait_for_timeout(1500)
        log("  ✓ Data tab clicked")
    except Exception:
        pass

    await screenshot(page, "07_data_tab")
    return True


async def export_period(page: Page, period: str, dest: Path) -> bool:
    """Set period combobox, click Export → Data Export, capture download."""
    log(f"[{period}] Setting period combobox...")
    try:
        combo = page.locator("input#autocomplete[role='combobox'], input[role='combobox']").first
        await combo.wait_for(state="visible", timeout=10_000)
        await combo.triple_click()
        await combo.fill(period)
        await page.locator(f"[role='option']:has-text('{period}')").first.click()
        await page.wait_for_timeout(1000)
        log(f"  ✓ Period set to '{period}'")
    except Exception as exc:
        log(f"  ✗ Could not set period: {exc}")
        await screenshot(page, f"err_{period.lower()}_combobox")
        return False

    log(f"[{period}] Clicking Export...")
    try:
        export_btn = page.locator("span.placeholder-normal, button, span").filter(has_text="Export").first
        await export_btn.wait_for(state="visible", timeout=10_000)
        await export_btn.click()
        await page.wait_for_timeout(800)
    except Exception as exc:
        log(f"  ✗ Export button error: {exc}")
        await screenshot(page, f"err_{period.lower()}_export_btn")
        return False

    log(f"[{period}] Clicking 'Data Export' menu item...")
    try:
        data_export = page.locator("[role='menuitem']:has-text('Data Export'), div:has-text('Data Export')").first
        await data_export.wait_for(state="visible", timeout=10_000)

        async with page.expect_download(timeout=90_000) as dl_info:
            await data_export.click()

        download = await dl_info.value
        suggested = download.suggested_filename or f"str_{period.lower()}.xlsx"
        dest.parent.mkdir(parents=True, exist_ok=True)
        await download.save_as(str(dest))
        log(f"  ✓ {period} export saved → {dest}  (original: {suggested})")
        return True

    except Exception as exc:
        log(f"  ✗ Download failed for {period}: {exc}")
        await screenshot(page, f"err_{period.lower()}_download")
        return False


async def main() -> None:
    if not USERNAME or not PASSWORD:
        print("ERROR: COSTAR_USER and COSTAR_PASS must be set.")
        return

    DL_DIR.mkdir(exist_ok=True)
    STR_DIR.mkdir(parents=True, exist_ok=True)

    log("=" * 52)
    log("  CoStar/STR Headless Download")
    log("=" * 52)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
            downloads_path=str(DL_DIR),
        )
        context = await browser.new_context(
            accept_downloads=True,
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        )
        page = await context.new_page()

        try:
            ok = await login(page)
            if not ok:
                log("Aborting — login failed. Check logs/ screenshots.")
                return

            await find_str_section(page)

            daily_dl   = DL_DIR / "str_daily_new.xlsx"
            monthly_dl = DL_DIR / "str_monthly_new.xlsx"

            log("\n── Daily Export ──────────────────────────────────")
            daily_ok = await export_period(page, "Daily",   daily_dl)

            log("\n── Monthly Export ────────────────────────────────")
            monthly_ok = await export_period(page, "Monthly", monthly_dl)

            # Move to canonical data/str/ location
            if daily_ok and daily_dl.exists():
                shutil.copy2(daily_dl, STR_DIR / "str_daily.xlsx")
                log(f"  ✓ Copied daily   → {STR_DIR}/str_daily.xlsx")

            if monthly_ok and monthly_dl.exists():
                shutil.copy2(monthly_dl, STR_DIR / "str_monthly.xlsx")
                log(f"  ✓ Copied monthly → {STR_DIR}/str_monthly.xlsx")

            log("\n" + "=" * 52)
            if daily_ok and monthly_ok:
                log("  ✓ Both exports complete. Run pipeline next.")
            else:
                log("  ⚠ One or more exports failed. Check logs/ screenshots.")
            log("=" * 52)

        except Exception as exc:
            log(f"[ERROR] {exc}")
            await screenshot(page, "fatal_error")
            raise
        finally:
            await context.close()
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
