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

Run one process only with `py .\kotn_scraper.py histories --limit 15000 --workers 10`. Do not launch ten separate copies: this version shares one database writer, with parallel fetchers and a per-worker delay. If the server responds with 429/403, stop and lower `--workers`. Ctrl+C stops processing; committed results are preserved. Requests may finish out of listing-ID order.
