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
    summary["Total Inbound"] = summary.filter(like="Inbound").filter(regex="Total Actions").sum(axis=1)
    summary["Total Outbound"] = summary.filter(like="Outbound").filter(regex="Total Actions").sum(axis=1)
    summary["Total Actions"] = summary["Total Inbound"] + summary["Total Outbound"]

    base_cols = [
        "Company", "Company Category",
        "Total Actions", "Total Inbound", "Total Outbound"
    ]
    flow_types = ["Intra Inbound", "Intra Outbound", "Inter Inbound", "Inter Outbound"]
    action_cols = [f"{flow} {action.capitalize()}" for flow in flow_types for action in valid_actions]
    desired_cols = base_cols + action_cols

    summary = summary.reindex(columns=desired_cols, fill_value=0).sort_values(by="Company")

    numeric_cols = summary.columns.difference(["Company", "Company Category"])
    summary[numeric_cols] = summary[numeric_cols].astype(int)
    summary["Company Category"] = pd.to_numeric(summary["Company Category"], errors='coerce').fillna(0).astype(int)
    summary.columns = [f'\\textbf{{{col}}}' for col in summary.columns]

    # Determine layout logic
    use_longtable = network_type == "attention"
    
    # Set caption/label
    caption = "Attention Actions Summary (Company Level)" if use_longtable else "Collaboration Edges Summary (Company Level)"
    label = "tab:attention_summary" if use_longtable else "tab:collaboration_summary"
    
    # Define LaTeX column format string
    first_col_width = '2cm'
    column_format = (
        f'p{{{first_col_width}}} ' +                              # First column fixed width
        '>{\\centering\\arraybackslash}X ' +                      # Second column centered
        '>{\\raggedleft\\arraybackslash}X ' * (len(summary.columns) - 2)  # Remaining numeric columns right-aligned
    )
    
    # Choose table environment
    latex_str = summary.to_latex(
        index=False,
        escape=False,
        caption=caption,
        label=label,
        column_format=column_format,
        position='htbp',
        longtable=use_longtable,
    )
    
    # Common replacements
    latex_str = latex_str.replace(
        '\\textwidth',
        '\\linewidth'
    )
    
    if use_longtable:
        # --- For ATTENTION network with threeparttablex + longtable layout ---
        latex_str = latex_str.replace(
            '\\begin{longtable}',
            '\\begin{ThreePartTable}\n\\begin{TableNotes}\n\\footnotesize\n'
            '\\item \\textbf{Company Category:} 1 = Digital and marketing consultancies, '
            '2 = Bespoke app companies, 3 = Data-broker- and infrastructure companies, '
            '4 = Companies with specific digital part/app as part of service/product\n'
            '\\end{TableNotes}\n'
            '\\rowcolors{3}{gray!10}{white}\n'
            '\\begin{longtable}'
        ).replace(
            '\\end{longtable}',
            '\\insertTableNotes\n\\end{longtable}\n\\end{ThreePartTable}'
        )
    else:
        # --- For COLLABORATION network using threeparttable + tabularx ---
        latex_str = latex_str.replace(
            '\\begin{table}[htbp]',
            '\\begin{table}[htbp]\n\\centering\n\\begin{threeparttable}'
        ).replace(
            '\\begin{tabular}',
            '\\rowcolors{2}{gray!10}{white}\n\\begin{tabularx}{\\linewidth}'
        ).replace(
            '\\end{tabular}',
            '\\end{tabularx}\n\\begin{tablenotes}[para,flushleft]\n\\footnotesize\n'
            '\\item \\textbf{Company Category:} 1 = Digital and marketing consultancies, '
            '2 = Bespoke app companies, 3 = Data-broker- and infrastructure companies, '
            '4 = Companies with specific digital part/app as part of service/product\n'
            '\\end{tablenotes}'
        ).replace(
            '\\end{table}',
            '\\end{threeparttable}\n\\end{table}'
        )

    return summary, latex_str