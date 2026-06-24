# METHOD.md

## Goal
Build an independent, transparent 2026 FIFA World Cup forecast using only public data and saved internal calculations.

## What we can publicly learn from PELE-style descriptions
These are publicly described feature categories often associated with advanced football forecasting, including Nate Silver's PELE framework. We use them only as inspiration, not as a template to copy numbers or proprietary implementation details.

### Publicly described PELE-style features
- Elo-style dynamic team strength
- offensive and defensive team profile or "tilt"
- roster quality, injuries, absences, and squad age
- match importance and recent competitive performance
- home-field and travel effects
- scoreline probabilities
- tournament simulation with bracket advancement odds
- separate treatment of extra time and penalties

## Our independent implementation

### 1. Base team strength
- Start from a public men’s national-team rating source, with World Football Elo as the default baseline.
- Save the pulled rating snapshot with retrieval timestamp.
- Optionally backfill our own rolling Elo later from public match results for validation and robustness.

### 2. Modest recent-form adjustment
- Apply a capped recent-form modifier based on a rolling window of recent competitive internationals.
- Keep the adjustment small relative to base strength so the model does not overreact to one result.
- Default cap: plus or minus 25 Elo-equivalent points.

### 3. Roster availability adjustment
- Apply only for confirmed absences, suspensions, or clearly reported key injuries from official or highly credible public sources.
- No rumor-account adjustments.
- Initial implementation uses a simple documented point deduction by player importance band, with all adjustments saved to state.

### 4. Offensive and defensive split
- Convert overall team strength into attack and defense components using recent goals for and against, opponent-adjusted where possible.
- Keep this split modest and mean-reverting.
- Initial version uses a simple shrinkage blend rather than a high-parameter latent model.

### 5. Venue, host, and travel effects
- Apply a home-advantage bump for USA, Mexico, and Canada when applicable.
- Apply no arbitrary travel penalty at first run unless validated; document any future addition.
- Neutral-site baseline for all other matches.

### 6. Match model
- Use independent Poisson goal scoring with a low-score correction in a later version if testing supports it.
- Output win, draw, and loss probabilities from scoreline enumeration.
- Save expected goals and full probability vectors for each match.

### 7. Knockout modeling
- Regulation modeled from 90-minute scoreline probabilities.
- If tied after regulation, model extra time using reduced expected goals, default 0.33 of regulation rate for each side over 30 minutes.
- If still tied, use a penalty shootout model. Initial implementation uses 50-50 unless a documented public goalkeeper or team penalty edge is added later and validated.

### 8. Tournament simulation
- Use the real 2026 format: 12 groups of 4, top two in each group plus best eight third-placed teams advance.
- Apply official tiebreakers where feasible using saved simulated results.
- Use FIFA’s published round-of-32 mapping logic for third-place combinations where feasible; until fully encoded, flag this as an implementation priority and avoid pretending exactness.

### 9. Daily update process
- Treat completed matches as fixed.
- Update ratings.
- Recompute remaining match probabilities.
- Run at least 100,000 simulations.
- Save all inputs and outputs into `state/` before reporting.

## Assumptions
- Public Elo is a good starting baseline for international strength.
- Recent form helps, but only modestly.
- Confirmed absences matter, but simple documented adjustments are better than opaque complexity.
- Penalties are near coin-flip absent stronger public evidence.
- A transparent Poisson system is preferable to a black-box model without validation.

## Limitations
- This is not PELE and does not attempt to reverse-engineer PELE.
- Roster-value adjustments are necessarily approximate at first run.
- Public injury data can be incomplete or lag official confirmation.
- Travel and climate effects are difficult to estimate cleanly without overfitting.
- Exact 2026 round-of-32 third-place mapping must be explicitly encoded from official regulations to claim full bracket precision.
- Public market probabilities are used only as a comparison benchmark, not as the model driver.

## Validation plan
- Back-test against 2018 and 2022 World Cups.
- Compare log loss and Brier score of the base Elo plus Poisson model against simple alternatives.
- Only add complexity if it improves back-test performance and calibration.
