
import os
import random
import tempfile
import urllib.request
import pydub
import speech_recognition as sr
import time
import numpy as np
from scipy.interpolate import splrep, splev
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException

def human_move(driver, element):
    """Simulate human-like mouse movement to an element using B-spline interpolation, corrected for viewport bounds"""
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(0.2)

        rect = driver.execute_script("return arguments[0].getBoundingClientRect();", element)
        size = element.size
        target_x = rect['x'] + rect['width'] / 2
        target_y = rect['y'] + rect['height'] / 2

        # Get browser viewport size
        viewport_width = driver.execute_script("return window.innerWidth")
        viewport_height = driver.execute_script("return window.innerHeight")

        # Clamp target coordinates to viewport
        target_x = min(max(target_x, 0), viewport_width - 1)
        target_y = min(max(target_y, 0), viewport_height - 1)

        # Choose a starting point well within viewport to ensure it's in bounds
        start_x = random.uniform(50, viewport_width / 2)
        start_y = random.uniform(50, viewport_height / 2)

        control_points = np.array([
            [start_x, start_y],
            [start_x + (target_x - start_x) * 0.3, start_y + (target_y - start_y) * 0.2],
            [start_x + (target_x - start_x) * 0.6, start_y + (target_y - start_y) * 0.7],
            [target_x, target_y]
        ])

        t = range(len(control_points))
        ipl_t = np.linspace(0.0, len(control_points) - 1, 60)

        x_i = splev(ipl_t, splrep(t, control_points[:, 0], k=3))
        y_i = splev(ipl_t, splrep(t, control_points[:, 1], k=3))

        prev_x, prev_y = x_i[0], y_i[0]

        action = ActionChains(driver)
        action.move_to_element_with_offset(element, 0, 0).perform()  # to ensure mouse context starts inside browser
        for new_x, new_y in zip(x_i[1:], y_i[1:]):
            dx = new_x - prev_x
            dy = new_y - prev_y
            prev_x, prev_y = new_x, new_y

            step = ActionChains(driver)
            step.move_by_offset(dx, dy).perform()
            time.sleep(random.uniform(0.005, 0.02))

        ActionChains(driver).move_to_element_with_offset(element, size['width']//2, size['height']//2).click().perform()
        time.sleep(random.uniform(0.1, 0.3))

    except Exception as e:
        print(f"⚠️ Human movement failed: {e}")
        try:
            element.click()
        except:
            pass


def trace_iframes(driver):
    print("🔍 Enumerating iframes on page...")
    frames = driver.find_elements(By.TAG_NAME, "iframe")
    for i, frame in enumerate(frames):
        try:
            title = frame.get_attribute("title")
            src = frame.get_attribute("src")
            print(f"#{i}: title='{title}', src='{src}'")
        except Exception as e:
            print(f"⚠️ Error reading iframe #{i}: {e}")
    print(f"🔎 Total iframes found: {len(frames)}")


def download_and_recognize_audio(audio_url):
    mp3_path = os.path.join(tempfile.gettempdir(), f"{random.randint(0, 999999)}.mp3")
    wav_path = mp3_path.replace('.mp3', '.wav')

    try:
        urllib.request.urlretrieve(audio_url, mp3_path)
        sound = pydub.AudioSegment.from_mp3(mp3_path)
        sound = sound.set_channels(1).set_frame_rate(16000)
        sound.export(wav_path, format="wav")

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio = recognizer.record(source)

        return recognizer.recognize_google(audio)

    finally:
        for path in [mp3_path, wav_path]:
            if os.path.exists(path):
                os.remove(path)


def is_captcha_solved(driver):
    try:
        WebDriverWait(driver, 5).until(
            EC.frame_to_be_available_and_switch_to_it((By.ID, "webprocureframe"))
        )
        WebDriverWait(driver, 5).until(
            EC.frame_to_be_available_and_switch_to_it((By.XPATH, "//iframe[@title='reCAPTCHA']"))
        )
        driver.find_element(By.CLASS_NAME, "recaptcha-checkbox-checked")
        return True
    except Exception:
        return False
    finally:
        driver.switch_to.default_content()




def solve_captcha(driver):
    #trace_iframes(driver)
        
    try:
        # Check if we're already in the correct iframe
        frame_title = driver.execute_script("return window.frameElement ? window.frameElement.title : '';")
        if frame_title != "reCAPTCHA":
            print("📦 Switching to reCAPTCHA iframe...")
            WebDriverWait(driver, 10).until(
                EC.frame_to_be_available_and_switch_to_it((By.XPATH, "//iframe[@title='reCAPTCHA']"))
            )
        else:
            print("✅ Already inside reCAPTCHA iframe.")

        checkbox = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "recaptcha-checkbox-border"))
        )
        checkbox.click()
        print("☑️ Checkbox clicked")
        time.sleep(2)

        #human_move(driver, checkbox)
        print("☑️ Checkbox clicked with human-like movement")
        time.sleep(random.uniform(1.5, 2.5))

        driver.switch_to.default_content()
        driver.switch_to.frame("webprocureframe")


        if is_captcha_solved(driver):
            print("✅ CAPTCHA checkbox click was sufficient.")
            return True

        print("🔁 Re-entering main iframe: webprocureframe")
        WebDriverWait(driver, 10).until(
            EC.frame_to_be_available_and_switch_to_it((By.ID, "webprocureframe"))
        )

        print("🎯 Switching to challenge iframe...")
        WebDriverWait(driver, 10).until(
            EC.frame_to_be_available_and_switch_to_it((By.XPATH, "//iframe[contains(@title, 'challenge')]"))
        )

        print("🎧 Clicking audio challenge button...")
        audio_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "recaptcha-audio-button"))
        )

        human_move(driver, audio_btn)
        time.sleep(random.uniform(1.0, 1.8))

        for attempt in range(3):
            print(f"🔄 Attempt {attempt + 1} to solve audio challenge")
            src = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "audio-source"))
            ).get_attribute("src")

            audio_text = download_and_recognize_audio(src)
            print(f"🎤 Recognized audio text: {audio_text}")

            response_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "audio-response"))
            )
            print('typing')
            for char in audio_text.lower():
                response_box.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))
            time.sleep(random.uniform(0.2, 0.5))

            verify_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "recaptcha-verify-button"))
            )
            human_move(driver, verify_btn)
            time.sleep(random.uniform(1.0, 2.0))

            driver.switch_to.default_content()
            driver.switch_to.frame("webprocureframe")

            if is_captcha_solved(driver):
                print("✅ CAPTCHA solved successfully!")
                return True
            else:
                print("❌ CAPTCHA not solved, retrying...")
                WebDriverWait(driver, 10).until(
                    EC.frame_to_be_available_and_switch_to_it((By.ID, "webprocureframe"))
                )
                WebDriverWait(driver, 10).until(
                    EC.frame_to_be_available_and_switch_to_it((By.XPATH, "//iframe[contains(@title, 'challenge')]"))
                )

                reload_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "recaptcha-reload-button"))
                )
                human_move(driver, reload_btn)
                time.sleep(random.uniform(1.0, 2.0))

        raise Exception("❌ Failed to solve CAPTCHA after multiple attempts.")

    except Exception as e:
        print(f"❌ CAPTCHA solving failed: {e}")
        return False
