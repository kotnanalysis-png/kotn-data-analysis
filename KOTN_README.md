## v2.2: Stop at first zero bid in high-bid order

This version uses `https://kotnauction.com/auctions/1389?order_by=bid_desc&per_page=90` by default. It scans subsequent pages (`page=2`, etc.) until the **first zero-bid listing**, then stops. It processes only positive-bid listings and keeps the same incremental comparison, bid-history refresh, SQLite deduplication, CSV exports and analysis.

```powershell
py .\kotn_scraper.py sync --auction-id 1389 --workers 3 --delay 3
```

For all active auctions instead:

```powershell
py .\kotn_scraper.py sync --auction-id 0 --workers 3 --delay 3
```

The early-stop shortcut is valid **only if KOTN returns listings sorted by decreasing bid**. The script verifies the order across pages and checks the selected sort menu when present; if invalid, it raises an error instead of silently skipping higher bids. `--within-hours` is ignored in v2.2 because TBD times are not trustworthy. Existing SQLite data is preserved.

**Note:** A zero-bid listing does not mean the database has no more historical bids. The stop only applies to this run's ordered catalogue scan. This scan is a snapshot and doesn't prove all previously seen listings are still active.

# KOTN Read-only Bid Research Collector

Collects public catalogue summaries and available per-listing bid histories. **Does not place bids, log in, reuse authentication tokens, or bypass access controls.** SQLite is the durable store, with CSV exports and a basic activity summary.

## Install (Windows PowerShell)

```powershell
py -m pip install requests beautifulsoup4
```

## Try the first two 90-item catalogue pages

```powershell
py .\kotn_scraper.py scan --start-page 1 --pages 2
py .\kotn_scraper.py histories --limit 30
py .\kotn_scraper.py analyze
py .\kotn_scraper.py export
```

This creates `kotn.sqlite`, `kotn_listings.csv`, and `kotn_bids.csv` in your working directory. `histories` processes records not yet checked and now **skips catalogue listings with a $0 current bid by default**. Use `--refresh` to revisit already collected records. Use `--include-zero` to also request zero-bid listings.

## Collect additional pages

```powershell
py .\kotn_scraper.py scan --start-page 3 --pages 10 --delay 4
py .\kotn_scraper.py histories --limit 100 --delay 4
```

The collector defaults to at least 3 seconds per request, serial requests, and retry backoff. It does not fetch or check robots.txt. It stops if login is required and does not use credentials or submit bids. Respect HTTP rate limits and site access restrictions.

## Import previously saved HTML without accessing the website

```powershell
py .\kotn_scraper.py import-html "saved-catalogue.html" "saved-listing.html"
```

**Caution:** The original HTML you saved while logged in includes API and CSRF tokens. Keep originals private; this scraper extracts only listing and bid data into its database, not the tokens.

## Data model

`listings` table: listing ID, title, current bid, leading bidder, scheduled end, open/closed state, last observation, history-checked time.

`bids` table: unique bid ID, listing ID, bidder username, amount, timestamp. BID IDs are deduplicated across page visits.

Bid history available to the public may disappear after closing, so collect while pages are accessible. A saved page snapshot cannot guarantee the history remains complete through final close. Some pages may show no historical bids even if items have ended.

The `analyze` output is exploratory and does **not** determine who operates a bot or prove shill bidding. Faster-than-human sequences should be examined with data completeness and timing uncertainty in mind.

## Skip $0 bid listings (default)

```powershell
py .\kotn_scraper.py histories --limit 15000
```

The limit now applies to eligible nonzero-bid listings, not every catalogue entry. To opt back into checking zero-bid listings:

```powershell
py .\kotn_scraper.py histories --limit 15000 --include-zero
```

The catalogue scan still saves zero-bid listings in the database; the history-request stage skips them. Listings that receive bids later can be picked up when you re-run `scan` followed by `histories`. Previously checked listings require `--refresh` to check again.

## Parallel history collection

Run one process only with `py .\kotn_scraper.py histories --limit 15000 --workers 15`. Do not launch 15 separate copies: this version shares one database writer, with parallel fetchers and a per-worker delay. If the server responds with 429/403, stop and lower `--workers`. Ctrl+C stops processing; committed results are preserved. Requests may finish out of listing-ID order.

## Incremental updates (v2)

Keep your existing `kotn.sqlite` in the same folder. Replace `kotn_scraper.py` with the v2 script, then run:

```powershell
py .\kotn_scraper.py sync --workers 3 --delay 3
```

`sync` rescans the current catalogue (90 entries/page) to detect new listings and changed leaders/prices. It collects individual histories **only** if: the listing has never been collected, it changed since its last history collection, the previous history needs a one-time baseline migration, or it is due for a periodic/near-close refresh. New bids use their unique bid ID, so previous records are not duplicated. After collection, the command rewrites the cumulative `kotn_bids.csv` and `kotn_listings.csv` and prints the same `analyze` output. `collection_runs` and `listing_observations` preserve per-run audit information in SQLite.

Run more frequently with `--stale-hours 24` or reduce work with `--stale-hours 0` (disables periodic catchup, **not** changes or final checks). To avoid refreshing many legacy listings on the first v2 run, use `--limit 500`; later calls will continue where eligible. For a very slow or rate-limited server, lower `--workers 1` and increase `--delay 5`.

**Important:** Old auctions no longer visible in the active catalogue are not revisited automatically. To capture final winners and bids, schedule a sync before auctions close and run again before the site removes their histories. The existing exporter replaces cumulative CSV exports; always commit the resulting CSV changes to Git if you want to preserve them publicly. SQLite and raw HTML should remain private, and do not publish API/CSRF tokens or credentials.

To update a public GitHub repo after review:

```powershell
git status --short
git add kotn_scraper.py kotn_bids.csv kotn_listings.csv
git commit -m "Update incremental auction bid dataset"
git push
```


## Closing-window incremental collection (v2.1)

For a daily run focused on auctions closing within the next 24 hours:

```powershell
py .\kotn_scraper.py sync --within-hours 24 --final-grace-hours 24 --workers 3 --delay 3
```

The scraper scans the `ending_asc` catalogue only until an entire page lies beyond the next 24 hours, then refreshes bid histories only for positive-bid listings closing within that window (including an optional 24-hour grace period after scheduled closing if still listed). The normal new/changed/stale comparison and deduplication still apply; exports and analysis run as before. Without `--within-hours`, v2's original broad incremental scan remains in effect.

**Important:** A single daily run can miss bids placed in the final hours if KOTN removes closed listings before the next run. For an accurate final-price investigation, run closer to the auction's end as well, or run every 12 hours. `--final-grace-hours` cannot recover listings that have already disappeared from the catalogue. The website's two-minute extensions can alter actual closing times; a scheduled end is not always a final end.

## v2.3 sorting compatibility

Some KOTN auction pages ignore `order_by=bid_desc` and return `Newly listed`.
The scraper now detects this and falls back to scanning all catalogue pages,
skipping zero-bid listings on each page. It stops at the first $0 only when
KOTN confirms high-to-low sorting and the actual bids stay in descending order.
This prevents loss of later positive-bid listings. You cannot reliably stop
at the first $0 when the site returns unsorted listings.

`py .\\kotn_scraper.py sync --auction-id 1389 --workers 3 --delay 3`


## v2.4 worker limit

Both `sync` and `histories` accept `--workers 1` through `--workers 15`. The per-worker minimum GET delay is 2 seconds, so 15 workers may produce relatively high combined traffic. Use `--workers 15 --delay 3` only if the site tolerates it; reduce concurrency on 429/403. The unsorted-catalogue fallback is unchanged.
