# FAA SDR CSV Template (ELI5)

## What Is This?

Think of this like giving the app a map to where FAA SDR CSV files live.

- The app needs a URL pattern (template) to fetch CSV files.
- The pattern must include `{year}` so the app can ask for 2024, 2025, etc.
- Without this, FAA SDR import can run but process 0 records.

## One-Line Goal

Set `FAA_SDR_CSV_URL_TEMPLATE` to a working CSV URL pattern and verify it returns real CSV.

---

## Step-by-Step (ELI5)

1. Find where your FAA SDR CSV files will live.
- Example places: S3 bucket, internal file server, static web host.
- You need one CSV per year (or at least the year you want to import now).

2. Make sure each file is reachable by URL.
- Test by opening the URL in browser.
- You should see CSV-like content (header line with commas), not an HTML web page.

3. Build the URL template string.
- Replace the year part with `{year}`.
- Example:
  - Real file: `https://data.example.com/faa-sdr/faa_sdr_2024.csv`
  - Template: `https://data.example.com/faa-sdr/faa_sdr_{year}.csv`

4. Put the template in environment config.
- Add to `.env` (or your runtime env):
- `FAA_SDR_CSV_URL_TEMPLATE=https://data.example.com/faa-sdr/faa_sdr_{year}.csv`

5. Quick preflight test (important).
- Replace year with a real one and verify response is CSV:
```bash
python - <<'PY'
import os, httpx
tpl = os.environ.get("FAA_SDR_CSV_URL_TEMPLATE", "")
url = tpl.format(year=2024)
r = httpx.get(url, timeout=30, follow_redirects=True)
print("status:", r.status_code)
print("content-type:", r.headers.get("content-type"))
head = (r.text or "").splitlines()[0] if (r.text or "") else ""
print("first-line:", head[:120])
print("looks-like-csv:", "," in head or "\t" in head)
PY
```

6. Run FAA SDR import for one year.
```bash
flask import-data faa-sdr --year 2024
```

7. Confirm records were actually processed.
- Check app logs / `ImportState` for `FAA_SDR`.
- `last_records_processed` should be `> 0`.

8. If it still shows 0, check these first.
- URL returns HTML (login page or website shell) instead of CSV.
- Wrong filename pattern in template.
- Year file does not exist for requested year.
- CSV has unexpected columns/format.

---

## Minimal Example You Can Copy

```env
FAA_SDR_CSV_URL_TEMPLATE=https://your-bucket.example.com/faa_sdr_{year}.csv
```

Then run:

```bash
flask import-data faa-sdr --year 2024
```

---

## Done Criteria

- `FAA_SDR_CSV_URL_TEMPLATE` is set.
- Preflight URL test says `looks-like-csv: True`.
- `flask import-data faa-sdr --year <year>` completes.
- `ImportState.last_records_processed` for `FAA_SDR` is greater than 0.
