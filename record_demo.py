import asyncio
import glob
import os
import shutil
import time
import imageio_ffmpeg
from playwright.async_api import async_playwright

APP_URL = "https://apartment-agent-frontend-122679751069.us-east1.run.app"
ARTIFACTS_DIR = "/config/.gemini/antigravity/brain/a4aec273-cff3-4425-aad9-c6d834f0e802"
FINAL_VIDEO_NAME = "apartment_agent_demo.mp4"

async def record_demo():
    raw_dir = os.path.abspath("demo_raw")
    if os.path.exists(raw_dir):
        shutil.rmtree(raw_dir)
    os.makedirs(raw_dir, exist_ok=True)

    print(f"Starting Playwright demo recording for {APP_URL}...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=raw_dir,
            record_video_size={"width": 1280, "height": 720}
        )
        page = await context.new_page()

        # Step 1: Open app and show Hero Welcome Card
        print("Opening app...")
        await page.goto(APP_URL, wait_until="networkidle")
        await page.wait_for_selector("#suggestions", timeout=10000)
        await asyncio.sleep(2)

        # Step 2: Toggle Dark Mode
        print("Toggling Dark Mode...")
        theme_btn = await page.query_selector("#theme-icon")
        if theme_btn:
            await theme_btn.click()
            await asyncio.sleep(2)

        # Step 3: Click prompt chip - Search 2BR under $3500
        print("Clicking prompt chip: Search 2BR under $3500...")
        chips = await page.query_selector_all(".chip")
        if chips:
            await chips[0].click()
            # Wait for response bubble to settle (typing indicator gone)
            await page.wait_for_selector(".msg.agent", timeout=30000)
            await page.wait_for_selector(".typing-indicator", state="detached", timeout=30000)
            await asyncio.sleep(3)

        # Step 4: Type query - Schedule a viewing
        print("Typing schedule viewing query...")
        input_el = await page.query_selector("#input")
        if input_el:
            await input_el.type("Schedule a viewing for apt_101 on Friday at 2pm", delay=40)
            await asyncio.sleep(0.5)
            await page.keyboard.press("Enter")
            await page.wait_for_selector(".typing-indicator", state="detached", timeout=30000)
            await asyncio.sleep(3)

        # Step 5: Type query - Rent-to-income budget estimate
        print("Typing rent-to-income estimate query...")
        if input_el:
            await input_el.type("Calculate rent-to-income for $3200/mo rent with $110000 income", delay=40)
            await asyncio.sleep(0.5)
            await page.keyboard.press("Enter")
            await page.wait_for_selector(".typing-indicator", state="detached", timeout=30000)
            await asyncio.sleep(3)

        # Step 6: Generate video preview
        print("Typing video generation query...")
        if input_el:
            await input_el.type("Generate a preview video for apt_101", delay=40)
            await asyncio.sleep(0.5)
            await page.keyboard.press("Enter")
            await page.wait_for_selector(".typing-indicator", state="detached", timeout=45000)
            await asyncio.sleep(3)

        print("Finished recording actions.")
        await context.close()
        await browser.close()

    # Find recorded webm file
    webm_files = glob.glob(os.path.join(raw_dir, "*.webm"))
    if not webm_files:
        raise RuntimeError("No recorded video found in demo_raw directory.")
    
    webm_path = webm_files[0]
    print(f"Recorded raw video: {webm_path}")

    # Combine with lofi_beat.wav using ffmpeg
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    lofi_wav = os.path.abspath("lofi_beat.wav")
    final_output = os.path.abspath(FINAL_VIDEO_NAME)
    artifact_output = os.path.join(ARTIFACTS_DIR, FINAL_VIDEO_NAME)

    cmd = [
        ffmpeg_exe, "-y",
        "-i", webm_path,
        "-i", lofi_wav,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "22",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        final_output
    ]

    print("Combining video and lo-fi audio track with ffmpeg...")
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        print("FFmpeg Error:", stderr.decode())
        raise RuntimeError("FFmpeg processing failed.")

    print(f"Successfully generated demo video: {final_output}")
    shutil.copy(final_output, artifact_output)
    print(f"Copied demo video to artifacts panel: {artifact_output}")

if __name__ == "__main__":
    asyncio.run(record_demo())
