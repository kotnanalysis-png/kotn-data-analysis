# KOTN Bid Data Research — Multi-page GitHub Pages Site

Independent analysis of publicly recorded KOTN auction bid records. Not affiliated with the auction operator.

## Live site

https://kotnanalysis-png.github.io/kotn-data-analysis/

## Site contents

- Overview (`index.html`)
- Daily activity (`activity.html`)
- Bidder profiles (`bidders.html`)
- Inferred category concentrations (`categories.html`)
- Bidding timing and patterns (`patterns.html`)
- Data quality and outcomes (`quality.html`)
- Methodology and downloads (`methodology.html`)

## Analysis cutoff

The October 17 run excludes all bids made on October 17. It includes 28,026 bids through October 16, 23:59:45 (source timestamps interpreted as Toronto local time). October 13 is a partial first observed date. Source catalogue state was captured October 17; it is not a reconstructed historical October 16 financial state. No verified closed outcomes available.

## Deployment

Upload the contents of this archive into the **root** of `kotnanalysis-png/kotn-data-analysis` on branch `main`, preserving the `assets/` and `data/` folders. Keep `index.html` at repository root. The website uses only local CSS/JS and works on GitHub Pages. It also opens offline by opening index.html, with no external APIs required.

Do not upload authenticated page HTML, cookies, secrets, browser profiles, or local database files.

## Caution

High-frequency bidding is not proof of bots, dishonest behaviour, or wrongdoing.
