import logging
import os
import shutil
from dataclasses import dataclass
from typing import Literal

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService

logger = logging.getLogger(__name__)

DriverKind = Literal["selenium", "uc"]


class DriverStartupError(RuntimeError):
    """Raised when Chrome/ChromeDriver cannot be started with actionable context."""


@dataclass(frozen=True)
class DriverConfig:
    driver: DriverKind = "selenium"
    chrome_binary: str | None = None
    chromedriver: str | None = None
    headless: bool = False
    user_agent: str | None = None
    user_data_dir: str | None = None
    page_timeout: int = 120

    @classmethod
    def from_env(
        cls,
        *,
        driver: str | None = None,
        chrome_binary: str | None = None,
        chromedriver: str | None = None,
        headless: bool | None = None,
        user_agent: str | None = None,
        user_data_dir: str | None = None,
        page_timeout: int | None = None,
    ) -> "DriverConfig":
        env_driver = os.getenv("FOREXFACTORY_DRIVER")
        env_headless = os.getenv("FOREXFACTORY_HEADLESS")
        resolved_headless = headless
        if resolved_headless is None and env_headless is not None:
            resolved_headless = env_headless.strip().lower() in {"1", "true", "yes", "on"}

        return cls(
            driver=(driver or env_driver or "selenium").lower(),  # type: ignore[arg-type]
            chrome_binary=chrome_binary or os.getenv("FOREXFACTORY_CHROME_BINARY"),
            chromedriver=chromedriver or os.getenv("FOREXFACTORY_CHROMEDRIVER"),
            headless=bool(resolved_headless) if resolved_headless is not None else False,
            user_agent=user_agent or os.getenv("FOREXFACTORY_USER_AGENT"),
            user_data_dir=_expand_path(user_data_dir or os.getenv("FOREXFACTORY_USER_DATA_DIR")),
            page_timeout=page_timeout or int(os.getenv("FOREXFACTORY_PAGE_TIMEOUT", "120")),
        )


def _expand_path(path: str | None) -> str | None:
    if not path:
        return None
    return os.path.abspath(os.path.expandvars(os.path.expanduser(path)))


def _chrome_options(config: DriverConfig) -> ChromeOptions:
    options = ChromeOptions()
    if config.chrome_binary:
        options.binary_location = config.chrome_binary
    if config.headless:
        options.add_argument("--headless=new")
    if config.user_agent:
        options.add_argument(f"--user-agent={config.user_agent}")
    if config.user_data_dir:
        options.add_argument(f"--user-data-dir={config.user_data_dir}")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--lang=en-US")
    options.add_argument("--window-size=1400,1000")
    return options


def _resolve_chromedriver(path: str | None) -> str | None:
    if path:
        return path
    return shutil.which("chromedriver")


def _startup_help(config: DriverConfig, original: Exception) -> DriverStartupError:
    driver_hint = (
        "Install a ChromeDriver matching your Chrome/Chromium version and ensure it is on PATH, "
        "or pass --chromedriver /path/to/chromedriver. On Debian/Ubuntu try: "
        "sudo apt install chromium chromium-driver. On macOS with Homebrew try: "
        "brew install --cask google-chrome && brew install chromedriver."
    )
    binary_hint = "If Chrome/Chromium is not on the standard path, pass --chrome-binary /path/to/chrome."
    uc_hint = (
        "For --driver uc, this project requires a local ChromeDriver path as well; it will not let "
        "undetected_chromedriver download a driver at runtime."
    )
    message = (
        f"Could not start Chrome WebDriver using driver={config.driver!r}. {driver_hint} "
        f"{binary_hint} {uc_hint} Original error: {original}"
    )
    return DriverStartupError(message)


def create_chrome_driver(config: DriverConfig | None = None):
    config = config or DriverConfig.from_env()
    chromedriver_path = _resolve_chromedriver(config.chromedriver)

    if config.driver not in {"selenium", "uc"}:
        raise DriverStartupError("--driver must be either 'selenium' or 'uc'.")

    if not chromedriver_path:
        raise DriverStartupError(
            "ChromeDriver was not found locally. Install ChromeDriver and put it on PATH, "
            "or pass --chromedriver /path/to/chromedriver. Driver downloads are intentionally "
            "not performed at scraper runtime."
        )

    logger.info("Starting Chrome WebDriver with %s driver and ChromeDriver at %s", config.driver, chromedriver_path)
    try:
        if config.driver == "uc":
            import undetected_chromedriver as uc

            options = uc.ChromeOptions()
            selenium_options = _chrome_options(config)
            for arg in selenium_options.arguments:
                options.add_argument(arg)
            if config.chrome_binary:
                options.binary_location = config.chrome_binary
            return uc.Chrome(
                options=options,
                driver_executable_path=chromedriver_path,
                browser_executable_path=config.chrome_binary,
            )

        service = ChromeService(executable_path=chromedriver_path)
        return webdriver.Chrome(service=service, options=_chrome_options(config))
    except (WebDriverException, OSError, RuntimeError) as exc:
        raise _startup_help(config, exc) from exc
