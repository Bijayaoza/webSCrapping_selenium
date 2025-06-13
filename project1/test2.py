import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import subprocess
from RecaptchaSolver import solve_captcha

def safe_click(driver, element):
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        WebDriverWait(driver, 5).until(EC.element_to_be_clickable(element)).click()
        return True
    except Exception as e:
        print(f"⚠️ Click failed: {e}")
        return False

def force_click(driver, element):
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        driver.execute_script("arguments[0].click();", element)
        return True
    except Exception as e:
        print(f"⚠️ Forced click failed: {e}")
        return False

def search_ct_bidboard(part_number):
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")

    try:
        driver = uc.Chrome(options=options, version_main=137, headless=False, use_subprocess=True)
    except Exception as e:
        print(f"❌ Chrome launch failed: {e}")
        return

    try:
        print("🌐 Opening CT BidBoard...")
        driver.get("https://portal.ct.gov/das/ctsource/bidboard")
        time.sleep(5)

        print("🔁 Switching to iframe: #webprocureframe")
        driver.switch_to.frame("webprocureframe")
        time.sleep(5)

        print("⌨️ Typing part number into search bar...")
        js_typing = f"""
        const input = document.querySelector('#search');
        if (input) {{
            input.focus();
            input.value = "{part_number}";
            input.dispatchEvent(new InputEvent('input', {{ bubbles: true }}));
            input.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Enter' }}));
            input.dispatchEvent(new KeyboardEvent('keyup', {{ key: 'Enter' }}));
            return true;
        }}
        return false;
        """
        success = driver.execute_script(js_typing)
        if not success:
            print("❌ Failed to find or type in the search box.")
            return

        time.sleep(8)

        print("🔍 Looking for matching bid link...")
        matches = driver.find_elements(By.CSS_SELECTOR, 'a[style*="cursor: pointer"]')
        target = next((el for el in matches if part_number in el.text), None)

        if not target:
            print("❌ No matching result found for part number.")
            return

        print("✅ Found match, clicking...")
        target.click()
        time.sleep(10)

        print("📂 Looking for downloadable PDFs...")
        ul_xpaths = [
            '/html/body/div[1]/app-root/app-bid-board/app-bid-board-details/div[2]/div/div[6]/div/div/div/div[1]/ul',
            '/html/body/div[1]/app-root/app-bid-board/app-bid-board-details/div[2]/div/div[6]/div/div/div/div[2]/ul',
            '/html/body/div[1]/app-root/app-bid-board/app-bid-board-details/div[2]/div/div[6]/div/div/div/div[3]/ul'
        ]

        pdf_links = []

        for xpath in ul_xpaths:
            try:
                ul_element = driver.find_element(By.XPATH, xpath)
                anchors = ul_element.find_elements(By.TAG_NAME, "a")
                for a in anchors:
                    text = a.text.strip().lower()
                    if text.endswith(".pdf"):
                        pdf_links.append(a)
            except Exception as e:
                print(f"⚠️ Error processing XPath {xpath}: {e}")
                

        for link in pdf_links:
            while True:
                try:
                    driver.switch_to.default_content()
                    driver.switch_to.frame("webprocureframe")
                    print(f"⬇️ Attempting download: {link.text.strip()}")

                    if not force_click(driver, link):
                        print("⚠️ Force click failed. Retrying in 1 minute...")
                        time.sleep(60)
                        continue

                    overlay = driver.find_elements(By.CSS_SELECTOR, "div.modal-overlay[style*='display: block']")
                    time.sleep(8)

                    if overlay:
                        print("🔐 CAPTCHA modal detected — solving...")
                        solve_captcha(driver)
                        time.sleep(10)

                        print("🔁 Retrying download after CAPTCHA...")
                        driver.switch_to.default_content()
                        driver.switch_to.frame("webprocureframe")

                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div.modal[style*='display: block']"))
                        )

                        try:
                            download_button = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((
                                    By.XPATH,
                                    "//button[contains(@class, 'modal-close') and .//i[contains(@class, 'fa-download')]]"
                                ))
                            )
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", download_button)
                            download_button.click()
                            print("✅ Download successful.")
                            break  # Exit retry loop
                        except Exception as e:
                            print(f"⚠️ Failed to click download button after CAPTCHA: {e}")
                    else:
                        print("✅ Download started without CAPTCHA.")
                        break  # Exit retry loop

                except Exception as e:
                    print(f"❌ Unexpected error: {e}")

                print("⏳ Waiting 1 minute before retrying this download...\n")
                time.sleep(60)

        print("💾 All files attempted.")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        driver.quit()
        print("🧹 Browser closed.")

if __name__ == "__main__":
    part_number = input("Enter Part Number: ").strip()
    search_ct_bidboard(part_number)
