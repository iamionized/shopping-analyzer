"""Configuration constants for Lidl API integration."""

class LidlConfig:
    """Configuration constants for Lidl API integration."""

    # Country and Account settings
    COUNTRY = "de"
    ACCOUNT = "main"

    # File paths
    RECEIPTS_JSON_FILE = f"lidl_receipts_{COUNTRY}_{ACCOUNT}.json"
    COOKIES_JSON_FILE = f"lidl_cookies_{COUNTRY}_{ACCOUNT}.json"

    # Request settings
    DEFAULT_TIMEOUT = 15
    REQUEST_DELAY = 0.5
    PAGES_TO_CHECK = 3

    # Browser settings
    SUPPORTED_BROWSERS = {"firefox": "Firefox", "chrome": "Chrome", "chromium": "Chromium"}

    # API settings
    DEFAULT_PAGE_SIZE = 10

    @classmethod
    def get_base_url(cls) -> str:
        """Get the base URL for the current country."""
        return f"https://www.lidl.{cls.COUNTRY}"

    @classmethod
    def get_tickets_url(cls) -> str:
        """Get the tickets API URL."""
        return f"{cls.get_base_url()}/mre/api/v1/tickets"

    @classmethod
    def get_receipt_url(cls, receipt_id: str) -> str:
        """Get the receipt API URL for a specific receipt."""
        return f"{cls.get_base_url()}/mre/api/v1/tickets/{receipt_id}"

    @classmethod
    def get_country_code(cls) -> str:
        """Get the country code in uppercase (e.g., 'DE', 'BG')."""
        return cls.COUNTRY.upper()

    @classmethod
    def get_language_code(cls) -> str:
        """Get the language code (e.g., 'de-DE', 'bg-BG')."""
        return f"{cls.COUNTRY}-{cls.COUNTRY.upper()}"

    @classmethod
    def get_cookie_domain(cls) -> str:
        """Get the domain for cookie extraction (e.g., 'lidl.de', 'lidl.bg')."""
        return f"lidl.{cls.COUNTRY}"

    @classmethod
    def _update_file_paths(cls) -> None:
        cls.RECEIPTS_JSON_FILE = f"lidl_receipts_{cls.COUNTRY}_{cls.ACCOUNT}.json"
        cls.COOKIES_JSON_FILE = f"lidl_cookies_{cls.COUNTRY}_{cls.ACCOUNT}.json"

    @classmethod
    def set_country(cls, country: str) -> None:
        """Set the country and update all derived settings."""
        if country:
            cls.COUNTRY = country.lower()
        cls._update_file_paths()

    @classmethod
    def set_account(cls, account: str) -> None:
        """Set the account and update all derived settings."""
        if account:
            cls.ACCOUNT = account.lower()
        cls._update_file_paths()
