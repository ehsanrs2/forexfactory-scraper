# Forex Factory Scraper

Reads the [Forex Factory](https://www.forexfactory.com/) economic calendar and uploads it to tmd-auth (`POST /api/calendar/econ/upload`), which serves it to the Calendar tab, the chart markers and the mobile app.

## How it works

1. [SeleniumBase](https://github.com/seleniumbase/SeleniumBase) opens Chrome in UC Mode, which gets past Cloudflare.
2. For each month it opens `calendar?month=oct.2026` and reads the event list Forex Factory embeds in the page (`window.calendarComponentStates`). Every event has a stable id, a Unix `dateline` (so times are UTC with no time zone guessing), actual, forecast, previous and revision.
3. The detail of each event (source, what it measures, usual effect, frequency, next release) comes from `/calendar/details/1-<id>`, fetched from inside the page. Details are cached in `cache/details.json`. A run fetches the detail of a new event, and refreshes it once a day only while the event is between 3 days ago and 14 days ahead, so the daily year run stays light.
4. Events are uploaded one month at a time as `{ source, from, to, events }`. tmd-auth writes each event by its Forex Factory id, removes the events in that window that Forex Factory no longer lists, and records revisions on the earlier release.

A run that cannot read a month uploads nothing, so a bad page never removes good data.

## Usage

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

| Command | What it does |
|---|---|
| `venv/bin/python run.py --window` | This month and next month. The regular run. |
| `venv/bin/python run.py --year 2026` | A whole year. Used for the first fill and once a day. |
| `venv/bin/python run.py --range 2026-10-13 2026-10-15` | Any dates, both included. |
| `--no-details` | Skip the detail of each event. |
| `--dry-run out.json` | Write what would be uploaded to a file instead of uploading. |

`run.py` reads `ECON_UPLOAD_URL` (for example `https://host/api`) and `ECON_UPLOAD_SECRET` from `.env` or `.env.local` beside it, or from the environment.

## Tests

```bash
venv/bin/python -m unittest discover -s tests -t .
```

## Server setup (Ubuntu 24.04, x86_64)

Run as the user that owns the cron (root on `cron-bot-forex`), from `/root/forexfactory-scraper`.

1. Chrome and a virtual display:

   ```bash
   wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
   apt install -y ./google-chrome-stable_current_amd64.deb python3-venv xvfb
   rm google-chrome-stable_current_amd64.deb
   ```

2. Code and packages:

   ```bash
   git pull
   mv venv venv-old
   python3 -m venv venv
   venv/bin/pip install -r requirements.txt
   ```

3. Check `.env` still has `ECON_UPLOAD_URL` and `ECON_UPLOAD_SECRET`.

4. Try it without uploading:

   ```bash
   venv/bin/python run.py --window --dry-run /tmp/ff-check.json
   ```

5. Once tmd-auth with the window upload is deployed, fill the year:

   ```bash
   venv/bin/python run.py --year 2026
   ```

6. Replace the old cron line (`crontab -e`):

   ```cron
   */15 * * * * flock -n /tmp/ff-scraper.lock /root/forexfactory-scraper/venv/bin/python /root/forexfactory-scraper/run.py --window >> /root/forexfactory-scraper/actuals.log 2>&1
   30 3 * * * flock -w 900 /tmp/ff-scraper.lock /root/forexfactory-scraper/venv/bin/python /root/forexfactory-scraper/run.py --year $(date +\%Y) >> /root/forexfactory-scraper/actuals.log 2>&1
   ```

   `flock -n` skips a run while the previous one is still going. The daily year run waits up to 15 minutes for it instead.

7. Keep a week of logs in `/etc/logrotate.d/forexfactory-scraper`:

   ```
   /root/forexfactory-scraper/actuals.log {
       daily
       rotate 7
       compress
       missingok
       notifempty
       copytruncate
   }
   ```

## Deploy order

1. tmd-auth first. It still accepts the old upload, so the old cron keeps working until step 2.
2. This scraper on the server, steps 1 to 5 above.
3. The new cron lines.

## Local runs on Apple Silicon

SeleniumBase runs its UC driver as an Intel binary on Apple Silicon, so the Mac needs Rosetta 2. Linux servers do not.

## License

This project is licensed under the [MIT License](LICENSE).

**Disclaimer:** For personal and educational use only. Ensure compliance with Forex Factory's [Terms of Service](https://www.forexfactory.com/disclaimer).
