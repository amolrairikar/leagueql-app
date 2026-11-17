## Decision: winsorize weekly scores at median + 2 robust σ

- **Cap:** per cut week, over every played regular-season team-week through that week, `cap = median + 2·(1.4826·MAD)`. Upper bound only; low scores are not floored.
- **Why median/MAD, not mean/SD:** a mean and SD are inflated by the very outlier being capped (a 400-point week in a 12-score sample pushes mean + 2σ to ~293, barely capping it). Median and MAD are unaffected by it, while 1.4826·MAD matches the SD for normal data. It adapts to each league's scoring scale with no tuned constant.
- **Recomputed per cut:** each week's rankings use that cut's cap, so history stays internally consistent and ranks for earlier weeks are unaffected by later spikes.
- **Rejected:** median for form (discards hot streaks), percentile scaling (loses margin information), weight changes (does not address the cause).
