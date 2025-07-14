import pandas as pd
from functools import reduce
from io import StringIO

def count_actions(df, group_col, prefix, valid_actions):
    """Count total and action-specific occurrences grouped by a column."""
    total = df.groupby(group_col).size().rename(f"{prefix} Total Actions")

    actions_count = (
        df.groupby([group_col, "action"]).size()
        .unstack(fill_value=0)
        .reindex(columns=valid_actions, fill_value=0)
        .rename(columns=lambda c: f"{prefix} {c.capitalize()}")
    )

    result = pd.concat([total, actions_count], axis=1).reset_index()
    return result.rename(columns={group_col: "Company"})


def summarize_company_interactions(edge_df: pd.DataFrame, network_type="attention", title: str = ""):
    """Summarize company interactions for either attention or collaboration networks.

    Returns:
        summary: pd.DataFrame with aggregated counts
        latex_table: str LaTeX representation of the summary table
    """
    if network_type == "attention":
        valid_actions = ["stars", "watches", "follows"]
    elif network_type == "collaboration":
        valid_actions = ["forks"]
    else:
        raise ValueError("network_type must be 'attention' or 'collaboration'")

    filtered_df = edge_df[edge_df["action"].isin(valid_actions)].copy()

    filtered_df['flow'] = pd.NA
    filtered_df.loc[filtered_df['src_company'] == filtered_df['target_company'], 'flow'] = 'intra'
    filtered_df.loc[filtered_df['src_company'] != filtered_df['target_company'], 'flow'] = 'inter'

    counts = []
    for flow in ['intra', 'inter']:
        for direction, company_col, prefix in [
            ('inbound', 'target_company', f"{flow.capitalize()} Inbound"),
            ('outbound', 'src_company', f"{flow.capitalize()} Outbound"),
        ]:
            sub_df = filtered_df[filtered_df['flow'] == flow]
            counts.append(count_actions(sub_df, company_col, prefix, valid_actions))

    summary = reduce(lambda left, right: pd.merge(left, right, on="Company", how="outer"), counts).fillna(0)

    # Extract metadata columns if available
    src_meta_cols = ["src_company", "src_company_category"]
    target_meta_cols = ["target_company", "target_company_category"]

    src_meta = pd.DataFrame()
    target_meta = pd.DataFrame()

    if all(col in edge_df.columns for col in src_meta_cols):
        src_meta = edge_df[src_meta_cols].drop_duplicates().rename(columns={
            "src_company": "Company",
            "src_company_category": "Company Category"
        })

    if all(col in edge_df.columns for col in target_meta_cols):
        target_meta = edge_df[target_meta_cols].drop_duplicates().rename(columns={
            "target_company": "Company",
            "target_company_category": "Company Category"
        })

    meta = pd.concat([src_meta, target_meta], ignore_index=True).drop_duplicates(subset="Company")
    summary = meta.merge(summary, on="Company", how="right")

    # Compute totals
    summary["Total Inbound Actions"] = summary.filter(like="Inbound").filter(regex="Total Actions").sum(axis=1)
    summary["Total Outbound Actions"] = summary.filter(like="Outbound").filter(regex="Total Actions").sum(axis=1)
    summary["Total Actions"] = summary["Total Inbound Actions"] + summary["Total Outbound Actions"]

    base_cols = [
        "Company", "Company Category",
        "Total Actions", "Total Inbound Actions", "Total Outbound Actions"
    ]
    flow_types = ["Intra Inbound", "Intra Outbound", "Inter Inbound", "Inter Outbound"]
    action_cols = [f"{flow} {action.capitalize()}" for flow in flow_types for action in valid_actions]
    desired_cols = base_cols + action_cols

    summary = summary.reindex(columns=desired_cols, fill_value=0)

    numeric_cols = summary.columns.difference(["Company", "Company Category"])
    summary[numeric_cols] = summary[numeric_cols].astype(int)
    summary["Company Category"] = pd.to_numeric(summary["Company Category"], errors='coerce').fillna(0).astype(int)

    # Convert DataFrame to LaTeX table (no longtable to avoid environment issues)

    if network_type == "attention":
        caption = "Attention Edges Summary (Company Level)"
        label = "tab:attention_summary"
    else:
        caption = "Collaboration Edges Summary (Company Level)"
        label = "tab:collaboration_summary"

    column_format = '>{\\raggedright\\arraybackslash}X ' * len(summary.columns)

    latex_str = summary.to_latex(
        index=False,
        escape=True,
        caption=caption,
        label=label,
        column_format=column_format.strip(),
    )
    
    # Replace tabular with tabularx and add \textwidth
    latex_str = latex_str.replace(
        '\\begin{tabular}',
        '\\begin{tabularx}{\\textwidth}'
    ).replace(
        '\\end{tabular}',
        '\\end{tabularx}'
    )

    return summary, latex_str