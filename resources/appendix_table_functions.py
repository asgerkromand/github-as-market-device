import pandas as pd
from functools import reduce


def count_actions(df, group_col, prefix, valid_actions):
    total = df.groupby(group_col).size().rename(f"{prefix} Total Actions")

    actions_count = (
        df.groupby([group_col, "action"]).size()
        .unstack(fill_value=0)
        .reindex(columns=valid_actions, fill_value=0)
        .rename(columns=lambda c: f"{prefix} {c.capitalize()}")
    )

    result = pd.concat([total, actions_count], axis=1).reset_index()
    return result.rename(columns={group_col: "Company"})


def get_column_format(network_type: str, ncols: int) -> str:
    if network_type == "attention":
        return (
            '>{\\raggedright\\arraybackslash}p{1.3cm} '
            '>{\\centering\\arraybackslash}p{1.3cm} '
            + '>{\\centering\\arraybackslash}p{1cm} ' * (ncols - 2)
        ).strip()
    else:
        return (
            'p{2cm} '
            + '>{\\centering\\arraybackslash}X '
            + '>{\\raggedleft\\arraybackslash}X ' * (ncols - 2)
        ).strip()


def format_attention_table(latex_str: str, columns, caption: str, label: str, column_format: str) -> str:
    header = ' & '.join([f'\\textbf{{{col}}}' for col in columns]) + ' \\\\\n\\midrule\n'

    first_head = (
        f'\\caption{{{caption}}} \\label{{{label}}} \\\\\n'
        f'{header}'
        '\\endfirsthead\n'
    )
    
    continued_head = (
        '\\rowcolors{2}{white}{gray!30}\n'
        '\\caption[]{(continued)} \\\\\n'
        f'{header}'
        '\\endhead\n'
        '\\rowcolors{2}{white}{gray!30}\n'
    )

    # Add table notes and formatting before longtable
    latex_str = latex_str.replace(
        '\\begin{longtable}',
        '\\begin{ThreePartTable}\n'
        '\\begin{TableNotes}\n\\footnotesize\n'
        '\\item \\textbf{Company Category:} 1 = Digital and marketing consultancies, '
        '2 = Bespoke app companies, 3 = Data-broker- and infrastructure companies, '
        '4 = Companies with specific digital part/app as part of service/product\n'
        '\\end{TableNotes}\n\n'
        '\\footnotesize\n\n'
        '\\begin{longtable}'
    )

    # Replace only the first \toprule with first header
    latex_str = latex_str.replace('\\toprule', first_head, 1)

    # Insert continued header before \endhead
    latex_str = latex_str.replace('\\endhead', continued_head)

    # Add bottom rule and insertTableNotes
    latex_str = latex_str.replace(
        '\\bottomrule',
        '\\bottomrule\n\\insertTableNotes'
    ).replace(
        '\\end{longtable}',
        '\\end{longtable}\n\\end{ThreePartTable}'
    )

    return latex_str


def format_collaboration_table(latex_str: str, caption: str, label: str) -> str:
    return latex_str \
        .replace(
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


def build_latex_table(df: pd.DataFrame, network_type: str) -> str:
    ncols = len(df.columns)
    if ncols < 2:
        raise ValueError("DataFrame must have at least two columns.")

    caption = (
        "Attention Actions Summary (Company Level)"
        if network_type == "attention"
        else "Collaboration Edges Summary (Company Level)"
    )
    label = (
        "tab:attention_summary"
        if network_type == "attention"
        else "tab:collaboration_summary"
    )

    column_format = get_column_format(network_type, ncols)
    use_longtable = (network_type == "attention")

    latex_str = df.to_latex(
        index=False,
        escape=False,
        caption=caption if not use_longtable else False,
        label=label if not use_longtable else False,
        column_format=column_format,
        position='htbp',
        longtable=use_longtable,
    ).replace('\\textwidth', '\\linewidth')

    if use_longtable:
        return format_attention_table(latex_str, df.columns, caption, label, column_format)
    else:
        return format_collaboration_table(latex_str, caption, label)


def summarize_company_interactions(edge_df: pd.DataFrame, network_type="attention", title: str = ""):
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
    if network_type == "attention":
        intra_df = filtered_df[filtered_df['flow'] == 'intra']
        counts.append(count_actions(intra_df, 'target_company', "Intra", valid_actions))

        inter_df = filtered_df[filtered_df['flow'] == 'inter']
        for direction, company_col, prefix in [
            ('inbound', 'target_company', "Inter Inbound"),
            ('outbound', 'src_company', "Inter Outbound"),
        ]:
            counts.append(count_actions(inter_df, company_col, prefix, valid_actions))
    else:
        for flow in ['intra', 'inter']:
            for direction, company_col, prefix in [
                ('inbound', 'target_company', f"{flow.capitalize()} Inbound"),
                ('outbound', 'src_company', f"{flow.capitalize()} Outbound"),
            ]:
                sub_df = filtered_df[filtered_df['flow'] == flow]
                counts.append(count_actions(sub_df, company_col, prefix, valid_actions))

    summary = reduce(lambda left, right: pd.merge(left, right, on="Company", how="outer"), counts).fillna(0)

    # Add metadata
    src_meta_cols = ["src_company", "src_company_category"]
    target_meta_cols = ["target_company", "target_company_category"]

    src_meta = (
        edge_df[src_meta_cols]
        .drop_duplicates()
        .rename(columns={"src_company": "Company", "src_company_category": "Company Category"})
        if all(col in edge_df.columns for col in src_meta_cols) else pd.DataFrame()
    )

    target_meta = (
        edge_df[target_meta_cols]
        .drop_duplicates()
        .rename(columns={"target_company": "Company", "target_company_category": "Company Category"})
        if all(col in edge_df.columns for col in target_meta_cols) else pd.DataFrame()
    )

    meta = pd.concat([src_meta, target_meta], ignore_index=True).drop_duplicates(subset="Company")
    summary = meta.merge(summary, on="Company", how="right")

    # Compute totals
    if network_type == "attention":
        summary["Total Inbound"] = summary.filter(like="Inter Inbound").filter(regex="Total Actions").sum(axis=1)
        summary["Total Outbound"] = summary.filter(like="Inter Outbound").filter(regex="Total Actions").sum(axis=1)
    else:
        summary["Total Inbound"] = summary.filter(like="Inbound").filter(regex="Total Actions").sum(axis=1)
        summary["Total Outbound"] = summary.filter(like="Outbound").filter(regex="Total Actions").sum(axis=1)
        summary["Total Actions"] = summary["Total Inbound"] + summary["Total Outbound"]

    base_cols = [
        "Company", "Company Category", "Total Actions", "Total Inbound", "Total Outbound"
    ]

    flow_types = (
        ["Intra", "Inter Inbound", "Inter Outbound"]
        if network_type == "attention"
        else ["Intra Inbound", "Intra Outbound", "Inter Inbound", "Inter Outbound"]
    )

    action_cols = [f"{flow} {action.capitalize()}" for flow in flow_types for action in valid_actions]
    summary = summary.reindex(columns=base_cols + action_cols, fill_value=0).sort_values(by="Company")

    numeric_cols = summary.columns.difference(["Company", "Company Category"])
    summary[numeric_cols] = summary[numeric_cols].astype(int)
    summary["Company Category"] = pd.to_numeric(summary["Company Category"], errors='coerce').fillna(0).astype(int)
    summary.columns = [f'\\textbf{{{col}}}' for col in summary.columns]

    latex_table = build_latex_table(summary, network_type)
    return summary, latex_table