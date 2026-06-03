# Forex Factory Scraper

A robust and flexible web scraper for [Forex Factory](https://www.forexfactory.com/) calendar events. This tool uses Selenium and pandas to collect, update, and manage Forex Factory event data, with incremental scraping and optional detailed event information.

## Dataset

The main scraped CSV dataset is hosted on [Hugging Face](https://huggingface.co/datasets/Ehsanrs2/Forex_Factory_Calendar). The local `forex_factory_cache.csv` file is treated as generated/downloaded data and is intentionally ignored by git.

If you place `forex_factory_cache.csv` in the project root, the test suite will validate its basic schema without requiring a live scrape.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Dependencies](#dependencies)
- [Testing](#testing)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Incremental Scraping:** Only fetch new or updated events based on existing CSV data.
- **Detailed Event Information:** Optionally scrape detailed specifications for each event.
- **Flexible Date Range:** Specify custom date ranges for scraping.
- **Timezone Support:** Configure the timezone according to your preference.
- **Data Management with pandas:** Efficiently handle data merging and updates using pandas.
- **Error Handling:** Robust handling of common web scraping issues like stale elements and timeouts.
- **Command-Line Interface:** Easy-to-use CLI with configurable parameters.

## Installation

### Prerequisites

- **Python 3.12+**: The current test environment uses Python 3.12.
- **Google Chrome**: Required for live Selenium scraping.

### Step-by-Step Guide

1. **Clone the Repository**

   ```bash
   git clone https://github.com/yourusername/forexfactory_scraper.git
   cd forexfactory_scraper
   ```

2. **Create a Virtual Environment (Optional but Recommended)**

   ```bash
   python -m venv .venv
   ```

   - **Activate the Virtual Environment:**
     - **Windows:**
       ```bash
       .venv\Scripts\activate
       ```
     - **macOS/Linux:**
       ```bash
       source .venv/bin/activate
       ```

3. **Install Dependencies**

   Ensure you have `pip` updated:

   ```bash
   pip install --upgrade pip
   ```

   Install required packages:

   ```bash
   pip install -r requirements.txt
   ```

   For development and tests, install:

   ```bash
   pip install -r requirements-dev.txt
   ```

4. **Download WebDriver**

   The scraper uses `undetected-chromedriver` to handle dynamic content and bypass some scraping protections. No additional setup is required as `undetected-chromedriver` manages the ChromeDriver version automatically.

## Usage

The main script can be executed via the command line, allowing you to specify various parameters such as the date range, output CSV file, timezone, and whether to scrape detailed event information.

### Command-Line Arguments

- `--start`: **(Required)** Start date for scraping in `YYYY-MM-DD` format.
- `--end`: **(Required)** End date for scraping in `YYYY-MM-DD` format.
- `--csv`: **(Optional)** Output CSV file path. Default is `forex_factory_cache.csv`.
- `--tz`: **(Optional)** Timezone for event dates. Default is `Asia/Tehran`.
- `--details`: **(Optional)** Flag to enable scraping of detailed event information. If omitted, only basic event data is scraped.
- `--impact`: **(Optional)** Comma-separated impact filter, such as `high,medium`.
- `--keep-currencies`: **(Optional)** Space-separated currency filter, such as `USD EUR GBP`.

### Running the Scraper

Navigate to the project root directory and execute the script using Python:

```bash
python -m src.forexfactory.main --start YYYY-MM-DD --end YYYY-MM-DD [--csv OUTPUT_CSV] [--tz TIMEZONE] [--details]
```

The scraper reads the existing output CSV before scraping. Days that already exist in the CSV are skipped by incremental mode. When `--details` is enabled, days with missing detail values are refreshed.

### Examples

1. **Scrape Events from March 21, 2024, to March 25, 2024, Including Details**

   ```bash
   python -m src.forexfactory.main --start 2024-03-21 --end 2024-03-25 --csv forex_factory_cache.csv --tz Asia/Tehran --details
   ```

2. **Scrape Events from January 1, 2024, to January 31, 2024, Without Details**

   ```bash
   python -m src.forexfactory.main --start 2024-01-01 --end 2024-01-31 --csv january_events.csv --tz Asia/Tehran
   ```

3. **Scrape Events from February 15, 2024, to February 20, 2024, Saving to a Custom CSV File**

   ```bash
   python -m src.forexfactory.main --start 2024-02-15 --end 2024-02-20 --csv feb_events.csv --tz Asia/Tehran
   ```

## Dependencies

All dependencies are listed in `requirements.txt`. Key libraries include:

- [selenium](https://pypi.org/project/selenium/): For browser automation.
- [pandas](https://pandas.pydata.org/): For data manipulation and management.
- [undetected-chromedriver](https://pypi.org/project/undetected-chromedriver/): To bypass Selenium detection mechanisms.
- [python-dateutil](https://dateutil.readthedocs.io/en/stable/): For advanced date handling.

Install dependencies using:

```bash
pip install -r requirements.txt
```

Install test dependencies using:

```bash
pip install -r requirements-dev.txt
```

## Testing

Run the normal test suite with:

```bash
python -m pytest -q
```

The normal suite does not run a live Selenium scrape. If `forex_factory_cache.csv` exists in the project root, the integration test validates the cached dataset schema.

To run the live scrape integration test, set `RUN_LIVE_SCRAPE=1`:

```bash
RUN_LIVE_SCRAPE=1 python -m pytest -q tests/integration/test_full_scrape.py
```

## Examples

### Scraping with Details

```bash
python -m src.forexfactory.main --start 2024-03-21 --end 2024-03-25 --csv forex_factory_cache.csv --tz Asia/Tehran --details

```

This command scrapes Forex Factory events from March 21, 2024, to March 25, 2024, including detailed specifications for each event, and saves the data to `forex_factory_cache.csv` with Tehran timezone.

### Scraping without Details

```bash
python -m src.forexfactory.main --start 2024-03-21 --end 2024-03-25 --csv forex_factory_cache.csv --tz Asia/Tehran
```

This command performs the same scraping without fetching detailed event specifications, resulting in a faster scraping process.

## Troubleshooting

### Common Issues and Solutions

1. **`StaleElementReferenceException` Errors**

   **Cause:** The web page's DOM has changed, making the reference to the web element invalid.

   **Solution:**
   - Increase the wait time using `WebDriverWait`.
   - Re-fetch the web element after certain actions.
   - Implement retry mechanisms.

2. **CAPTCHA or Cloudflare Challenges**

   **Cause:** Forex Factory may employ CAPTCHA or Cloudflare protection to prevent automated scraping.

   **Solution:**
   - Use `undetected-chromedriver` to bypass some protections.
   - Implement delays between requests to mimic human behavior.
   - Use proxies if necessary.
   - Be mindful of the scraping rate to avoid IP bans.

3. **Incorrect Date Parsing**

   **Cause:** Mismatch between the date format in the CSV and the expected format in the script.

   **Solution:**
   - Ensure that dates in the CSV are in ISO format (`YYYY-MM-DDTHH:MM:SS+TZ`).
   - Verify that the CSV contains the expected columns: `DateTime`, `Currency`, `Impact`, `Event`, `Actual`, `Forecast`, `Previous`, and `Detail`.

4. **Missing or Incorrect XPath Selectors**

   **Cause:** Changes in the Forex Factory website structure leading to incorrect XPath selectors.

   **Solution:**
   - Verify the current structure of the Forex Factory website.
   - Update XPath selectors in the scraper accordingly.

5. **Browser Driver Issues**

   **Cause:** Incompatible or outdated ChromeDriver versions.

   **Solution:**
   - Ensure that `undetected-chromedriver` is up to date.
   - Verify that Google Chrome is updated to the latest version.

### Viewing Logs

Logs provide detailed information about the scraping process and can help identify issues.

- **Info Logs:** Provide general information about the scraping progress.
- **Warning Logs:** Indicate non-critical issues that do not stop the scraper.
- **Error Logs:** Highlight critical issues that may require attention.

Ensure that your terminal or log files capture these logs for effective debugging.

## Contributing

Contributions are welcome! If you encounter bugs or have suggestions for improvements, feel free to open an issue or submit a pull request.

### Steps to Contribute

1. **Fork the Repository**

2. **Create a Feature Branch**

   ```bash
   git checkout -b feature/YourFeatureName
   ```

3. **Commit Your Changes**

   ```bash
   git commit -m "Add your message here"
   ```

4. **Push to the Branch**

   ```bash
   git push origin feature/YourFeatureName
   ```

5. **Open a Pull Request**

   Provide a clear description of your changes and the problem they solve.

## License

This project is licensed under the [MIT License](LICENSE).

---

**Disclaimer:** This scraper is intended for personal use and educational purposes only. Ensure compliance with Forex Factory's [Terms of Service](https://www.forexfactory.com/disclaimer) and avoid violating any usage policies. Use responsibly.
