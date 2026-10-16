KOTN PUBLIC BID-LEVEL DATASET - ORIGINAL USERNAMES

Sources: User-collected KOTN auction HTML exported by the read-only research scraper.
Collection date: October 15, 2026. Records reflect bids before auction close.

Bids CSV (19,813 rows): bid_id, listing_id, bidder (public username), amount, created_at.
Listings CSV (14,877 rows): id, title, current_bid, current_bidder (public username), scheduled_end, is_closed, min_bid, last_seen, history_checked_at.

The username strings are preserved exactly as in the user's scraper exports.
Rows are observations, not verified identities; user handles do not establish automation, affiliation, collusion, or wrongdoing.
Timestamps are recorded to the second. Current leading bidders are NOT finalized winners.
The dataset is not exhaustive of all historical auctions, and two positive-bid listings lacked recovered histories in the prior analysis.
No session cookies, API tokens or account credentials are included in these CSV files.

Research calculations should use bid_id as the unique bid key and join bids.listing_id to listings.id.
