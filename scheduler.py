"""Weekly scheduler for Lidl receipt data refresh and automatic cookie renewal."""

import argparse
import os
import signal
import sys
import time
from datetime import datetime
from typing import Optional

import schedule

from config import LidlConfig, load_accounts
from auth import auto_login, load_cookies_from_file, test_api_connection
from workflows import update_data


RUNNING = True


def signal_handler(signum, frame):
    """Handle termination signals gracefully."""
    global RUNNING
    print(f"\n[Scheduler] Signal {signum} empfangen. Fahre Scheduler herunter...")
    RUNNING = False


def refresh_account_data(
    account: str,
    country: str,
    email: Optional[str] = None,
    password: Optional[str] = None,
    force_login: bool = False,
) -> bool:
    """
    Check cookie validity, auto-login if needed, and execute update workflow.

    Args:
        account: Account identifier.
        country: Country code.
        email: Optional account email.
        password: Optional account password.
        force_login: If True, bypass validity check and force new login.

    Returns:
        bool: True if process succeeded, False otherwise.
    """
    account = account.strip().lower()
    country = country.strip().lower()
    cookie_file = f"lidl_cookies_{country}_{account}.json"
    receipts_file = f"lidl_receipts_{country}_{account}.json"

    print(f"\n{'=' * 60}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starte Aktualisierung für '{account}' ({country.upper()})")
    print(f"{'=' * 60}")

    LidlConfig.set_country(country)
    LidlConfig.set_account(account)

    cookies_valid = False

    if not force_login and os.path.exists(cookie_file):
        print(f"[Scheduler] Prüfe vorhandene Cookies in '{cookie_file}'...")
        session = load_cookies_from_file(cookie_file)
        if session:
            cookies_valid = test_api_connection(session)
            if cookies_valid:
                print(f"✓ [Scheduler] Vorhandene Cookies sind noch gültig.")
            else:
                print(f"⚠ [Scheduler] Cookies abgelaufen oder ungültig.")
        else:
            print(f"⚠ [Scheduler] Konnte Cookies aus '{cookie_file}' nicht laden.")
    else:
        print(f"[Scheduler] Keine bestehenden Cookies gefunden oder Login erzwungen.")

    # Refresh cookies via auto-login if invalid
    if not cookies_valid:
        print(f"[Scheduler] Starte automatischen Login für '{account}' ({country.upper()})...")
        login_success = auto_login(
            account=account,
            country=country,
            email=email,
            password=password,
            interactive=False,  # Headless background execution
            headless=True,
            cookie_file=cookie_file,
        )
        if not login_success:
            print(f"✗ [Scheduler] Automatischer Login für '{account}' ({country.upper()}) fehlgeschlagen!")
            return False

    # Execute update workflow from get_data.py
    print(f"[Scheduler] Starte Kassenbon-Update für '{account}' ({country.upper()})...")
    try:
        update_success = update_data(auth_method="file", cookies_file=cookie_file)
        if update_success:
            print(f"✓ [Scheduler] Kassenbon-Update für '{account}' ({country.upper()}) erfolgreich abgeschlossen!")
            return True
        else:
            print(f"✗ [Scheduler] Kassenbon-Update für '{account}' ({country.upper()}) fehlgeschlagen.")
            return False
    except Exception as ex:
        print(f"✗ [Scheduler] Fehler während des Updates für '{account}' ({country.upper()}): {ex}")
        return False


def run_weekly_job(
    account_filter: Optional[str] = None,
    country_filter: Optional[str] = None,
    force_login: bool = False,
) -> None:
    """
    Iterate over all configured accounts and countries to verify cookies and update receipts.
    """
    print(f"\n============================================================")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Wöchentlicher Aktualisierungsjob gestartet")
    print(f"============================================================")

    accounts = load_accounts()
    if not accounts:
        print("✗ [Scheduler] Keine Konten in 'accounts.json' oder Umgebungsvariablen konfiguriert!")
        return

    total_tasks = 0
    successful_tasks = 0

    for acc in accounts:
        if account_filter and acc.account.lower() != account_filter.lower():
            continue

        for country in acc.countries:
            if country_filter and country.lower() != country_filter.lower():
                continue

            total_tasks += 1
            ok = refresh_account_data(
                account=acc.account,
                country=country,
                email=acc.email,
                password=acc.password,
                force_login=force_login,
            )
            if ok:
                successful_tasks += 1

            # Brief delay between accounts
            time.sleep(2)

    print(f"\n============================================================")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Job abgeschlossen: {successful_tasks}/{total_tasks} erfolgreich.")
    print(f"============================================================\n")


def start_scheduler(
    day_of_week: str = "sunday",
    scheduled_time: str = "03:00",
    run_now: bool = False,
    account_filter: Optional[str] = None,
    country_filter: Optional[str] = None,
) -> None:
    """
    Configure and run the background scheduler loop.
    """
    global RUNNING
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    job_func = lambda: run_weekly_job(account_filter, country_filter)

    # Configure weekly schedule
    schedule_day = day_of_week.lower()
    scheduler_map = {
        "monday": schedule.every().monday,
        "tuesday": schedule.every().tuesday,
        "wednesday": schedule.every().wednesday,
        "thursday": schedule.every().thursday,
        "friday": schedule.every().friday,
        "saturday": schedule.every().saturday,
        "sunday": schedule.every().sunday,
    }

    sched_builder = scheduler_map.get(schedule_day, schedule.every().sunday)
    sched_builder.at(scheduled_time).do(job_func)

    print(f"[Scheduler] Hintergrund-Scheduler initialisiert:")
    print(f"  - Ausführung: Jeden {schedule_day.capitalize()} um {scheduled_time} Uhr")
    next_run = schedule.next_run()
    if next_run:
        print(f"  - Nächster geplanter Lauf: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")

    if run_now:
        print("[Scheduler] Option '--run-now' angegeben. Führe sofortigen Durchlauf aus...")
        job_func()

    print("[Scheduler] Warte auf geplante Ausführungen (Beenden mit Ctrl+C)...")
    while RUNNING:
        schedule.run_pending()
        time.sleep(10)

    print("[Scheduler] Scheduler beendet.")


def main():
    parser = argparse.ArgumentParser(description="Lidl Shopping Analyzer Background Scheduler")
    parser.add_argument("--run-now", action="store_true", help="Execute the update job immediately on startup")
    parser.add_argument("--once", action="store_true", help="Execute the update job once immediately and exit")
    parser.add_argument("--force-login", action="store_true", help="Force new login even if cookies appear valid")
    parser.add_argument("--account", "-a", help="Limit execution to a specific account name")
    parser.add_argument("--country", "-c", help="Limit execution to a specific country code")
    parser.add_argument(
        "--day",
        default=os.getenv("SCHEDULE_DAY", "sunday"),
        help="Day of the week to run weekly job (default: sunday)",
    )
    parser.add_argument(
        "--time",
        default=os.getenv("SCHEDULE_TIME", "03:00"),
        help="Time of the day (HH:MM) to run weekly job (default: 03:00)",
    )

    args = parser.parse_args()

    if args.once:
        run_weekly_job(
            account_filter=args.account,
            country_filter=args.country,
            force_login=args.force_login,
        )
        sys.exit(0)

    start_scheduler(
        day_of_week=args.day,
        scheduled_time=args.time,
        run_now=args.run_now,
        account_filter=args.account,
        country_filter=args.country,
    )


if __name__ == "__main__":
    main()
