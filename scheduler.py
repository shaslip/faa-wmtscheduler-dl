import os
import json
import time
import re
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# Load environment variables
load_dotenv()
EMAIL = os.getenv("FAA_EMAIL")
PASSWORD = os.getenv("FAA_PASSWORD")

# Configuration
INITIALS = os.getenv("FAA_INITIALS")
START_URL = "https://wmtscheduler.faa.gov/Views/WorksheetView"
OUTPUT_FILE = "my_schedule.json"

def login(page):
    """Handles the Okta multi-step login process with resilient factor selection."""
    print("Starting automated login...")

    page.wait_for_selector('input[name="identifier"]')
    page.fill('input[name="identifier"]', EMAIL)
    page.click('input[type="submit"]')
    print("Email submitted. Waiting for next screen...")

    try:
        print("Looking for Factor Selection list...")
        page.wait_for_selector('.mfa-list-container, .auth-content', timeout=10000)
        password_btn = page.locator(
            'a[data-se="okta_password"], '
            'a[data-se="password"], '
            'div:has-text("Password") >> a.button:has-text("Select"), '
            '.mfa-password-button'
        ).first

        password_btn.wait_for(state="visible", timeout=5000)
        password_btn.click()
        print("Clicked 'Select' for Password factor.")

    except Exception as e:
        if page.locator('input[name="password"]').is_visible():
            print("Already on password screen, skipping selection.")
        else:
            page.screenshot(path="debug_login_error.png")
            print("Could not find 'Select' button or Password field. See debug_login_error.png")
            raise e

    print("Waiting for password input field...")

    try:
        page.wait_for_selector(".okta-waiting-spinner", state="hidden", timeout=10000)
        pw_selector = 'input[name="password"], input[type="password"], .okta-sign-in-password input'
        pw_field = page.wait_for_selector(pw_selector, state="visible", timeout=10000)
        
        pw_field.click()
        pw_field.fill("")
        page.keyboard.type(PASSWORD, delay=100)
        print("Password typed.")

        submit_btn = page.locator('.button-primary, input[type="submit"], button[type="submit"]').first
        if submit_btn.is_visible():
            submit_btn.click()
        else:
            page.keyboard.press("Enter")
        print("Submit action performed.")

    except Exception as e:
        print("FAILED at password entry. Taking screenshot...")
        page.screenshot(path="password_failure.png")
        container_html = page.locator("#okta-login-container").inner_html()
        with open("debug_container.html", "w") as f:
            f.write(container_html)
        raise e

    # 4. Gatekeeper / Warning Page
    print("Waiting for Gatekeeper/Warning screen...")
    try:
        gatekeeper_btn = page.wait_for_selector('#btnLogin', timeout=15000)
        print("Gatekeeper detected. Clicking final 'Login' button...")
        gatekeeper_btn.click()
        time.sleep(2) # Give the server a moment to register the click
    except Exception:
        print("Gatekeeper button not found. Moving to dashboard...")

    # Force navigation to the schedule in case the site's redirect hangs
    print("Navigating directly to WorksheetView...")
    page.goto(START_URL)

    # Wait for the schedule table to appear instead of relying on the URL
    page.wait_for_selector("#ScheduledShifts", timeout=30000)
    print("Successfully reached the Schedule page.")

def get_shift_from_page(page):
    try:
        page.wait_for_selector("#ScheduledShifts", timeout=5000)
        row = page.locator(f"//table[@id='ScheduledShifts']//tr[.//a[contains(text(), '{INITIALS}')]]")
        return row.first.locator("td").nth(0).inner_text().strip() if row.count() > 0 else "OFF/RDO"
    except:
        return "Error"

def get_current_date_text(page):
    try:
        return page.inner_text("#lblSelectedDate").strip()
    except:
        return "Unknown Date"

def run():
    with sync_playwright() as p:
        # Changed to headless=True to run invisibly in the background
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        page.goto(START_URL)
        login(page)
        page.wait_for_url("**/Views/WorksheetView**", timeout=30000)
        print("Login confirmed. Starting scrape...")

        schedule_data = []
        pay_periods_to_scrape = 2 # 1 for current, 1 for next
        pay_periods_processed = 0

        while pay_periods_processed < pay_periods_to_scrape:
            # Scrape all days in the currently loaded pay period
            while True:
                current_date = get_current_date_text(page)
                shift = get_shift_from_page(page)
                print(f"Scraped: {current_date} -> {shift}")

                schedule_data.append({"date": current_date, "shift": shift})

                next_day_cell = page.locator("//table[@id='WorksheetViewDayStrip']//td[contains(@style, 'ffff00')]/following-sibling::td[1]")
                if next_day_cell.count() > 0:
                    next_link = next_day_cell.locator("a[href*='/Index/']")
                    if next_link.count() > 0:
                        next_link.first.click()
                        time.sleep(1)
                        continue
                break # Reached the end of the day strip

            pay_periods_processed += 1

            # If we still need to scrape another pay period, advance the dropdown
            if pay_periods_processed < pay_periods_to_scrape:
                print("End of current pay period. Looking for next pay period...")
                
                # Execute JS to find the value of the next option in the dropdown
                next_pp_value = page.evaluate('''() => {
                    const select = document.getElementById('PayPeriodId');
                    const selectedIndex = select.selectedIndex;
                    if (selectedIndex + 1 < select.options.length) {
                        return select.options[selectedIndex + 1].value;
                    }
                    return null;
                }''')

                if next_pp_value:
                    print(f"Loading next pay period: {next_pp_value}")
                    page.select_option('#PayPeriodId', next_pp_value)
                    
                    # Wait for the page to submit and reload the schedule table
                    time.sleep(3) 
                    page.wait_for_selector("#ScheduledShifts", timeout=15000)
                else:
                    print("No more future pay periods available in the dropdown.")
                    break

        with open(OUTPUT_FILE, 'w') as f:
            json.dump(schedule_data, f, indent=4)

        print(f"Done. Saved {len(schedule_data)} days to {OUTPUT_FILE}.")
        browser.close()

if __name__ == "__main__":
    run()
