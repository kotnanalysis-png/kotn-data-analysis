# I analyzed 19,813 King of the North Auction bids. The bot activity allegations deserve a closer look.

There have been multiple Reddit discussions over the years accusing King of the North Auction (KOTN) of allowing bidding bots.

Rather than relying on screenshots or speculation, I wrote a Python scraper to collect the actual bidding histories from KOTN's website.

**I collected 19,813 individual bids from 2,194 different usernames across 8,208 auction listings.**

The results raise some interesting questions about automated bidding and KOTN's enforcement of its own rules.

I've also made the underlying transaction-level data available so others can independently verify the findings.

## 1. The dataset

Collected October 15, 2026, covering bidding activity from October 13–15.

| Metric | Result |
|---|---:|
| Total auction listings | 14,877 |
| Listings with recovered bid histories | 8,208 |
| Individual bids | 19,813 |
| Unique bidder accounts | 2,194 |
| Duplicate bid IDs | 0 |
| Missing bid fields | 0 |
| Catalogue listings with bids but no recovered history | 2 |
| Timestamp precision | 1 second |

Every bid record contains a unique bid ID, auction listing ID, username, amount and timestamp.

The data was extracted from the bidding histories provided directly by KOTN's website.

No bids were placed during this investigation.

## 2. Some accounts are bidding on 15–21 different items per minute

I calculated each account's busiest rolling 60-second period using the individual transaction timestamps.

| Username | Total bids | Most bids in 60 seconds |
|---|---:|---:|
| chikit1616 | 409 | 21 |
| chanelbby | 122 | 20 |
| tinka | 329 | 20 |
| joepro | 31 | 19 |
| rdookie | 27 | 18 |
| whitneyhaz | 307 | 18 |
| akshar9 | 40 | 17 |

These bursts involved separate products, not multiple bids on one item.

**Twenty-one bids on 21 different auction items within 60 seconds works out to roughly one bid every three seconds.**

That doesn't automatically mean a bot was involved. Someone could potentially achieve these speeds through an optimized manual workflow.

But it is unusual enough to warrant examination, especially given KOTN's explicit prohibition against bidding bots and automated scripts.

## 3. A username identified in a 2024 Reddit investigation is still active

In November 2024, another Reddit user analyzed approximately 25,000 KOTN bids and raised concerns about `chikit1616`.

Original investigation:

https://www.reddit.com/r/barrie/comments/1gul090/

Nearly two years later, the same username appears in my dataset.

Here's what I found:

| Metric | chikit1616 |
|---|---:|
| Total bids | 409 |
| Unique listings | 211 |
| Median interval between bids | 6 seconds |
| Cross-listing bid transitions within 5 seconds | 200 |
| Maximum bids in 60 seconds | 21 |
| Listings currently leading | 147 |
| Percentage currently leading | 69.7% |

One actual sequence from October 14, 2026:

| Time | Listing | Bid amount |
|---|---|---:|
| 4:15:11 PM | 4313928 | $11 |
| 4:15:12 PM | 4314402 | $15 |
| 4:15:15 PM | 4313855 | $15 |
| 4:15:19 PM | 4313929 | $9 |
| 4:15:22 PM | 4295785 | $15 |
| 4:15:24 PM | 4313712 | $10 |
| 4:15:27 PM | 4316768 | $8 |
| 4:15:30 PM | 4313643 | $8 |

**Eight bids on eight different products in 19 seconds.**

The username is publicly displayed in KOTN's bidding history, and the listing IDs can be used to examine the individual auctions.

This isn't proof that `chikit1616` is automated. However, the persistence of unusually rapid activity from an account previously questioned publicly is worth investigating.

## 4. This isn't isolated to one account

Several other accounts also demonstrate repeated rapid bidding.

| Username | Total bids | Median interval | Cross-item gaps ≤5 seconds |
|---|---:|---:|---:|
| chikit1616 | 409 | 6 sec | 200 |
| whitneyhaz | 307 | 12.5 sec | 119 |
| tinka | 329 | 24 sec | 86 |
| libitsawati | 294 | 31 sec | 49 |
| blindbuzz | 276 | 27 sec | 49 |

That suggests the bidding pattern is broader than a single account.

Possible explanations include legitimate high-volume resellers, specialized bidding software, browser automation, or very efficient manual bidding.

The data alone cannot distinguish these possibilities conclusively.

## 5. I tested whether accounts instantly outbid other users

One of the more serious accusations is that bots immediately respond when regular customers place bids.

I reconstructed the bidding sequences within individual auctions and calculated the delay between bids from competing usernames.

Across 11,501 competing-bid transitions:

| Response time | Number | Percentage |
|---|---:|---:|
| Within 5 seconds | 5 | 0.04% |
| Within 30 seconds | 55 | 0.48% |

This is actually an important finding.

**The data does not support widespread instantaneous counterbidding.**

The unusual behaviour appears to be rapid bidding across many different items, rather than bots automatically responding to every competing customer.

That's a meaningful distinction when evaluating allegations of price manipulation.

## 6. Some accounts repeatedly bid against each other

I also examined accounts that repeatedly appeared on the same listings.

| Bidder pair | Shared listings |
|---|---:|
| blindbuzz / libitsawati | 20 |
| blindbuzz / whitneyhaz | 14 |
| chikit1616 / jay00funk | 13 |
| tinka / whitneyhaz | 12 |

Some pairs also exchanged multiple successive competing bids.

| Bidder pair | Alternating bid transitions |
|---|---:|
| antmansam / chikit1616 | 21 |
| chikit1616 / j007 | 20 |
| blindbuzz / libitsawati | 12 |
| chikit1616 / jay00funk | 12 |
| tinka / whitneyhaz | 12 |

This does not prove coordination. High-volume bidders targeting similar inventory are naturally more likely to compete against one another.

A proper collusion analysis would need to account for product preferences, total bidding volume and expected overlap.

## 7. The biggest question is KOTN's anti-bot enforcement

KOTN's terms explicitly prohibit unauthorized bots, automation tools and scripts from participating in auctions.

But the data shows multiple accounts placing bids across separate products at exceptionally high speeds.

One username raised in public discussions in 2024 is still exhibiting rapid bidding patterns in 2026.

That raises several questions:

1. Does KOTN have automated systems to identify suspicious bidding behaviour?
2. Does it investigate accounts regularly submitting 15–21 bids per minute across separate products?
3. How many accounts have been suspended for violating its automation policy?
4. Are certain forms of automated bidding permitted?
5. If reseller bidding software is being used, how does KOTN distinguish it from prohibited bots?

There are several possible explanations.

KOTN may not detect automated bidding effectively. It may detect activity but not enforce its policy consistently. Or it may have examined the accounts and determined their activity was legitimate.

**We don't have enough evidence to determine which explanation is correct.**

What we can say is that these publicly observable bidding patterns warrant scrutiny.

## 8. What I haven't proven

To be completely clear:

- I have not proven that any named account is a bot.
- I have not proven that KOTN operates automated bidding accounts.
- I have not found evidence establishing deliberate price manipulation by KOTN.
- I cannot determine whether KOTN has investigated or disciplined any specific account.
- The auctions were still active when the data was collected, so provisional leading bids aren't final wins.

This is an investigation into observable bidding behaviour, not an allegation that particular individuals or KOTN have committed fraud.

## 9. I'm releasing the raw bidding data

Rather than expecting everyone to trust my interpretation, I'm making the underlying data available.

**Dataset: 19,813 individual bids, 14,877 auction listings, 2,194 bidder usernames.**

The dataset preserves the publicly displayed usernames, individual bid IDs, amounts, timestamps and listing IDs.

That means anyone can reproduce the analysis, check the bidding sequences and challenge the methodology.

[Insert publicly accessible GitHub or file-sharing link here.]

The collection contains no login credentials or private account information.

## 10. What's next?

The most revealing follow-up will be the completed auctions.

After the October 18–19 auctions close, we can compare how often these accounts actually win items versus how frequently they raise prices and are subsequently outbid.

We can also test whether 20 bids across different items within 60 seconds is achievable using KOTN's ordinary website without automation.

Those two tests should help distinguish aggressive legitimate buyers from genuinely suspicious activity.

**My question to KOTN is simple: Given that automated bidding is prohibited, what systems are used to detect it, and how is that policy enforced?**

And for people who use KOTN regularly, have you observed similar behaviour?

I'm particularly interested in hearing from anyone who has tested how quickly bids can be placed through the normal website, or who has received a direct explanation of KOTN's anti-bot enforcement.
