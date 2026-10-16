# KOTN Auction Bid Data Analysis

Independent, reproducible analysis of publicly displayed bidding histories from King of the North Auction (KOTN).

**[Read the full HTML report](https://kotnanalysis-png.github.io/kotn-data-analysis/)** · [View the source data](data/)

> **Research status:** This is an observational analysis of bidding patterns. Rapid bidding, recurring bidder pairs, or unusual timing do **not** establish that a particular account uses a bot, that the auction operator is involved, or that misconduct occurred. The project is not affiliated with KOTN.

## Dataset (October 2026 snapshot)

| Measure | Result |
| --- | ---: |
| Catalogue listings | 14,877 |
| Listings with recovered bid histories | 8,208 |
| Individual bid records | 19,813 |
| Distinct bidder usernames | 2,194 |
| Bid timestamps covered | October 13–15, 2026 |
| Duplicate bid IDs in export | 0 |

These are **snapshot** counts, not a claim to represent all bids ever made. Auction outcomes were not finalized when the data was captured.

## Files

| File | Description |
| --- | --- |
| [`index.html`](index.html) | Full public-facing research report; serves as the GitHub Pages homepage |
| [`data/kotn_raw_bids_with_usernames.csv`](data/kotn_raw_bids_with_usernames.csv) | One row per bid: `bid_id`, `listing_id`, `bidder`, `amount`, `created_at` |
| [`data/kotn_raw_listings_with_usernames.csv`](data/kotn_raw_listings_with_usernames.csv) | Listing metadata and snapshot values, including title, leading bid, closing-time field, and last-seen timestamps |

To reproduce bidder statistics, group the bids file by `bidder`, sort each account's records by `created_at`, and calculate rolling 60-second windows and consecutive bid gaps. Join the two CSVs using `listing_id` (bids) = `id` (listings). The timestamps in the bid CSV are recorded at **one-second resolution**. They are not evidence of precise millisecond-level actions.

## Findings and interpretation

The data includes accounts submitting bids across many different items within short time windows, including cases of over 15 bids on distinct listings in a rolling minute. It also includes repeated competition between some account pairs. These are observations worth testing, not proof of automation, shill bidding, collusion, or ineffective enforcement. Bidding via a fast catalogue interface or high-volume purchasing can produce some similar patterns.

Same-listing counterbid response times should be analyzed separately from fast cross-listing bidding. The initial study observed very few responses from a different bidder within five seconds on the same listing. See the [full report](https://kotnanalysis-png.github.io/kotn-data-analysis/) for the methodology, figures, examples, and limitations.

## Limitations

- This is a bounded, partial collection from auctions visible at the time; it is not an audit of all platform activity.
- Account usernames are public-facing identifiers, **not verified identities**. Do not attempt to identify the people behind them.
- Current leading bidder does not mean final winner. Unavailable or subsequently changed listings may affect outcomes.
- Seller/operator affiliation, network activity, internal bot-detection measures, and enforcement actions cannot be determined from the exported records.
- Historical pages and closing-time displays may change. Preserve dated copies of any additional datasets and record collection methods.

## GitHub Pages setup

Publish from **Settings → Pages → Deploy from a branch → `main` → `/ (root)`**. The file `index.html` must be in the repository root. After successful deployment, visit:

https://kotnanalysis-png.github.io/kotn-data-analysis/

## Responsible use

This dataset is provided for independent review of publicly visible auction records. Avoid harassment or unsubstantiated accusations against named accounts. No authentication cookies, API tokens, or personal account credentials should be committed to this repository.
