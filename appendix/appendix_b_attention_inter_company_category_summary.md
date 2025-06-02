# Appendix B: Attention Between Companies of Different Categories

This table summarizes inter-company-category GitHub actions between users.
Each row corresponds to GitHub activity where the source user works for a company in one category, and the target user works for a company in a different category.

The `no_attention_actions` column counts the number of GitHub actions (e.g., follows, stars, watches) from users in the source category toward users in the target category.

**Example:**
If GitHub user X (working for a company labeled **`a`**) stars a repository owned by GitHub user Y (working for a company labeled **`b`**), and `a ≠ b`, this is counted as 1 toward the cell `(src_company_label = a, target_company_label = b)`.

| **src_company_label** | **target_company_label** | **no_attention_actions** |
|---|---|---|
| *1 Digital and marketing consultancies* | *1 Digital and marketing consultancies* | 6 |
| *1 Digital and marketing consultancies* | *2 Bespoke app companies* | 6 |
