# -*- coding: utf-8 -*-
import sys
import io
import time
import requests
import re
from playwright.sync_api import sync_playwright

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ============================================================
# TEMP EMAIL FUNCTIONS (Multiple providers with fallback)
# ============================================================

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def get_temp_email():
    """Generate a temporary email - tries multiple providers"""
    
    # Provider 1: temp-mail.io (WORKING)
    try:
        print("[MAIL] Trying temp-mail.io ...")
        resp = requests.post(
            'https://api.internal.temp-mail.io/api/v3/email/new',
            json={'min_name_length': 10, 'max_name_length': 10},
            timeout=15,
            headers=HEADERS
        )
        if resp.status_code == 200:
            data = resp.json()
            email_addr = data['email']
            token = data.get('token', '')
            print(f"[MAIL] temp-mail.io email created: {email_addr}")
            return email_addr, {'provider': 'temp-mail.io', 'email': email_addr}
        else:
            raise Exception(f"Status: {resp.status_code}")
    except Exception as e:
        print(f"[WARN] temp-mail.io failed: {e}")

    # Provider 2: mail.tm
    try:
        print("[MAIL] Trying mail.tm ...")
        resp = requests.get('https://api.mail.tm/domains', timeout=10)
        domains = resp.json()
        if 'hydra:member' in domains and len(domains['hydra:member']) > 0:
            domain = domains['hydra:member'][0]['domain']
        else:
            raise Exception("No domains available")
        
        import random, string
        username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
        email_addr = f"{username}@{domain}"
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        
        resp = requests.post('https://api.mail.tm/accounts', json={
            "address": email_addr, "password": password
        }, timeout=10)
        
        if resp.status_code in [200, 201]:
            resp2 = requests.post('https://api.mail.tm/token', json={
                "address": email_addr, "password": password
            }, timeout=10)
            token = resp2.json().get('token', '')
            print(f"[MAIL] mail.tm email created: {email_addr}")
            return email_addr, {'provider': 'mail.tm', 'token': token}
        else:
            raise Exception(f"Account creation failed: {resp.status_code}")
    except Exception as e:
        print(f"[WARN] mail.tm failed: {e}")

    # Provider 3: GuerrillaMail
    try:
        print("[MAIL] Trying guerrillamail.com ...")
        resp = requests.get('http://api.guerrillamail.com/ajax.php?f=get_email_address', timeout=10)
        data = resp.json()
        email_addr = data['email_addr']
        sid_token = data['sid_token']
        print(f"[MAIL] GuerrillaMail email created: {email_addr}")
        return email_addr, {'provider': 'guerrillamail', 'sid_token': sid_token}
    except Exception as e:
        print(f"[WARN] GuerrillaMail failed: {e}")

    print("[ERROR] All email providers failed!")
    return None, None


def check_mailbox(session_data, max_retries=30, delay=5):
    """Check inbox and extract verification code"""
    provider = session_data.get('provider', '')
    
    for i in range(max_retries):
        print(f"[MAIL] Checking inbox ({provider})... (Attempt {i+1}/{max_retries})")
        try:
            if provider == 'temp-mail.io':
                email_addr = session_data['email']
                resp = requests.get(
                    f'https://api.internal.temp-mail.io/api/v3/email/{email_addr}/messages',
                    timeout=15,
                    headers=HEADERS
                )
                if resp.status_code == 200:
                    messages = resp.json()
                    for msg in messages:
                        msg_body = msg.get('body_text', '') or msg.get('body_html', '') or msg.get('subject', '')
                        code = _extract_code(msg_body)
                        if code:
                            return code

            elif provider == 'mail.tm':
                token = session_data['token']
                resp = requests.get('https://api.mail.tm/messages', headers={
                    'Authorization': f'Bearer {token}'
                }, timeout=10)
                messages = resp.json().get('hydra:member', [])
                for msg in messages:
                    msg_id = msg['id']
                    msg_resp = requests.get(f'https://api.mail.tm/messages/{msg_id}', headers={
                        'Authorization': f'Bearer {token}'
                    }, timeout=10)
                    msg_body = msg_resp.json().get('text', '') or msg_resp.json().get('html', [''])[0]
                    code = _extract_code(msg_body)
                    if code:
                        return code

            elif provider == 'guerrillamail':
                sid_token = session_data['sid_token']
                resp = requests.get(
                    f'http://api.guerrillamail.com/ajax.php?f=check_email&seq=0&sid_token={sid_token}',
                    timeout=10
                )
                messages = resp.json().get('list', [])
                for msg in messages:
                    if 'guerrillamail' in msg.get('mail_from', '').lower():
                        continue
                    msg_id = msg['mail_id']
                    msg_resp = requests.get(
                        f'http://api.guerrillamail.com/ajax.php?f=fetch_email&email_id={msg_id}&sid_token={sid_token}',
                        timeout=10
                    )
                    msg_body = msg_resp.json().get('mail_body', '')
                    code = _extract_code(msg_body)
                    if code:
                        return code

        except Exception as e:
            print(f"[MAIL] Error: {e}")
        time.sleep(delay)
    
    print("[MAIL] Timeout waiting for email.")
    return None


def _extract_code(text):
    """Extract verification code from email body"""
    match = re.search(r'\b(\d{6})\b', text)
    if match:
        code = match.group(1)
        print(f"[MAIL] Code extracted: {code}")
        return code
    match = re.search(r'\b(\d{4})\b', text)
    if match:
        code = match.group(1)
        print(f"[MAIL] Code extracted (4 digits): {code}")
        return code
    return None


# ============================================================
# MAIN AUTOMATION
# ============================================================

def run_automation():
    # Step 0: Generate temp email
    email, sid_token = get_temp_email()
    if not email:
        print("[ERROR] Could not generate temp email. Exiting.")
        return {"success": False, "error": "Could not generate temp email"}
    print(f"[OK] Generated temporary email: {email}")

    with sync_playwright() as p:
        # Launch browser in headless mode for server deployment
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'])

        # Create isolated context (clean cookies every time) with clipboard permissions
        context = browser.new_context(permissions=['clipboard-read', 'clipboard-write'])
        page = context.new_page()

        try:
            # ==== STEP 1: Navigate to site (with retry) ====
            max_nav_retries = 5
            for attempt in range(1, max_nav_retries + 1):
                try:
                    print(f"[STEP 1] Navigating to bot.botnovabooster.ru ... (Attempt {attempt}/{max_nav_retries})")
                    page.goto('https://bot.botnovabooster.ru', wait_until='domcontentloaded', timeout=90000)
                    print("[STEP 1] Page loaded successfully!")
                    break
                except Exception as nav_err:
                    print(f"[WARN] Navigation failed: {nav_err}")
                    if attempt < max_nav_retries:
                        print(f"[INFO] Retrying in 5 seconds...")
                        page.wait_for_timeout(5000)
                    else:
                        raise Exception(f"Failed to navigate after {max_nav_retries} attempts")
            # Wait briefly before finding the email button
            page.wait_for_timeout(1000)

            # ==== STEP 2: Click "Email" button ====
            print("[STEP 2] Clicking 'Email' button...")
            email_btn = page.locator('text="Email"').first
            email_btn.wait_for(state='visible', timeout=30000)
            email_btn.click()
            page.wait_for_timeout(500)

            # ==== STEP 3: Enter email address ====
            print(f"[STEP 3] Entering email: {email}")
            email_input = page.get_by_placeholder('your@email.com')
            email_input.wait_for(state='visible', timeout=10000)
            email_input.fill(email)
            page.wait_for_timeout(500)

            # ==== STEP 4: Click "Войти" (Login/Register) ====
            print("[STEP 4] Clicking login button...")
            login_btn = page.locator('button', has_text='\u0412\u043e\u0439\u0442\u0438')
            login_btn.click()
            page.wait_for_timeout(1000)

            # ==== STEP 5: Wait for verification code email ====
            print("[STEP 5] Waiting for verification code in email...")
            code = check_mailbox(sid_token, delay=2)
            if not code:
                print("[ERROR] Could not retrieve verification code. Exiting.")
                return {"success": False, "error": "Could not retrieve verification code"}

            # ==== STEP 6: Enter the 6-digit code ====
            print(f"[STEP 6] Entering verification code: {code}")
            # The code page has 6 separate input fields
            code_inputs = page.locator('input[type="text"], input[type="number"], input[type="tel"]')
            input_count = code_inputs.count()
            print(f"[INFO] Found {input_count} code input fields")

            if input_count >= len(code):
                for idx, digit in enumerate(code):
                    code_inputs.nth(idx).fill(digit)
                    page.wait_for_timeout(200)
            else:
                # Fallback: try to find inputs and type digit by digit
                print("[INFO] Trying keyboard input fallback...")
                first_input = code_inputs.first
                first_input.click()
                for digit in code:
                    page.keyboard.press(digit)
                    page.wait_for_timeout(200)

            # Wait for auto-submission or page transition
            print("[STEP 6] Code entered. Waiting for page to process...")
            page.wait_for_timeout(2000)

            # ==== STEP 7: Skip Passkey (click "Пропустить") ====
            print("[STEP 7] Skipping Passkey setup...")
            try:
                skip_btn = page.locator('text="\u041f\u0440\u043e\u043f\u0443\u0441\u0442\u0438\u0442\u044c"')
                skip_btn.wait_for(state='visible', timeout=15000)
                skip_btn.click()
                page.wait_for_timeout(1000)
            except Exception as e:
                print(f"[WARN] Could not find skip button, trying alternatives: {e}")
                # Try clicking anywhere that says skip
                page.locator('button:has-text("\u041f\u0440\u043e\u043f\u0443\u0441\u0442\u0438\u0442\u044c"), a:has-text("\u041f\u0440\u043e\u043f\u0443\u0441\u0442\u0438\u0442\u044c")').first.click()
                page.wait_for_timeout(1000)

            # ==== STEP 8: Click "Подключить устройство" (Connect device) ====
            print("[STEP 8] Clicking 'Connect Device'...")
            try:
                connect_btn = page.locator('text="\u041f\u043e\u0434\u043a\u043b\u044e\u0447\u0438\u0442\u044c \u0443\u0441\u0442\u0440\u043e\u0439\u0441\u0442\u0432\u043e"')
                connect_btn.wait_for(state='visible', timeout=15000)
                connect_btn.click()
                page.wait_for_timeout(1000)
            except Exception:
                # Alternative: look for the green button on the dashboard
                print("[INFO] Trying alternative selector for connect button...")
                page.locator('button', has_text='\u041f\u043e\u0434\u043a\u043b\u044e\u0447\u0438\u0442\u044c').first.click()
                page.wait_for_timeout(1000)

            # ==== STEP 9: Click "Другое устройство" (Other device) ====
            print("[STEP 9] Clicking 'Other Device'...")
            try:
                other_device_btn = page.locator('text="\u0414\u0440\u0443\u0433\u043e\u0435 \u0443\u0441\u0442\u0440\u043e\u0439\u0441\u0442\u0432\u043e"')
                other_device_btn.wait_for(state='visible', timeout=15000)
                other_device_btn.click()
                page.wait_for_timeout(1000)
            except Exception:
                print("[INFO] Trying alternative selector for 'other device' button...")
                page.locator('button', has_text='\u0414\u0440\u0443\u0433\u043e\u0435').first.click()
                page.wait_for_timeout(1000)

            # ==== STEP 10: Extract the link ====
            print("[STEP 10] Extracting the link...")

            final_link = None

            # Attempt 0: Search page content for the exact pattern first
            print("[INFO] Searching page content for /sub/ pattern...")
            try:
                page_text = page.content()
                # Look for tsub-novavps.ru or similar domains with /sub/ and a token
                sub_matches = re.findall(r'(https?://[a-zA-Z0-9.-]+/sub/[^\s"<>]+)', page_text)
                if sub_matches:
                    final_link = sub_matches[0]
                    print(f"[INFO] Found link via regex in HTML: {final_link}")
            except Exception as e:
                print(f"[WARN] Regex search failed: {e}")

            # Method 1: Try to get the link from "Скопировать ссылку" button
            if not final_link:
                try:
                    # Inject clipboard interceptor just in case
                    page.evaluate("window.copiedText = ''; navigator.clipboard.writeText = async (text) => { window.copiedText = text; };")
                    
                    copy_btn = page.locator('text="\u0421\u043a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0441\u0441\u044b\u043b\u043a\u0443"')
                    copy_btn.wait_for(state='visible', timeout=10000)

                    # Try to get the link from clipboard by clicking the copy button
                    copy_btn.click()
                    page.wait_for_timeout(1500)

                    # Check intercepted clipboard
                    intercepted = page.evaluate('window.copiedText')
                    if intercepted and 'http' in intercepted:
                        final_link = intercepted
                        print("[INFO] Got link from intercepted clipboard.")
                    else:
                        # Try to read actual clipboard
                        try:
                            clipboard_text = page.evaluate('navigator.clipboard.readText()')
                            if clipboard_text and 'http' in clipboard_text:
                                final_link = clipboard_text
                                print("[INFO] Got link from actual clipboard.")
                        except Exception:
                            pass
                except Exception as e:
                    print(f"[WARN] Could not click copy button: {e}")

            # Method 2: Try to get link from any visible text or href on the page
            if not final_link:
                try:
                    # Look for links on the page
                    all_links = page.locator('a[href]')
                    for i in range(all_links.count()):
                        href = all_links.nth(i).get_attribute('href')
                        if href and '/sub/' in href:
                            final_link = href
                            print("[INFO] Got link from href.")
                            break
                except Exception:
                    pass

            # Final validation to avoid returning the installation guide URL
            if final_link and 'bot.botnovabooster.ru' in final_link and 'subscriptionId' in final_link:
                print("[WARN] Extracted link is the page URL, not the subscription link. Invalidating it.")
                final_link = None

            print("=" * 60)
            print(f"[RESULT] Final extracted link: {final_link}")
            print(f"[RESULT] Current page URL: {page.url}")
            print("=" * 60)

            if not final_link:
                return {"success": False, "error": "Could not find the correct subscription link (/sub/...)."}

            return {"success": True, "link": final_link, "email": email}

        except Exception as e:
            print(f"[ERROR] Automation failed: {e}")
            error_msg = str(e)
            # Take screenshot for debugging
            try:
                page.screenshot(path='error_screenshot.png')
                print("[INFO] Error screenshot saved to error_screenshot.png")
            except:
                pass
            return {"success": False, "error": error_msg}
        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    print(run_automation())
