"""
Automated Visual Walkthrough of Shorts Studio
Uses Playwright to navigate through all core workflow modules,
capturing high-resolution screenshots and recording an MP4/WebM video walkthrough.
"""

import asyncio
import os
import shutil
import subprocess
from pathlib import Path
from playwright.async_api import async_playwright

BASE_URL = "http://localhost:8000"
PROJECT_ROOT = Path(r"d:\Antigravity.google\ShortsStudio")
DOCS_DIR = PROJECT_ROOT / "docs"
SCREENSHOTS_DIR = DOCS_DIR / "walkthrough_steps"
VIDEO_TEMP_DIR = DOCS_DIR / "temp_video"
OUTPUT_VIDEO_WEBM = PROJECT_ROOT / "shorts_studio_walkthrough.webm"
OUTPUT_VIDEO_MP4 = PROJECT_ROOT / "shorts_studio_walkthrough.mp4"
PROJECT_ID = "02d35e8191b34e4fab5c2608aef567d6"

CURSOR_SCRIPT = """
(() => {
    const cursor = document.createElement('div');
    cursor.id = 'playwright-cursor';
    cursor.style.cssText = `
        position: fixed;
        top: 0; left: 0;
        width: 18px; height: 18px;
        border-radius: 50%;
        background: rgba(255, 71, 87, 0.75);
        border: 2px solid #ffffff;
        box-shadow: 0 0 12px rgba(255, 71, 87, 0.9);
        pointer-events: none;
        z-index: 9999999;
        transform: translate(-50%, -50%);
        transition: transform 0.08s ease;
    `;
    document.documentElement.appendChild(cursor);

    window.addEventListener('mousemove', e => {
        cursor.style.left = e.clientX + 'px';
        cursor.style.top = e.clientY + 'px';
    });

    window.addEventListener('mousedown', () => {
        cursor.style.transform = 'translate(-50%, -50%) scale(0.6)';
        cursor.style.background = 'rgba(46, 213, 115, 0.9)';
    });

    window.addEventListener('mouseup', () => {
        cursor.style.transform = 'translate(-50%, -50%) scale(1)';
        cursor.style.background = 'rgba(255, 71, 87, 0.75)';
    });
})();
"""

async def smooth_highlight(page, selector, border_color="#e74c3c", duration_ms=1000):
    """Draw a smooth animated highlight box around an element."""
    try:
        await page.evaluate(f"""
            (sel) => {{
                const el = document.querySelector(sel);
                if (el) {{
                    el.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                    const prevBorder = el.style.boxShadow;
                    el.style.transition = 'box-shadow 0.3s ease-in-out';
                    el.style.boxShadow = '0 0 0 3px {border_color}, 0 0 20px {border_color}88';
                    setTimeout(() => {{
                        el.style.boxShadow = prevBorder;
                    }}, {duration_ms});
                }}
            }}
        """, selector)
        await asyncio.sleep(duration_ms / 1000)
    except Exception as e:
        print(f"Highlight note on {selector}: {e}")

async def select_project_safely(page, selector_id, project_id):
    try:
        loc = page.locator(selector_id)
        if await loc.count() > 0:
            await loc.select_option(value=project_id)
            await page.evaluate(f"document.querySelector('{selector_id}').dispatchEvent(new Event('change'))")
            await asyncio.sleep(0.8)
    except Exception as e:
        print(f"Select note on {selector_id}: {e}")

async def run_walkthrough():
    if SCREENSHOTS_DIR.exists():
        shutil.rmtree(str(SCREENSHOTS_DIR), ignore_errors=True)
    if VIDEO_TEMP_DIR.exists():
        shutil.rmtree(str(VIDEO_TEMP_DIR), ignore_errors=True)

    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    VIDEO_TEMP_DIR.mkdir(parents=True, exist_ok=True)

    print("==================================================")
    print("🎬 Starting Shorts Studio Visual Walkthrough")
    print("==================================================")

    async with async_playwright() as p:
        edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        launch_kwargs = {
            "headless": True,
            "args": ["--no-sandbox", "--disable-dev-shm-usage", "--mute-audio"]
        }
        if Path(edge_path).exists():
            launch_kwargs["executable_path"] = edge_path
            print(f"Using Chromium/Edge engine: {edge_path}")

        browser = await p.chromium.launch(**launch_kwargs)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            record_video_dir=str(VIDEO_TEMP_DIR),
            record_video_size={"width": 1440, "height": 900}
        )

        page = await context.new_page()
        await page.add_init_script(CURSOR_SCRIPT)

        # ── Step 1: Dashboard ────────────────────────────────────────────────
        print("\n[1/10] Navigating to Dashboard...")
        await page.goto(f"{BASE_URL}/#dashboard", wait_until="networkidle")
        await asyncio.sleep(2.0)
        await smooth_highlight(page, '#sidebar-nav', '#7d5fff')
        await smooth_highlight(page, '.stat-card', '#00d2d3')
        await page.screenshot(path=str(SCREENSHOTS_DIR / "01_dashboard.png"))

        # ── Step 2: Script Editor ────────────────────────────────────────────
        print("[2/10] Navigating to Script Editor...")
        await page.hover('a[data-page="script-editor"]')
        await asyncio.sleep(0.4)
        await page.click('a[data-page="script-editor"]')
        await asyncio.sleep(1.5)
        await select_project_safely(page, '#se-project-select', PROJECT_ID)
        await smooth_highlight(page, '#se-editor', '#ff9f43')
        await page.screenshot(path=str(SCREENSHOTS_DIR / "02_script_editor.png"))

        # ── Step 3: Storyboard ───────────────────────────────────────────────
        print("[3/10] Navigating to Storyboard & Scene Manager...")
        await page.hover('a[data-page="storyboard"]')
        await asyncio.sleep(0.4)
        await page.click('a[data-page="storyboard"]')
        await asyncio.sleep(1.5)
        await select_project_safely(page, '#sb-project-select', PROJECT_ID)
        await smooth_highlight(page, '.scene-card[data-idx="0"]', '#10ac84')
        await page.screenshot(path=str(SCREENSHOTS_DIR / "03_storyboard.png"))

        # ── Step 4: Storyboard Scene Edit Modal ──────────────────────────────
        print("[4/10] Inspecting Storyboard Scene 1 with Assigned Video...")
        edit_btn = page.locator('.scene-card[data-idx="0"] .sb-edit')
        if await edit_btn.count() > 0:
            await edit_btn.first.click()
            await asyncio.sleep(1.2)
            await smooth_highlight(page, '#sm-asset', '#ee5253')
            await page.screenshot(path=str(SCREENSHOTS_DIR / "04_storyboard_modal.png"))
            cancel_btn = page.locator('.modal-footer button:has-text("Cancel")')
            if await cancel_btn.count() > 0:
                await cancel_btn.first.click()
                await asyncio.sleep(0.8)

        # ── Step 5: Voiceover Studio ─────────────────────────────────────────
        print("[5/10] Navigating to Voiceover Studio...")
        await page.hover('a[data-page="voiceover"]')
        await asyncio.sleep(0.4)
        await page.click('a[data-page="voiceover"]')
        await asyncio.sleep(1.5)
        await select_project_safely(page, '#vo-project-select', PROJECT_ID)
        await smooth_highlight(page, '#vo-scenes-list', '#0abde3')
        await page.screenshot(path=str(SCREENSHOTS_DIR / "05_voiceover_studio.png"))

        # ── Step 6: Assets Library ───────────────────────────────────────────
        print("[6/10] Navigating to Visual Assets Library...")
        await page.hover('a[data-page="assets"]')
        await asyncio.sleep(0.4)
        await page.click('a[data-page="assets"]')
        await asyncio.sleep(1.5)
        await select_project_safely(page, '#asset-project-select', PROJECT_ID)
        asset_cards = page.locator('.asset-card')
        if await asset_cards.count() > 0:
            await asset_cards.first.click()
            await asyncio.sleep(1.0)
            await smooth_highlight(page, '#asset-detail', '#5f27cd')
        await page.screenshot(path=str(SCREENSHOTS_DIR / "06_assets_library.png"))

        # ── Step 7: Video Editor & Timeline ──────────────────────────────────
        print("[7/10] Navigating to Video Editor & Multi-track Timeline...")
        await page.hover('a[data-page="video-editor"]')
        await asyncio.sleep(0.4)
        await page.click('a[data-page="video-editor"]')
        await asyncio.sleep(2.0)
        await select_project_safely(page, '#editor-project-select', PROJECT_ID)
        # Click Scene 1 on the visual track
        scene_block = page.locator('.timeline-block.scene-block[data-idx="0"]')
        if await scene_block.count() > 0:
            await scene_block.first.click()
            await asyncio.sleep(1.0)
        await smooth_highlight(page, '#player-container', '#ff6b6b')
        await smooth_highlight(page, '#scene-inspector-body', '#48dbfb')
        await page.screenshot(path=str(SCREENSHOTS_DIR / "07_video_editor.png"))

        # ── Step 8: Captions & Audio ─────────────────────────────────────────
        print("[8/10] Navigating to Captions & Subtitles...")
        await page.hover('a[data-page="captions"]')
        await asyncio.sleep(0.4)
        await page.click('a[data-page="captions"]')
        await asyncio.sleep(1.5)
        await select_project_safely(page, '#cap-project-select', PROJECT_ID)
        await smooth_highlight(page, '#cap-cues-list', '#f368e0')
        await page.screenshot(path=str(SCREENSHOTS_DIR / "08_captions.png"))

        # ── Step 9: Render Queue ─────────────────────────────────────────────
        print("[9/10] Navigating to Render Queue...")
        await page.hover('a[data-page="render-queue"]')
        await asyncio.sleep(0.4)
        await page.click('a[data-page="render-queue"]')
        await asyncio.sleep(1.5)
        await smooth_highlight(page, '#rq-jobs-list', '#1dd1a1')
        await page.screenshot(path=str(SCREENSHOTS_DIR / "09_render_queue.png"))

        # ── Step 10: Export Center & Quality ─────────────────────────────────
        print("[10/10] Navigating to Export Center...")
        await page.hover('a[data-page="quality"]')
        await asyncio.sleep(0.4)
        await page.click('a[data-page="quality"]')
        await asyncio.sleep(1.2)
        await select_project_safely(page, '#qc-project-select', PROJECT_ID)
        await page.screenshot(path=str(SCREENSHOTS_DIR / "10_quality_control.png"))

        await page.hover('a[data-page="export"]')
        await asyncio.sleep(0.4)
        await page.click('a[data-page="export"]')
        await asyncio.sleep(1.5)
        await select_project_safely(page, '#export-project-select', PROJECT_ID)
        await smooth_highlight(page, '#export-actions', '#ff9f43')
        await page.screenshot(path=str(SCREENSHOTS_DIR / "11_export_center.png"))

        print("\nFinishing walkthrough session...")
        await asyncio.sleep(2.0)
        await context.close()
        await browser.close()

    # Move and convert video output
    video_files = list(VIDEO_TEMP_DIR.glob("*.webm"))
    if video_files:
        src = video_files[0]
        shutil.copy(str(src), str(OUTPUT_VIDEO_WEBM))
        print(f"✓ Walkthrough WebM saved: {OUTPUT_VIDEO_WEBM} ({OUTPUT_VIDEO_WEBM.stat().st_size} bytes)")

        # Convert to MP4 using local portable ffmpeg
        ffmpeg_bin = PROJECT_ROOT / "bin" / "ffmpeg.exe"
        if ffmpeg_bin.exists():
            print("Encoding high-compatibility MP4 version with FFmpeg...")
            cmd = [
                str(ffmpeg_bin), "-y", "-i", str(OUTPUT_VIDEO_WEBM),
                "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                str(OUTPUT_VIDEO_MP4)
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if OUTPUT_VIDEO_MP4.exists():
                print(f"✓ Walkthrough MP4 saved: {OUTPUT_VIDEO_MP4} ({OUTPUT_VIDEO_MP4.stat().st_size} bytes)")
            else:
                print(f"FFmpeg conversion output: {res.stderr.decode('utf-8', errors='ignore')[-300:]}")

    # Clean up temp video folder
    shutil.rmtree(str(VIDEO_TEMP_DIR), ignore_errors=True)

    print("\n🎉 Walkthrough successfully completed!")
    print(f"Screenshots saved to: {SCREENSHOTS_DIR}")
    for img in sorted(SCREENSHOTS_DIR.glob("*.png")):
        print(f"  • {img.name} ({img.stat().st_size} bytes)")

if __name__ == "__main__":
    asyncio.run(run_walkthrough())
