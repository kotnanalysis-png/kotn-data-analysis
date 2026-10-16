#!/usr/bin/env python3
"""Read-only KOTN catalogue and bid-history collector.

Dependencies: requests, beautifulsoup4
No login, token reuse, bid submission, or account interaction.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import csv
import json
import logging
import random
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlencode, urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE = "https://kotnauction.com"
AGENT = "KOTN-ReadOnly-Research/1.0 (personal auction-bid analysis)"
LOG = logging.getLogger("kotn")


def embedded_var(html: str, name: str):
    # Only decode the JSON literal assigned to the named variable.
    match = re.search(r"\bvar\s+" + re.escape(name) + r"\s*=\s*", html)
    if not match:
        return None
    try:
        return json.JSONDecoder().raw_decode(html[match.end():].lstrip())[0]
    except json.JSONDecodeError as exc:
        LOG.warning("Invalid embedded JSON in %s: %s", name, exc)
        return None


def parse_catalogue(html: str):
    data = embedded_var(html, "listingData") or {}
    soup = BeautifulSoup(html, "html.parser")
    titles = {}
    for tile in soup.select(".listing-tile[data-id]"):
        id_ = tile.get("data-id")
        a = tile.select_one(".listing-tile-title-link")
        if id_ and a:
            titles[id_] = a.get_text(" ", strip=True)
    rows = []
    for id_, state in data.items():
        if not str(id_).isdigit() or not isinstance(state, dict):
            continue
        rows.append({"id": int(id_), "title": titles.get(str(id_), ""),
                     "current_bid": state.get("bid"), "current_bidder": state.get("bidder") or None,
                     "scheduled_end": state.get("end"), "is_closed": int(bool(state.get("is_closed"))),
                     "min_bid": state.get("minimum_bid")})
    return rows


def parse_listing(html: str):
    listing = embedded_var(html, "listing") or {}
    state = embedded_var(html, "listingStateBootstrap") or {}
    listing_id = listing.get("id")
    state_data = (state.get("listings") or {}).get(str(listing_id), {}) if listing_id is not None else {}
    bids = embedded_var(html, "initialBids")
    if bids is None:
        bids = state_data.get("bid_history") or []
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.select_one(".listing-content h1")
    title = h1.get_text(" ", strip=True) if h1 else ""
    if listing_id is None:
        m = re.search(r'listing-id="(\d+)"', html)
        listing_id = int(m.group(1)) if m else None
    if listing_id is None:
        return None, []
    row = {"id": int(listing_id), "title": title,
           "current_bid": state_data.get("current_bid"),
           "current_bidder": state_data.get("current_bidder"),
           "scheduled_end": listing.get("end_for_display"),
           "is_closed": int(bool(state_data.get("is_closed") or listing.get("closed_at"))),
           "min_bid": listing.get("minimum_bid")}
    out = []
    for b in bids:
        bid_id = b.get("id")
        if bid_id is None:
            continue
        out.append({"bid_id": int(bid_id), "listing_id": int(listing_id),
                    "bidder": b.get("bidder"), "amount": b.get("bid", b.get("amount")),
                    "created_at": b.get("created_at", b.get("created_at_iso"))})
    return row, out


def db_open(path):
    db = sqlite3.connect(path)
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS listings (
      id INTEGER PRIMARY KEY, title TEXT, current_bid REAL, current_bidder TEXT,
      scheduled_end TEXT, is_closed INTEGER, min_bid REAL, last_seen TEXT,
      history_checked_at TEXT);
    CREATE TABLE IF NOT EXISTS bids (
      bid_id INTEGER PRIMARY KEY, listing_id INTEGER NOT NULL,
      bidder TEXT, amount REAL, created_at TEXT,
      FOREIGN KEY(listing_id) REFERENCES listings(id));
    CREATE INDEX IF NOT EXISTS idx_bids_bidder_time ON bids(bidder, created_at);
    CREATE INDEX IF NOT EXISTS idx_bids_listing_time ON bids(listing_id, created_at);
    """)
    # Additive migration: safe with the original database and already-collected bids.
    for sql in (
        "ALTER TABLE listings ADD COLUMN history_bid_count INTEGER",
        "ALTER TABLE listings ADD COLUMN history_high_bid_id INTEGER",
        "ALTER TABLE listings ADD COLUMN history_current_bid REAL",
        "ALTER TABLE listings ADD COLUMN history_current_bidder TEXT",
        "ALTER TABLE listings ADD COLUMN last_catalogue_run INTEGER",
        "ALTER TABLE listings ADD COLUMN final_checked_at TEXT",
    ):
        try:
            db.execute(sql)
        except sqlite3.OperationalError as exc:
            if "duplicate column name" not in str(exc).lower():
                raise
    db.executescript("""
    CREATE TABLE IF NOT EXISTS collection_runs (
        run_id INTEGER PRIMARY KEY AUTOINCREMENT, started_at TEXT NOT NULL,
        finished_at TEXT, status TEXT, pages_scanned INTEGER DEFAULT 0,
        catalogue_records INTEGER DEFAULT 0, checked_histories INTEGER DEFAULT 0,
        new_bids INTEGER DEFAULT 0, error_count INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS listing_observations (
        run_id INTEGER NOT NULL, listing_id INTEGER NOT NULL, seen_at TEXT NOT NULL,
        current_bid REAL, current_bidder TEXT, is_closed INTEGER,
        PRIMARY KEY(run_id, listing_id)
    );
    CREATE INDEX IF NOT EXISTS idx_listing_observations_listing ON listing_observations(listing_id, run_id);
    """)
    db.commit()
    return db


def upsert_listing(db, x, history=False):
    now = datetime.now(timezone.utc).isoformat()
    db.execute("""INSERT INTO listings
        (id,title,current_bid,current_bidder,scheduled_end,is_closed,min_bid,last_seen,history_checked_at)
        VALUES (?,?,?,?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET
          title=CASE WHEN excluded.title != '' THEN excluded.title ELSE listings.title END,
          current_bid=COALESCE(excluded.current_bid, listings.current_bid),
          current_bidder=excluded.current_bidder,
          scheduled_end=COALESCE(excluded.scheduled_end,listings.scheduled_end),
          is_closed=excluded.is_closed,
          min_bid=COALESCE(excluded.min_bid,listings.min_bid),
          last_seen=excluded.last_seen,
          history_checked_at=COALESCE(excluded.history_checked_at,listings.history_checked_at)
       """, (x["id"], x["title"], x["current_bid"], x["current_bidder"],
              x["scheduled_end"], x["is_closed"], x["min_bid"], now, now if history else None))


def save_bids(db, bids):
    db.executemany("""INSERT INTO bids(bid_id,listing_id,bidder,amount,created_at)
        VALUES (:bid_id,:listing_id,:bidder,:amount,:created_at)
        ON CONFLICT(bid_id) DO UPDATE SET
          bidder=excluded.bidder, amount=excluded.amount, created_at=excluded.created_at""", bids)


class Fetcher:
    def __init__(self, delay):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": AGENT, "Accept": "text/html"})
        retry = Retry(total=3, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504],
                      allowed_methods=["GET"], respect_retry_after_header=True)
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self.delay = max(2.0, delay)
        self.last = 0

    def get(self, path, params=None):
        url = BASE + path
        if params:
            url += "?" + urlencode(params)
        wait = self.delay + random.uniform(0, 0.7) - (time.monotonic() - self.last)
        if wait > 0:
            time.sleep(wait)
        self.last = time.monotonic()
        resp = self.session.get(url, timeout=30, allow_redirects=True)
        if urlparse(resp.url).hostname != "kotnauction.com":
            raise RuntimeError("Unexpected redirect outside KOTN")
        if resp.status_code in (401, 403, 429):
            raise RuntimeError(f"HTTP {resp.status_code}: access denied/rate limited; stopped")
        resp.raise_for_status()
        if "login" in urlparse(resp.url).path and path != "/login":
            raise RuntimeError("Login required; refusing to scrape behind authentication")
        return resp.text


def cmd_scan(a, db):
    fetch = Fetcher(a.delay)
    total = 0
    for page in range(a.start_page, a.start_page + a.pages):
        html = fetch.get("/auctions/all", {"order_by": "ending_asc", "per_page": 90, "page": page})
        rows = parse_catalogue(html)
        if not rows:
            LOG.warning("No embedded listingData on page %d; stopping", page)
            break
        with db:
            for x in rows:
                upsert_listing(db, x)
        total += len(rows)
        print(f"Page {page}: {len(rows)} listings; {total} seen")
    print(f"Saved {total} catalogue entries (deduplicated in database)")


def cmd_histories(a, db):
    conditions = []
    if not a.refresh:
        conditions.append("history_checked_at IS NULL")
    if not a.include_zero:
        conditions.append("COALESCE(current_bid, 0) > 0")
    clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    ids = [r[0] for r in db.execute(
        f"SELECT id FROM listings {clause} ORDER BY id LIMIT ?", (a.limit,))]
    skipped = db.execute(
        "SELECT COUNT(*) FROM listings WHERE COALESCE(current_bid, 0) <= 0"
    ).fetchone()[0]
    if not a.include_zero:
        print(f"Skipping {skipped} zero-bid listings; fetching {len(ids)} eligible histories")

    worker_local = threading.local()

    def fetch_one(id_):
        if not hasattr(worker_local, "fetcher"):
            worker_local.fetcher = Fetcher(a.delay)
        html = worker_local.fetcher.get(f"/listings/{id_}")
        row, bids = parse_listing(html)
        return id_, row, bids

    completed = 0
    failed = 0
    # Workers only fetch/parse; the main thread alone writes to SQLite.
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        futures = {pool.submit(fetch_one, id_): id_ for id_ in ids}
        for future in as_completed(futures):
            id_ = futures[future]
            completed += 1
            try:
                _, row, bids = future.result()
                if not row:
                    failed += 1
                    LOG.warning("No structured listing available for %d", id_)
                    continue
                with db:
                    upsert_listing(db, row, history=True)
                    save_bids(db, bids)
                print(f"[{completed}/{len(ids)}] Listing {id_}: {len(bids)} historical bids", flush=True)
            except (requests.RequestException, RuntimeError, ValueError) as exc:
                failed += 1
                LOG.error("Failed listing %d: %s", id_, exc)
                if "429" in str(exc) or "403" in str(exc):
                    for pending in futures:
                        pending.cancel()
                    raise RuntimeError("KOTN rejected or rate-limited requests. Stop and reduce --workers.") from exc
    print(f"History collection finished; {completed - failed} saved; {failed} failed")

def cmd_import(a, db):
    for file in a.files:
        html = Path(file).read_text(encoding="utf-8", errors="replace")
        rows = parse_catalogue(html)
        row, bids = parse_listing(html)
        with db:
            for x in rows:
                upsert_listing(db, x)
            if row:
                upsert_listing(db, row, history=True)
                save_bids(db, bids)
        print(f"{file}: {len(rows)} catalogue entries; {len(bids)} bids" if row else
              f"{file}: {len(rows)} catalogue entries")


def _stamp():
    return datetime.now(timezone.utc).isoformat()


def _parse_end(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        # KOTN catalogue dates are Ontario local time; avoid mistaking them for UTC.
        if dt.tzinfo is None:
            from zoneinfo import ZoneInfo
            dt = dt.replace(tzinfo=ZoneInfo("America/Toronto"))
        return dt.astimezone(timezone.utc)
    except (ValueError, ImportError):
        return None


def cmd_sync(a, db):
    """Refresh catalogue, retrieve only new/changed/stale histories, then export and analyze."""
    started = _stamp()
    with db:
        cur = db.execute("INSERT INTO collection_runs(started_at,status) VALUES (?, 'running')", (started,))
        run_id = cur.lastrowid
    fetcher = Fetcher(a.delay)
    page_count = 0
    catalogue_count = 0
    checks = 0
    new_bids = 0
    errors = 0
    try:
        # A high-bid ordered auction catalogue allows an early exit at the FIRST
        # zero-bid listing.  Never assume the server honored the sorting request:
        # validate descending order (including across page boundaries) before
        # deciding that the remaining listings all have zero bids.
        previous_bid = float("inf")
        reached_zero = False
        sort_mode = None  # True only if the server really supplies bid-desc ordering
        warned_fallback = False
        for page in range(1, a.max_pages + 1):
            path = f"/auctions/{a.auction_id}" if a.auction_id else "/auctions/all"
            html = fetcher.get(path, {"order_by": "bid_desc", "per_page": 90, "page": page})
            # The catalogue page marks the active sort option. Some routes may
            # ignore order_by; do not apply the zero-bid shortcut in that case.
            soup = BeautifulSoup(html, "html.parser")
            selected_sorts = [a.get_text(" ", strip=True).lower()
                              for a in soup.select("a.dropdown-item.active")
                              if "order_by=" in (a.get("href") or "")]
            selected_high = any("bid (high to low)" in label for label in selected_sorts)
            if sort_mode is None:
                sort_mode = selected_high
            elif sort_mode and not selected_high:
                raise RuntimeError("Site stopped honouring bid-desc sorting mid-scan; refusing early cutoff")
            if not selected_high and not warned_fallback:
                print("KOTN did not honour bid_desc (selected: %s). "
                      "Switching to SAFE full-catalogue scan, ignoring $0 listings; "
                      "cannot stop at the first $0 without losing bids." % selected_sorts,
                      flush=True)
                warned_fallback = True
            rows = parse_catalogue(html)
            if not rows:
                if page == 1:
                    raise RuntimeError("No listingData on first page; check auction ID and page format")
                print(f"No listings on page {page}; catalogue scan finished.", flush=True)
                break

            eligible = []
            for row in rows:
                bid = float(row.get("current_bid") or 0)
                if sort_mode and bid > previous_bid:
                    raise RuntimeError(
                        f"Catalogue is not in descending bid order at page {page}, "
                        f"listing {row['id']} ({bid:g} after {previous_bid:g}). "
                        "Refusing to stop early because this could miss bids."
                    )
                previous_bid = bid
                if bid <= 0:
                    if sort_mode:
                        reached_zero = True
                        break
                    continue  # Unsorted catalogue: $0 is not the end of positive bids.
                eligible.append(row)

            # Validate remainder of page even after seeing zero: if sorting has
            # drifted, refuse early termination rather than silently lose data.
            if reached_zero:
                first_zero_index = len(eligible)
                for row in rows[first_zero_index + 1:]:
                    if float(row.get("current_bid") or 0) > 0:
                        raise RuntimeError(
                            "Positive bid found after zero bid on the same page; "
                            "site is not reliably sorted bid_desc."
                        )

            with db:
                for row in eligible:
                    upsert_listing(db, row)
                    db.execute("UPDATE listings SET last_catalogue_run=? WHERE id=?", (run_id, row["id"]))
                    db.execute("""INSERT OR REPLACE INTO listing_observations
                        (run_id,listing_id,seen_at,current_bid,current_bidder,is_closed)
                        VALUES(?,?,?,?,?,?)""", (run_id,row["id"],_stamp(),row["current_bid"],row["current_bidder"],row["is_closed"]))
            page_count += 1
            catalogue_count += len(eligible)
            print(f"Catalog page {page}: {len(eligible)} positive-bid listings", flush=True)
            if reached_zero:
                print(f"First $0 bid reached on page {page}; stopping catalogue scan.", flush=True)
                break
            if len(rows) < 90:
                break
        if page_count == 0:
            raise RuntimeError("No catalogue pages retrieved; cannot perform incremental sync")

        # Distinguish prior catalogue snapshot from the last successfully checked history.
        # This avoids skipping bid changes on listings we have already visited.
        cutoff = datetime.now(timezone.utc) - timedelta(hours=a.stale_hours)
        selected = []
        reasons = {}
        for (id_, current_bid, current_bidder, checked, history_bid, history_bidder,
             scheduled_end, closed, final_checked) in db.execute("""
            SELECT id,current_bid,current_bidder,history_checked_at,history_current_bid,
                   history_current_bidder,scheduled_end,is_closed,final_checked_at
            FROM listings WHERE last_catalogue_run=? AND COALESCE(current_bid,0)>0
            ORDER BY id""", (run_id,)):
            reason = None
            if checked is None:
                reason = "new history"
            elif history_bid is None:
                reason = "legacy history baseline"
            elif float(current_bid or 0) != float(history_bid or 0) or (current_bidder or "") != (history_bidder or ""):
                reason = "bid changed"
            else:
                checked_at = datetime.fromisoformat(checked.replace("Z", "+00:00"))
                if checked_at.tzinfo is None:
                    checked_at = checked_at.replace(tzinfo=timezone.utc)
                end = _parse_end(scheduled_end)
                now = datetime.now(timezone.utc)
                if end and now >= end and not final_checked:
                    reason = "final check"
                elif end and now < end <= now + timedelta(hours=a.closing_hours) and checked_at < cutoff:
                    reason = "closing soon"
                elif a.stale_hours > 0 and checked_at < cutoff:
                    reason = "stale"
            if reason:
                selected.append(id_)
                reasons[id_] = reason
        if a.limit > 0:
            selected = selected[:a.limit]
        print(f"Sync run {run_id}: {catalogue_count} observed listings; {len(selected)} histories to refresh", flush=True)

        worker_local = threading.local()
        def fetch_one(id_):
            if not hasattr(worker_local, "fetcher"):
                worker_local.fetcher = Fetcher(a.delay)
            row, bids = parse_listing(worker_local.fetcher.get(f"/listings/{id_}"))
            if not row:
                raise ValueError("No listing record")
            return row, bids

        if selected:
            with ThreadPoolExecutor(max_workers=a.workers) as pool:
                futures = {pool.submit(fetch_one, id_): id_ for id_ in selected}
                for index, future in enumerate(as_completed(futures), 1):
                    id_ = futures[future]
                    try:
                        row, bids = future.result()
                        before = db.total_changes
                        with db:
                            upsert_listing(db, row, history=True)
                            # Track insert count separately from updates, because bid IDs
                            # are stable and existing records are upserted.
                            known = set()
                            if bids:
                                wanted = [b['bid_id'] for b in bids]
                                for start in range(0, len(wanted), 800):
                                    chunk = wanted[start:start+800]
                                    marks = ','.join('?' for _ in chunk)
                                    known.update(r[0] for r in db.execute(f'SELECT bid_id FROM bids WHERE bid_id IN ({marks})', chunk))
                            save_bids(db, bids)
                            db.execute("""UPDATE listings SET history_bid_count=?, history_high_bid_id=?,
                                history_current_bid=?, history_current_bidder=?,
                                final_checked_at=CASE WHEN is_closed=1 THEN ? ELSE final_checked_at END
                                WHERE id=?""", (len(bids), max((b['bid_id'] for b in bids), default=None),
                                    row['current_bid'], row['current_bidder'], _stamp(), id_))
                        added = len(bids) - len(known)
                        new_bids += added
                        checks += 1
                        print(f"[{index}/{len(selected)}] {id_}: +{added} new bids ({len(bids)} total, {reasons[id_]})", flush=True)
                    except (requests.RequestException, RuntimeError, ValueError, sqlite3.Error) as exc:
                        errors += 1
                        LOG.error("Listing %d failed: %s", id_, exc)
                        if "429" in str(exc) or "403" in str(exc):
                            for pending in futures:
                                pending.cancel()
                            raise RuntimeError("Rate-limited or forbidden; stop collection and reduce workers") from exc
        with db:
            db.execute("""UPDATE collection_runs SET finished_at=?, status='complete',pages_scanned=?,
                catalogue_records=?,checked_histories=?,new_bids=?,error_count=? WHERE run_id=?""",
                       (_stamp(),page_count,catalogue_count,checks,new_bids,errors,run_id))
        print(f"SYNC COMPLETE: {checks} histories refreshed; {new_bids} new bids; {errors} errors", flush=True)
        if not a.no_export:
            cmd_export(argparse.Namespace(prefix=a.prefix), db)
            cmd_analyze(a,db)
    except Exception:
        with db:
            db.execute("""UPDATE collection_runs SET finished_at=?,status='failed',pages_scanned=?,
                catalogue_records=?,checked_histories=?,new_bids=?,error_count=? WHERE run_id=?""",
                       (_stamp(),page_count,catalogue_count,checks,new_bids,errors+1,run_id))
        raise


def cmd_export(a, db):
    prefix = Path(a.prefix)
    for table in ("listings", "bids"):
        cur = db.execute(f"SELECT * FROM {table}")
        file = prefix.with_name(prefix.name + "_" + table + ".csv")
        with file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([c[0] for c in cur.description])
            writer.writerows(cur)
        print(f"Wrote {file}")


def cmd_analyze(a, db):
    print("Most active bidders (observed bid history):")
    for row in db.execute("""SELECT bidder, COUNT(*) AS bids, COUNT(DISTINCT listing_id) AS listings
             FROM bids WHERE bidder IS NOT NULL GROUP BY bidder
             ORDER BY bids DESC LIMIT 20"""):
        print(f"  {row[0]:25} {row[1]:6} bids  {row[2]:5} listings")
    print("\nShortest cross-listing bid gaps (seconds; not proof of automation):")
    sql = """WITH timeline AS (
       SELECT bidder, listing_id, created_at,
         LAG(listing_id) OVER(PARTITION BY bidder ORDER BY created_at) AS prev_listing,
         LAG(created_at) OVER(PARTITION BY bidder ORDER BY created_at) AS prev_time
       FROM bids WHERE created_at IS NOT NULL AND bidder IS NOT NULL)
       SELECT bidder, COUNT(*) AS fast_pairs, MIN(delta) AS min_seconds FROM (
         SELECT bidder, (julianday(replace(substr(created_at,1,19),'T',' '))-
                    julianday(replace(substr(prev_time,1,19),'T',' ')))*86400 AS delta
         FROM timeline WHERE listing_id != prev_listing AND prev_time IS NOT NULL)
       WHERE delta BETWEEN 0 AND 5 GROUP BY bidder ORDER BY fast_pairs DESC LIMIT 20"""
    for user, count, seconds in db.execute(sql):
        print(f"  {user:25} {count:6} pairs  min {seconds:.1f}s")
    print("\nCaution: sample size, page coverage, manual multi-tab bidding, and time precision matter.")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default="kotn.sqlite", help="SQLite database path")
    sub = ap.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan", help="Collect live catalogue pages")
    scan.add_argument("--start-page", type=int, default=1)
    scan.add_argument("--pages", type=int, default=2)
    hist = sub.add_parser("histories", help="Collect individual bid histories for scanned listings")
    hist.add_argument("--limit", type=int, default=50)
    hist.add_argument("--workers", type=int, default=1, choices=range(1, 16), metavar="1-15", help="Concurrent read-only fetches; default 1, maximum 15")
    hist.add_argument("--refresh", action="store_true", help="Recheck already collected listings")
    hist.add_argument("--include-zero", action="store_true", help="Also fetch listings whose current bid is $0")
    imp = sub.add_parser("import-html", help="Import saved HTML pages without network access")
    imp.add_argument("files", nargs="+")
    exp = sub.add_parser("export", help="Export SQLite data to CSV")
    exp.add_argument("--prefix", default="kotn")
    sub.add_parser("analyze", help="Inspect observed bidder activity")
    sync = sub.add_parser("sync", help="Incrementally scan, refresh changed histories, export and analyze")
    sync.add_argument("--max-pages", type=int, default=250, help="Maximum catalogue pages; early $0 stop only if high-bid sorting is confirmed")
    sync.add_argument("--auction-id", type=int, default=1389, help="Auction ID (default: 1389); set 0 for all auctions")
    sync.add_argument("--workers", type=int, default=3, choices=range(1,16), metavar="1-15")
    sync.add_argument("--delay", type=float, default=3)
    sync.add_argument("--stale-hours", type=float, default=48, help="Revisit unchanged records after N hours; 0 disables")
    sync.add_argument("--closing-hours", type=float, default=12)
    sync.add_argument("--within-hours", type=float, default=0, help="Deprecated and ignored: sync now uses highest-bid ordering")
    sync.add_argument("--final-grace-hours", type=float, default=24, help="Include listings that closed up to N hours ago when using --within-hours")
    sync.add_argument("--limit", type=int, default=0, help="Max histories this run; 0 = all changed")
    sync.add_argument("--prefix", default="kotn")
    sync.add_argument("--no-export", action="store_true")
    for p in (scan, hist):
        p.add_argument("--delay", type=float, default=3, help="Minimum seconds between GET requests (>=2)")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    with db_open(args.db) as db:
        {"scan":cmd_scan,"histories":cmd_histories,"import-html":cmd_import,
         "export":cmd_export,"analyze":cmd_analyze,"sync":cmd_sync}[args.command](args, db)

if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, PermissionError, requests.RequestException) as exc:
        sys.exit(f"Stopped: {exc}")
