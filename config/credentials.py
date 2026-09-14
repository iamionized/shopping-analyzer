"""Credentials management for Lidl accounts."""

import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class AccountConfig:
    """Configuration data for a single Lidl account."""
    account: str
    email: str
    password: str
    countries: List[str] = field(default_factory=lambda: ["nl"])

    def has_country(self, country: str) -> bool:
        """Check if account targets the specified country."""
        return country.lower() in [c.lower() for c in self.countries]


def load_accounts(credentials_file: Optional[str] = None) -> List[AccountConfig]:
    """
    Load account credentials from accounts.json or environment variables.

    Args:
        credentials_file: Optional custom path to accounts JSON file.
                         Defaults to 'accounts.json' in current working directory.

    Returns:
        List[AccountConfig]: List of loaded and validated account configurations.
    """
    file_path = credentials_file or os.getenv("LIDL_ACCOUNTS_FILE", "accounts.json")
    accounts: List[AccountConfig] = []

    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        acc = _parse_account_dict(item)
                        if acc:
                            accounts.append(acc)
            elif isinstance(data, dict):
                # Handle dictionary format: {"user1": {"email": "...", "password": "...", "countries": [...]}}
                for acc_name, details in data.items():
                    if isinstance(details, dict):
                        details_copy = dict(details)
                        if "account" not in details_copy:
                            details_copy["account"] = acc_name
                        acc = _parse_account_dict(details_copy)
                        if acc:
                            accounts.append(acc)
        except Exception as e:
            print(f"⚠ Fehler beim Lesen der Anmeldedaten aus {file_path}: {e}")

    # Fallback to environment variables if no accounts loaded from file
    if not accounts and os.getenv("LIDL_EMAIL") and os.getenv("LIDL_PASSWORD"):
        acc_name = os.getenv("LIDL_ACCOUNT", "main").strip().lower()
        email = os.getenv("LIDL_EMAIL", "").strip()
        pwd = os.getenv("LIDL_PASSWORD", "").strip()
        countries_str = os.getenv("LIDL_COUNTRIES", "nl,de")
        countries = [c.strip().lower() for c in countries_str.split(",") if c.strip()]
        accounts.append(AccountConfig(account=acc_name, email=email, password=pwd, countries=countries))

    return accounts


def _parse_account_dict(data: Dict) -> Optional[AccountConfig]:
    """Parse and validate a dictionary into an AccountConfig."""
    account = str(data.get("account", "")).strip().lower()
    email = str(data.get("email", "")).strip()
    password = str(data.get("password", "")).strip()
    countries_raw = data.get("countries", ["nl"])

    if not email or not password:
        return None

    if not account:
        # Default account name from email prefix if omitted
        account = email.split("@")[0].lower()

    if isinstance(countries_raw, list):
        countries = [str(c).strip().lower() for c in countries_raw if str(c).strip()]
    elif isinstance(countries_raw, str):
        countries = [c.strip().lower() for c in countries_raw.split(",") if c.strip()]
    else:
        countries = ["nl"]

    if not countries:
        countries = ["nl"]

    return AccountConfig(account=account, email=email, password=password, countries=countries)


def get_account_config(account_name: str, credentials_file: Optional[str] = None) -> Optional[AccountConfig]:
    """
    Get configuration for a specific account by name.

    Args:
        account_name: Name of the account (case-insensitive).
        credentials_file: Optional custom path to accounts JSON file.

    Returns:
        Optional[AccountConfig]: Account configuration if found, else None.
    """
    accounts = load_accounts(credentials_file)
    target = account_name.strip().lower()
    for acc in accounts:
        if acc.account.lower() == target:
            return acc
    return None
