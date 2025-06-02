import os

def generate_appendix(
    df,
    src_col,
    target_col,
    action_col,
    new_column_name,
    relevant_actions,
    filename,
    appendix_label,
    appendix_title,
    appendix_dir
):
    # Step 1: Filter out intra-company-category activity
    filtered = df[df['src_company'] != df['target_company']]

    # Step 2: Count actions
    grouped = (
        filtered
        .groupby([src_col, target_col, action_col])
        .size()
        .reset_index(name='count')
    )

    # Step 3: Pivot to wide format
    pivoted = grouped.pivot_table(
        index=[src_col, target_col],
        columns=action_col,
        values='count',
        aggfunc='sum',
        fill_value=0
    ).reset_index()

    # Step 4: Compute total column and drop individual actions
    pivoted[new_column_name] = sum(pivoted.get(action, 0) for action in relevant_actions if action in pivoted.columns)
    pivoted.drop(columns=[a for a in relevant_actions if a in pivoted.columns], inplace=True)

    # Step 5: Prepare file output
    os.makedirs(appendix_dir, exist_ok=True)
    file_path = os.path.join(appendix_dir, filename)

    # Step 6: Write markdown file
    with open(file_path, "w") as f:
        f.write(f"# {appendix_label}: {appendix_title}\n\n")
        f.write(
            "This table summarizes inter-company-category GitHub actions between users.\n"
            "Each row corresponds to GitHub activity where the source user works for a company in one category, "
            "and the target user works for a company in a different category.\n\n"
            f"The `{new_column_name}` column counts the number of GitHub actions "
            f"(e.g., {', '.join(relevant_actions)}) from users in the source category toward users in the target category.\n\n"
            "**Example:**\n"
            "If GitHub user X (working for a company labeled **`a`**) stars a repository owned by GitHub user Y "
            "(working for a company labeled **`b`**), and `a ≠ b`, this is counted as 1 toward the cell "
            "`(src_company_label = a, target_company_label = b)`.\n\n"
        )

        # Markdown table header
        f.write("| " + " | ".join(f"**{col}**" for col in pivoted.columns) + " |\n")
        f.write("|" + "|".join(["---"] * len(pivoted.columns)) + "|\n")

        # Markdown table rows with italics for labels
        for _, row in pivoted.iterrows():
            row_data = []
            for col in pivoted.columns:
                val = row[col]
                if col in [src_col, target_col]:
                    val = f"*{val}*"
                row_data.append(str(val))
            f.write("| " + " | ".join(row_data) + " |\n")