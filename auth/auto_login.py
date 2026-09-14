"""Automated stealth authentication for Lidl accounts."""

import argparse
import json
import os
import sys
import time
from typing import List, Optional

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from playwright_stealth import Stealth

from config import LidlConfig, get_account_config, load_accounts
from .file_auth import load_cookies_from_file
from .session_manager import test_api_connection


def auto_login(
    account: str,
    country: str = "nl",
    email: Optional[str] = None,
    password: Optional[str] = None,
    interactive: bool = True,
    headless: bool = True,
    timeout_ms: int = 45000,
    cookie_file: Optional[str] = None,
) -> bool:
    """
    Programmatically log into accounts.lidl.com and extract session cookies.

    Args:
        account: Account identifier (e.g. 'ruben', 'kaja').
        country: Country code (e.g. 'nl', 'de').
        email: Account email (if None, loaded from credentials).
        password: Account password (if None, loaded from credentials).
        interactive: If True, prompt user on CLI for MFA challenge codes.
        headless: Run browser in headless mode.
        timeout_ms: Navigation and selector timeout in milliseconds.
        cookie_file: Target path for saving cookies (defaults to lidl_cookies_{country}_{account}.json).

    Returns:
        bool: True if authentication succeeded and valid cookies were saved, False otherwise.
    """
    account = account.strip().lower()
    country = country.strip().lower()

    if not email or not password:
        config = get_account_config(account)
        if not config:
            print(f"✗ Keine Zugangsdaten für Konto '{account}' gefunden.")
            print("  Bitte prüfe 'accounts.json' oder Umgebungsvariablen.")
            return False
        email = config.email
        password = config.password

    target_cookie_file = cookie_file or f"lidl_cookies_{country}_{account}.json"
    print(f"\n[Auto-Login] Starte Anmeldung für Konto '{account}' ({country.upper()}) -> {email}...")

    stealth = Stealth()
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--disable-dev-shm-usage",
            ],
        )

        context = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale=f"{country}-{country.upper()}",
        )

        page = context.new_page()
        stealth.apply_stealth_sync(page)

        try:
            mla_url = f"https://www.lidl.{country}/mla/"
            print(f"[Auto-Login] Öffne {mla_url} ...")
            page.goto(mla_url, wait_until="networkidle", timeout=timeout_ms)

            time.sleep(1.5)
            _handle_cookie_consent(page)

            # Step 1: Input Email
            print("[Auto-Login] Gebe E-Mail-Adresse ein...")
            email_input = page.wait_for_selector(
                "input#input-email, input[type='email'], input[name='EmailOrPhone']",
                timeout=15000,
            )
            email_input.fill(email)
            time.sleep(0.5)

            # Click next (ensuring we do not click Google login)
            _click_next_button(page)

            # Wait for response (check for overcapacity / rate limit or password input)
            time.sleep(2.5)
            _handle_possible_rate_limit(page)

            # Step 2: Input Password
            print("[Auto-Login] Gebe Passwort ein...")
            pwd_input = page.wait_for_selector(
                "input#Password, input[type='password']",
                timeout=15000,
            )
            pwd_input.fill(password)
            time.sleep(0.5)

            # Click password submit button
            _click_password_submit_button(page)

            # Step 3: Handle MFA or Success
            print("[Auto-Login] Warte auf Anmeldebestätigung / MFA-Prüfung...")
            time.sleep(4)

            # Check for MFA challenge
            mfa_detected = _detect_mfa_challenge(page)
            if mfa_detected:
                print(f"🔐 [MFA] Zwei-Faktor-Authentifizierung (MFA) erforderlich für '{account}'!")
                if not interactive:
                    print(f"✗ [MFA] Nicht-interaktiver Modus aktiv. Anmeldung für '{account}' abgebrochen.")
                    return False

                mfa_success = _handle_mfa_interactive(page, email)
                if not mfa_success:
                    print(f"✗ [MFA] Zwei-Faktor-Authentifizierung fehlgeschlagen.")
                    return False

            # Wait for login completion / cookies to populate
            _wait_for_login_completion(page, context, country, max_seconds=15)

            # Extract cookies
            raw_cookies = context.cookies()
            saved_cookies = _extract_and_format_cookies(raw_cookies, country)

            if not saved_cookies:
                print(f"✗ Keine gültigen Authentifizierungs-Cookies nach dem Login gefunden.")
                return False

            # Save cookies to target JSON file
            with open(target_cookie_file, "w", encoding="utf-8") as f:
                json.dump(saved_cookies, f, indent=2)

            print(f"✓ {len(saved_cookies)} Cookies gespeichert in '{target_cookie_file}'")

            # Validate the newly saved cookies using LidlConfig & test_api_connection
            LidlConfig.set_country(country)
            LidlConfig.set_account(account)
            session = load_cookies_from_file(target_cookie_file)
            if session:
                is_valid = test_api_connection(session)
                if is_valid:
                    print(f"✓ Auto-Login erfolgreich verifiziert für '{account}' ({country.upper()})!")
                    return True
                else:
                    print(f"⚠ Cookies gespeichert, aber API-Verbindungstest meldet Warnung (möglicherweise keine Kassenbons).")
                    return True
            else:
                print(f"✗ Fehler beim Laden der neu erstellten Cookie-Datei.")
                return False

        except PlaywrightTimeoutError as te:
            print(f"✗ Timeout beim Auto-Login für '{account}' ({country}): {te}")
            return False
        except Exception as ex:
            print(f"✗ Unerwarteter Fehler beim Auto-Login: {ex}")
            return False
        finally:
            browser.close()


def _handle_cookie_consent(page) -> None:
    """Detect and accept cookie consent banner if present."""
    try:
        # Check all matching cookie buttons and click the visible one
        cookie_selectors = [
            "button#cookie-consent-accept",
            "button#onetrust-accept-btn-handler",
            "button:has-text('Accepteren')",
            "button:has-text('Alles accepteren')",
            "button:has-text('Alle akzeptieren')",
            "button:has-text('Zustimmen')",
            "button:has-text('OK')",
        ]
        for sel in cookie_selectors:
            for btn in page.query_selector_all(sel):
                if btn.is_visible():
                    btn.click()
                    time.sleep(1)
                    return
    except Exception:
        pass


def _click_next_button(page) -> None:
    """Click the 'Next' submit button after entering email, avoiding Google login."""
    # Preferred selector by data-testid
    btn = page.query_selector("button[data-testid='login-or-register-submit-button']")
    if btn and btn.is_visible():
        btn.click()
        return

    # Fallback to visible buttons excluding Google
    for b in page.query_selector_all("button"):
        if not b.is_visible():
            continue
        testid = b.get_attribute("data-testid") or ""
        text = b.inner_text().strip().lower()
        if "google" in testid.lower() or "google" in text:
            continue
        if text in ["weiter", "volgende", "next", "continue"]:
            b.click()
            return

    # Fallback to Enter key
    page.keyboard.press("Enter")


def _click_password_submit_button(page) -> None:
    """Click the submit button on the password step."""
    # Check data-testids used by Lidl
    for sel in [
        "button[data-testid='button-primary']",
        "button[data-testid='login-input-password-button']",
        "button[data-testid='login-or-register-submit-button']",
    ]:
        btn = page.query_selector(sel)
        if btn and btn.is_visible():
            btn.click()
            return

    # Check visible buttons
    for b in page.query_selector_all("button"):
        if not b.is_visible():
            continue
        testid = b.get_attribute("data-testid") or ""
        text = b.inner_text().strip().lower()
        if "google" in testid.lower() or "google" in text or "zurück" in text or "terug" in text:
            continue
        if text in ["weiter", "volgende", "anmelden", "inloggen", "login", "submit"]:
            b.click()
            return

    page.keyboard.press("Enter")


def _handle_possible_rate_limit(page) -> None:
    """Check for temporary rate limit / overcapacity message and retry if necessary."""
    try:
        body_text = page.inner_text("body").lower()
        if "kapazität wurde überschritten" in body_text or "overcapacity" in body_text:
            print("⚠ Vorübergehende Kapazitätsgrenze erkannt. Warte 5 Sekunden...")
            time.sleep(5)
            _click_next_button(page)
            time.sleep(3)
    except Exception:
        pass


def _detect_mfa_challenge(page) -> bool:
    """Check whether an MFA / OTP verification challenge is active."""
    try:
        url = page.url.lower()
        if "mfa" in url or "otp" in url or "verification" in url:
            return True

        # Check for visible code input
        code_input = page.query_selector(
            "input[name='VerificationCode'], input#VerificationCode, input[type='tel'], input[data-testid*='code']"
        )
        if code_input and code_input.is_visible():
            return True

        # Check body text
        body = page.inner_text("body").lower()
        mfa_keywords = [
            "verificatiecode",
            "bevestigingscode",
            "bestätigungscode",
            "sicherheitscode",
            "verification code",
            "sms-code",
        ]
        return any(k in body for k in mfa_keywords)
    except Exception:
        return False


def _handle_mfa_interactive(page, email: str) -> bool:
    """Prompt user for MFA code on CLI, input it, and submit."""
    try:
        code_input = page.wait_for_selector(
            "input[name='VerificationCode'], input#VerificationCode, input[type='tel'], input[data-testid*='code'], input[type='text']",
            timeout=10000,
        )

        code = input(f"\n👉 [MFA] Bitte gib den Verifizierungscode für '{email}' ein: ").strip()
        if not code:
            print("✗ Kein Code eingegeben.")
            return False

        code_input.fill(code)
        time.sleep(0.5)

        # Click submit button
        submitted = False
        for sel in [
            "button[data-testid='button-primary']",
            "button[data-testid*='submit']",
            "button:has-text('Verifiëren')",
            "button:has-text('Bestätigen')",
            "button:has-text('Volgende')",
            "button:has-text('Weiter')",
        ]:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                btn.click()
                submitted = True
                break

        if not submitted:
            page.keyboard.press("Enter")

        time.sleep(5)
        return True
    except Exception as ex:
        print(f"✗ Fehler beim Verarbeiten des MFA-Codes: {ex}")
        return False


def _wait_for_login_completion(page, context, country: str, max_seconds: int = 15) -> None:
    """Wait for cookies or page navigation indicating login completion."""
    start = time.time()
    while time.time() - start < max_seconds:
        cookies = context.cookies()
        has_auth = any(
            c.get("name") in ["authToken", "ldi-customertoken", "LidlID"]
            for c in cookies
        )
        if has_auth:
            time.sleep(1)
            return

        # Check if URL redirected back to lidl.{country}
        if f"lidl.{country}" in page.url and "/Account/Login" not in page.url:
            time.sleep(1)
            return

        time.sleep(1)


def _extract_and_format_cookies(raw_cookies: List[dict], country: str) -> List[dict]:
    """Filter and format cookies for storage in lidl_cookies_{country}_{account}.json."""
    expected_domain = f"lidl.{country}"
    formatted = []
    cookie_id = 1

    for c in raw_cookies:
        domain = c.get("domain", "")
        # Keep cookies belonging to the target country domain or lidl.com SSO
        if expected_domain in domain or "lidl.com" in domain:
            formatted.append({
                "domain": domain,
                "expirationDate": c.get("expires", None),
                "hostOnly": not domain.startswith("."),
                "httpOnly": c.get("httpOnly", False),
                "name": c.get("name", ""),
                "path": c.get("path", "/"),
                "sameSite": c.get("sameSite", "unspecified"),
                "secure": c.get("secure", False),
                "session": c.get("expires", -1) in [-1, None],
                "storeId": "0",
                "value": c.get("value", ""),
                "id": cookie_id,
            })
            cookie_id += 1

    return formatted


def main():
    parser = argparse.ArgumentParser(description="Automated Lidl login and cookie retrieval.")
    parser.add_argument("--account", "-a", required=True, help="Account name (e.g. 'ruben', 'kaja')")
    parser.add_argument("--country", "-c", default="nl", help="Country code (e.g. 'nl', 'de'). Default: nl")
    parser.add_argument("--non-interactive", action="store_true", help="Disable interactive prompts for MFA")
    parser.add_argument("--headful", action="store_true", help="Run browser in headful mode (for debugging)")

    args = parser.parse_args()
    success = auto_login(
        account=args.account,
        country=args.country,
        interactive=not args.non_interactive,
        headless=not args.headful,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
