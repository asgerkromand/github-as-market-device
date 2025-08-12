# Import packages
import pandas as pd
from functools import reduce
from typing import Tuple

#############
# FUNCTIONS #
#############


def compute_adjacency_matrix_inter(df: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
    """
    Computes an adjacency matrix (excluding self-loops) from a DataFrame
    of edges between companies and returns both the matrix and its LaTeX representation.

    Args:
        df (pd.DataFrame): DataFrame containing at least the following columns:
            'src_company', 'target_company',
            'src_company_label', 'target_company_label'

    Returns:
        tuple: (adjacency matrix, LaTeX representation)
    """
    # Exclude self-loops
    mask = df["src_company"] != df["target_company"]
    filtered_df = df[mask].copy()

    # Get unique company labels
    labels = pd.Index(
        filtered_df["src_company_label"].tolist()
        + filtered_df["target_company_label"].tolist()
    ).unique()

    # Group by label pairs and count occurrences
    grouped = (
        filtered_df.groupby(["src_company_label", "target_company_label"])
        .size()
        .reset_index(name="count")
    )

    # Pivot to form adjacency matrix
    matrix = grouped.pivot(
        index="src_company_label", columns="target_company_label", values="count"
    ).fillna(0)

    # Reindex and sort to ensure symmetric alignment
    matrix = matrix.reindex(labels, axis=0).reindex(labels, axis=1)
    matrix = matrix.sort_index(axis=0).sort_index(axis=1).fillna(0).astype(int)

    # Set MultiIndex columns and name index
    matrix.columns = pd.MultiIndex.from_product([["Target"], matrix.columns])
    matrix.index.name = "Source"

    # Generate LaTeX string
    latex_matrix = matrix.to_latex(index=True, escape=True)

    return matrix, latex_matrix


def compute_adjacency_matrix_intra(df: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
    """
    Computes an adjacency matrix (including self-loops) from a DataFrame
    of edges between companies and returns both the matrix and its LaTeX representation.

    Args:
        df (pd.DataFrame): DataFrame containing at least the following columns:
            'src_company', 'target_company',
            'src_company_label', 'target_company_label'

    Returns:
        tuple:
            - pd.DataFrame: Adjacency matrix with MultiIndex columns
            - str: LaTeX-formatted string of the matrix
    """
    # Get all unique labels
    labels = pd.Index(
        df["src_company_label"].tolist() + df["target_company_label"].tolist()
    ).unique()

    # Group by label pairs and count occurrences (includes self-loops)
    grouped = (
        df.groupby(["src_company_label", "target_company_label"])
        .size()
        .reset_index(name="count")
    )

    # Pivot to form adjacency matrix
    matrix = grouped.pivot(
        index="src_company_label", columns="target_company_label", values="count"
    )

    # Reindex and sort for symmetry
    matrix = matrix.reindex(labels, axis=0).reindex(labels, axis=1)
    matrix = matrix.sort_index(axis=0).sort_index(axis=1).fillna(0).astype(int)

    # Set MultiIndex columns and index name
    matrix.columns = pd.MultiIndex.from_product([["Target"], matrix.columns])
    matrix.index.name = "Source"

    # Generate LaTeX representation
    latex_matrix = matrix.to_latex(index=True, escape=True)

    return matrix, latex_matrix


def count_actions(df, group_col: str, prefix: str, valid_actions: list):
    """
    Counts the number of actions per group and returns a DataFrame
    with the total actions and counts for each valid action.

    Args:
        df (pd.DataFrame): DataFrame containing the actions.
        group_col (str): Column name to group by.
        prefix (str): Prefix for the resulting columns.
        valid_actions (list): List of valid actions to count.

    Returns:
        pd.DataFrame: DataFrame with total actions and counts for each valid action.
    """
    # Count total actions and actions per group
    total = df.groupby(group_col).size().rename(f"{prefix} Total Actions")

    # Count actions per group and reindex to ensure all valid actions are present
    actions_count = df.groupby([group_col, "action"]).size()

    # Count total actions and actions per group
    total = df.groupby(group_col).size().rename(f"{prefix} Total Actions")

    # Count actions per group and reindex to ensure all valid actions are present
    actions_count = (
        df.groupby([group_col, "action"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=valid_actions, fill_value=0)
        .rename(columns=lambda c: f"{prefix} {c.capitalize()}")
    )

    # Combine total and actions count into a single DataFrame
    result = pd.concat([total, actions_count], axis=1).reset_index()

    return result.rename(columns={group_col: "Company"})


def filter_data_rows(latex_table: str, adjacency_table=False) -> str:
    """
    Filters the LaTeX table string to return only
    the data rows, excluding the header and footer.

    Args:
        latex_table (str): The LaTeX table string to filter.
        adjacency_table (bool): Whether the table is an adjacency table.

    Returns:
        str: The filtered data rows.
    """
    if adjacency_table:
        data_rows = latex_table.split("\\midrule\n")[1].split("\\bottomrule")[0].strip()
    else:
        data_rows = latex_table.split("\\midrule\n")[1].split("\\bottomrule")[0].strip()

    return data_rows


def summarize_company_interactions(
    edge_df: pd.DataFrame, network_type="attention", title: str = ""
) -> tuple:
    """
    Summarizes company interactions based on the edge DataFrame and network type.

    Parameters:
        edge_df (pd.DataFrame): DataFrame containing edge data with columns:
            'src_company', 'target_company', 'action', 'd_intra_level',
            'src_company_category', 'target_company_category'.
        network_type (str): Type of network, either "attention" or "collaboration".
        title (str): Title for the summary table.

    Returns:
        tuple: A tuple containing:
            - str: LaTeX-formatted string of the summary table data rows.
            - pd.DataFrame: Summary DataFrame with counts and metadata.
    """
    # Validate network_type
    if not isinstance(network_type, str) or network_type not in [
        "attention",
        "collaboration",
    ]:
        raise ValueError("network_type must be 'attention' or 'collaboration'")

    # Define valid actions based on network type
    valid_actions = []
    if network_type == "attention":
        valid_actions = ["stars", "watches", "follows"]
    elif network_type == "collaboration":
        valid_actions = ["forks"]
    else:
        raise ValueError("network_type must be 'attention' or 'collaboration'")

    # Filter edge DataFrame for valid actions
    filtered_df = edge_df[edge_df["action"].isin(valid_actions)].copy()

    # Count intra and inter actions
    counts = []
    inter_df = filtered_df[filtered_df["d_intra_level"] == 0]
    for direction, company_col, prefix in [
        ("inbound", "target_company", "Inter Inbound"),
        ("outbound", "src_company", "Inter Outbound"),
    ]:
        counts.append(count_actions(inter_df, company_col, prefix, valid_actions))
    intra_df = filtered_df[filtered_df["d_intra_level"] == 1]
    counts.append(count_actions(intra_df, "target_company", "Intra", valid_actions))

    # Merge all counts into a single DataFrame
    summary = reduce(
        lambda left, right: pd.merge(left, right, on="Company", how="outer"), counts
    ).fillna(0)

    # Compute meta columns
    src_meta_cols = ["src_company", "src_company_category"]
    target_meta_cols = ["target_company", "target_company_category"]

    src_meta = (
        edge_df[src_meta_cols]
        .drop_duplicates()
        .rename(columns={"src_company": "Company", "src_company_category": "Category"})
        if all(col in edge_df.columns for col in src_meta_cols)
        else pd.DataFrame()
    )

    target_meta = (
        edge_df[target_meta_cols]
        .drop_duplicates()
        .rename(
            columns={
                "target_company": "Company",
                "target_company_category": "Company Category",
            }
        )
        if all(col in edge_df.columns for col in target_meta_cols)
        else pd.DataFrame()
    )

    # Add metadata to summary
    meta = pd.concat([src_meta, target_meta], ignore_index=True).drop_duplicates(
        subset="Company"
    )
    summary = meta.merge(summary, on="Company", how="right")

    # Compute totals
    if network_type == "attention":
        summary["Total Inter Inbound"] = (
            summary.filter(like="Inter Inbound")
            .filter(regex="Total Actions")
            .sum(axis=1)
        )
        summary["Total Inter Outbound"] = (
            summary.filter(like="Inter Outbound")
            .filter(regex="Total Actions")
            .sum(axis=1)
        )
        summary["Total Inter Actions"] = (
            summary["Total Inter Inbound"] + summary["Total Inter Outbound"]
        )
        summary["Total Intra Actions"] = (
            summary.filter(like="Intra").filter(regex="Total Actions").sum(axis=1)
        )
    else:
        summary["Total Inter Actions"] = (
            summary.filter(like="Inter").filter(regex="Total Actions").sum(axis=1)
        )

    # Define base and action columns
    base_cols = [
        "Company",
        "Company Category",
    ]

    # Inter cols
    if network_type == "attention":
        inter_total_cols = [
            "Total Inter Actions",
            "Total Inter Inbound",
            "Total Inter Outbound",
        ]
    else:
        inter_total_cols = ["Total Inter Actions"]
    inter_flow_types = ["Inter Inbound", "Inter Outbound"]
    inter_action_cols = [
        f"{flow} {action.capitalize()}"
        for flow in inter_flow_types
        for action in valid_actions
    ]
    inter_cols = inter_total_cols + inter_action_cols

    # Intra cols
    intra_flow_types = ["Intra"]
    intra_action_cols = [
        f"{flow} {action.capitalize()}"
        for flow in intra_flow_types
        for action in valid_actions
    ]
    if network_type == "attention":
        intra_cols = ["Total Intra Actions"] + intra_action_cols
    else:
        intra_cols = intra_action_cols

    # Combine all columns
    summary = summary.reindex(
        columns=base_cols + inter_cols + intra_cols, fill_value=0
    ).sort_values(by="Company")

    # Convert numeric columns to int and format Company Category
    numeric_cols = summary.columns.difference(["Company", "Company Category"])
    summary[numeric_cols] = summary[numeric_cols].astype(int)
    summary["Company Category"] = (
        pd.to_numeric(summary["Company Category"], errors="coerce")
        .fillna(0)
        .astype(int)
    )
    summary.columns = [f"\\textbf{{{col}}}" for col in summary.columns]

    # Generate LaTeX table
    latex_table = summary.to_latex(index=False, escape=True)

    # Filter for data rows only
    data_rows = filter_data_rows(latex_table)

    return data_rows, summary
