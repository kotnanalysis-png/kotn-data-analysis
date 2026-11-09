# KOTN v3.9, November 9 2026 | Complete-page audit

Source: `kotn_bids(8).csv`, `kotn_listings(8).csv`. Baseline: complete v3.8 light-theme release. New current sections added; prior sections retained in dated appendix, with empty orphaned containers removed.

Date cutoff: November 9, 2026 at 00:00 Toronto local time (today excluded). Four cohorts by *scheduled* closing date; not verified actual closure.

| Page | New sections | Previous sections retained | Empty legacy blocks removed | Tables | Result |
|---|---:|---:|---:|---:|---|
| activity.html | 2 | 3 | 2 | 2 | PASS  |
| auctions.html | 2 | 3 | 0 | 3 | PASS  |
| bidders.html | 2 | 3 | 0 | 4 | PASS  |
| categories.html | 2 | 3 | 2 | 4 | PASS  |
| chikit1616.html | 3 | 4 | 0 | 6 | PASS  |
| community.html | 2 | 3 | 0 | 2 | PASS  |
| competition.html | 2 | 4 | 0 | 4 | PASS  |
| financial.html | 3 | 4 | 0 | 3 | PASS  |
| history.html | 2 | 3 | 0 | 3 | PASS  |
| index.html | 4 | 5 | 1 | 4 | PASS  |
| methodology.html | 3 | 4 | 0 | 1 | PASS  |
| operations.html | 2 | 3 | 0 | 2 | PASS  |
| patterns.html | 3 | 4 | 0 | 4 | PASS  |
| quality.html | 2 | 3 | 0 | 1 | PASS  |
| rounds.html | 3 | 4 | 0 | 6 | PASS  |
| sequences.html | 2 | 3 | 0 | 3 | PASS  |

## Statistical reconciliation

- Full bid records: 154,322; completed days: 153,777; November 9 excluded: 545.
- Unique accounts: 7,473; listings with analyzed bids: 52,784.
- One-second cross-listing transitions: 2,833 / 137,214 (2.06%).
- Catalogue histories: 2,749 missing high bid, 0 below catalogue among positive-bid listings.
- `is_closed`=0 for every supplied listing. No actual wins, prices paid or final outcomes can be asserted.
- Retained older sections are archival, not recalculated. The v3.8 collection was not guaranteed to contain complete bid histories.
- Audit tests existence and content structure and referenced local files, not browser visual rendering or exact accuracy of platform source data.
