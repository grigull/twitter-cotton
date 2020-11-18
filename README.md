# Twitter Bot for Cotton Reports

Cotton as a trading commodity is hardly covered by the media, which can sometimes make it difficult
to keep up to date with important data releases.

This script Tweets out the headline numbers of the cotton reports though the Twitter handle [@CottonChat](https://twitter.com/CottonChat).

## Functions

### export-sales

Every Thursday at 8:30am EST the USDA reports the sales & exports of cotton to each country over the past week (1 week lagged).
Sometimes the report is released a day or two late (never on weekends). Given the random nature of this situation, the script checks at several intervals past 8:30 on weekdays to see if any new data has been released that has not yet been tweeted out.
Key metrics - Total Sales, Total Cancelations, Total Exports.
Data URL - https://apps.fas.usda.gov/export-sales/cottfax.htm

## Tech Stack

- Packages: Tweepy
- AWS Services: Lambda, Secrets Manager, CloudWatch Events
