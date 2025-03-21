import sys
import time
from playwright.sync_api import sync_playwright

def run(playwright):
    print("Starting Playwright...")
    time.sleep(2)  # Simulate some delay for demonstration
    print("Launching browser...")
    browser = playwright.chromium.launch()
    print("Opening a new page...")
    time.sleep(2)  # Simulate some delay for demonstration
    page = browser.new_page()
    page.goto(sys.argv[1])
    # page.wait_for_timeout(10000)
    page.screenshot(path=sys.argv[1].split(".")[0] + ".png")
    browser.close()

with sync_playwright() as playwright:
    run(playwright)