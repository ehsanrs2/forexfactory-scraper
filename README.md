# ForexFactory Calendar Scraper

A powerful Python-based tool for scraping detailed economic events from [ForexFactory Calendar](https://www.forexfactory.com/calendar). It captures event data, including date, time, impact, currency, and more detailed specifications, and exports them to a CSV file for further analysis.

---

## 🚀 Features

- Scrapes events with detailed information like **Actual**, **Forecast**, and **Previous** values.
- Handles partial or full month ranges for scraping.
- Extracts details from expandable rows and formats them for easy CSV export.
- Includes timezone handling for accurate event timings.
- Debug-friendly with console outputs to track progress.

---

## 📋 Requirements

- **Python 3.7+**
- **Selenium** for web scraping.
- **undetected-chromedriver** for bypassing bot detection.
- **dateutil** for timezone and date handling.

Install dependencies using:

```bash
pip install undetected-chromedriver python-dateutil
```

---

## 🛠️ Usage

### Setup

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/forexfactory-scraper.git
   cd forexfactory-scraper
   ```
2. Ensure you have Google Chrome and the matching version of ChromeDriver installed.

### Running the Script

Set the desired date range and timezone, then run the script:

```bash
python forexfactory_scraper.py
```

Example: Scrape events for January 5, 2025:

```python
if __name__ == "__main__":
    tz = gettz("Asia/Tehran")
    start_dt = datetime(2025, 1, 5, tzinfo=tz)
    end_dt = datetime(2025, 1, 5, tzinfo=tz)

    scrape_range_with_details(
        start_date=start_dt,
        end_date=end_dt,
        output_csv="forex_factory_details.csv",
        tzname="Asia/Tehran"
    )
```

---

## 📂 Output

The script outputs a CSV file (`forex_factory_details.csv`) with the following columns:

| DateTime         | Currency | Impact | Event          | Actual | Forecast | Previous | Detail                                |
|------------------|----------|--------|----------------|--------|----------|----------|---------------------------------------|
| 2025-01-05T12:30 | USD      | High   | Nonfarm Payroll | 150K   | 170K     | 140K     | Speaker: Fed Chair | Notes: Detailed specs |

---

## 🧱 Future Enhancements

### 1️⃣ **Modular Architecture**
- **Goal:** Improve maintainability and scalability.
- **Plan:**
  - Split the script into modules like `detail_parser.py`, `url_builder.py`, and `csv_util.py`.
  - Separate business logic from Selenium interactions (e.g., a `forexfactory_selenium.py` module).

### 2️⃣ **Selenium Optimization**
- **Log Improvements:**
  - Replace `print()` with `logging` for configurable log levels (e.g., DEBUG, INFO).
- **Retry Logic:**
  - Add retries for timeout errors during table parsing.
- **Better Timeout Handling:**
  - Dynamically adjust WebDriverWait durations based on server response.

### 3️⃣ **Details Parsing**
- Streamline accordion handling for faster scraping.
- Enhance data parsing with more structured formats like JSON or database storage.

### 4️⃣ **Output Enhancements**
- Add support for multiple formats: `CSV`, `JSON`, or `XLSX`.
- Introduce escaping for special characters like `,` or `"` in CSV fields.

### 5️⃣ **Testing & CI/CD**
- Add **unit tests** for key functions like URL building and detail parsing.
- Implement **integration tests** for end-to-end validation.
- Set up automated CI/CD pipelines using **GitHub Actions**.

### 6️⃣ **Incremental Updates**
- Optimize for periodic scraping by only fetching new or updated events.
- Handle year transitions in date parsing seamlessly.

---

## 🎯 Summary

This project is a solid starting point for scraping and analyzing ForexFactory data. By following the outlined enhancements, the scraper can evolve into a robust, professional-grade tool suitable for larger-scale projects.

---

### 🌟 Contributing

Feel free to fork this repository and submit pull requests. Contributions to improve functionality, performance, or documentation are always welcome!

### 📝 License

This project is licensed under the MIT License. See the `LICENSE` file for details.

---

Happy scraping! 😊