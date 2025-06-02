import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
import textwrap
from matplotlib.lines import Line2D
import pandas as pd
from typing import Literal, Optional, List, Tuple
from pathlib import Path
import json
from collections import defaultdict
from datetime import datetime

# Paths
fp_main = Path(
    "/Volumes/SAM-SODAS-DISTRACT/Coding Distraction/github_as_a_market_device"
)
fp_main_output = Path(fp_main / "output")

company_category_map = {}
with open(fp_main_output / "company_category_dict.jsonl", "r") as f:
    for line in f:
        record = json.loads(line)
        company = record.get("company") or record.get("søgeord")  # whatever key holds company
        category = record.get("category") or record.get("new_company_category")
        if company and category is not None:
            company_category_map[company] = int(category)

class CompanyUserLookup:
    def __init__(self, df: pd.DataFrame, company_category_map: dict = company_category_map):
        self.df = df
        self.company_category = company_category_map
        self.users = set(df["user_login"].unique())

    def get_user_company(self, user: Optional[str]) -> Optional[str]:
        if user not in self.users:
            return None
        company = self.df.loc[self.df["user_login"] == user, "inferred_company"]
        return company.values[0] if not company.empty else None

    def get_company_category(self, company: Optional[str]) -> int:
        return self.company_category.get(company) if company else None


class NetworkEdgeListConstructor:
    CATEGORY_LABELS = {
        1: "1 Digital and marketing consultancies",
        2: "2 Bespoke app companies",
        3: "3 Data-broker- and infrastructure companies",
        4: "4 Companies with specific digital part/app as part of service/product",
    }

    def __init__(
        self,
        df: pd.DataFrame,
        company_category_map: dict = company_category_map,
    ):
        self.df = df
        self.lookup = CompanyUserLookup(df, company_category_map)
        self.company_label = self.CATEGORY_LABELS
        self.edge_types_in = ["forks_in", "stars_in", "watches_in", "follows_in"]
        self.edge_types_out = ["forks_out", "stars_out", "watches_out", "follows_out"]
        self.attention_actions = ["follows", "stars", "watches"]
        self.collaboration_actions = ["forks"]

    def _build_edge_dict(
        self,
        src_user: str,
        target_user: str,
        action: str,
        item: dict,
    ) -> Optional[dict]:
        if item is None:
            return None

        repo_name = item.get("repo_name")
        created_at = item.get("created_at")
        edge_repo = f"{repo_name}/{src_user}" if repo_name and src_user else None

        src_company = self.lookup.get_user_company(src_user)
        target_company = self.lookup.get_user_company(target_user)
        if not src_company or not target_company:
            return None

        d_intra = int(src_company == target_company)
        d_inter = int(src_company != target_company)

        src_company_category = self.lookup.get_company_category(src_company)
        target_company_category = self.lookup.get_company_category(target_company)

        src_company_label = self.company_label.get(src_company_category, "NA")
        target_company_label = self.company_label.get(target_company_category, "NA")

        return {
            "src": src_user,
            "target": target_user,
            "src_company": src_company,
            "target_company": target_company,
            "src_company_category": src_company_category,
            "src_company_label": src_company_label,
            "target_company_category": target_company_category,
            "target_company_label": target_company_label,
            "d_intra_level": d_intra,
            "d_inter_level": d_inter,
            "edge_repo": edge_repo,
            "action": action,
            "created_at": created_at,
        }

    def _process_edges(self, direction: Literal["in", "out"]) -> List[dict]:
        edges = []
        edge_types = self.edge_types_in if direction == "in" else self.edge_types_out

        for _, row in self.df.iterrows():
            user_login = row.get("user_login")

            for col in edge_types:
                action = col.split("_")[0]
                items = row.get(col)
                if items is None or len(items) == 0:
                    continue
                
                for item in items:
                    if direction == "in":
                        src_user = item.get("owner_login")
                        target_user = user_login
                    else:
                        src_user = user_login
                        target_user = item.get("owner_login")

                    if not src_user or not target_user:
                        continue

                    edge_dict = self._build_edge_dict(src_user, target_user, action, item)
                    if edge_dict:
                        edges.append(edge_dict)

        return edges

    def _build_user_level_edgelist(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        edges_in = self._process_edges("in")
        edges_out = self._process_edges("out")
        user_edges_df = pd.DataFrame(edges_in + edges_out)

        # Subset for attention and collaboration actions
        attention_df = user_edges_df[
            user_edges_df["action"].isin(self.attention_actions)
        ]
        collaboration_df = user_edges_df[
            user_edges_df["action"].isin(self.collaboration_actions)
        ]

        if user_edges_df.empty or attention_df.empty or collaboration_df.empty:
            print("WARNING: User edges DataFrame is empty!")

        return user_edges_df, attention_df, collaboration_df

    def get_edge_lists(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        return self._build_user_level_edgelist()


class GraphConstructor:
    def __init__(self, edge_list_df: pd.DataFrame, graph_type: Literal["attention", "collaboration"] = 'attention'):
        self.df = edge_list_df
        self.attention_actions = ["follows", "stars", "watches"]
        self.collaboration_actions = ["forks"]
        self.all_actions = self.attention_actions + self.collaboration_actions
        self.graph_type = graph_type
        
        if self.graph_type not in ["attention", "collaboration"]:
            raise ValueError("graph_type must be 'attention' or 'collaboration'")
        
        if self.graph_type == "attention":
            self.df_subset = self.df[self.df["action"].isin(self.attention_actions)]
        else:
            self.df_subset = self.df[self.df["action"].isin(self.collaboration_actions)]

        # Build company-category mapping once on init
        self.company_category_map = self._build_company_info_map()

    def _build_company_info_map(self):
        """
        Build a mapping from each unique company to a dict with 'category' and 'label'.
        """
        src = self.df_subset[['src_company', 'src_company_category', 'src_company_label']]
        tgt = self.df_subset[['target_company', 'target_company_category', 'target_company_label']]

        src = src.rename(columns={
            'src_company': 'company', 
            'src_company_category': 'category', 
            'src_company_label': 'label'
        })
        tgt = tgt.rename(columns={
            'target_company': 'company', 
            'target_company_category': 'category', 
            'target_company_label': 'label'
        })

        combined = pd.concat([src, tgt]).drop_duplicates(subset='company', keep='first')

        # Create a dict: company -> {'category': category_value, 'label': label_value}
        company_info_map = combined.set_index('company')[['category', 'label']].to_dict(orient='index')

        return company_info_map

    def build_user_graph(self) -> nx.DiGraph:
        # Count all occurrences of actions between users (including repeats)
        edge_action_counts = defaultdict(lambda: {action: 0 for action in self.all_actions})

        for _, row in self.df_subset.iterrows():
            src = row["src"]
            tgt = row["target"]
            action = row["action"].lower()
            if action not in self.all_actions:
                continue
            edge_action_counts[(src, tgt)][action] += 1

        G = nx.DiGraph()
        for (src, tgt), counts in edge_action_counts.items():
            # weight = 1 means user-user edge exists (unique edges)
            G.add_edge(src, tgt, weight=1, **counts)

        G = self.annotate_edges_with_intra_inter(G, level="user")
        return G

    def aggregate_to_company_graph(self, user_graph: nx.DiGraph, actions_to_include: list) -> nx.DiGraph:
        user_to_company = {}
        for _, row in self.df_subset.iterrows():
            user_to_company[row["src"]] = row["src_company"]
            user_to_company[row["target"]] = row["target_company"]

        company_edge_action_counts = defaultdict(lambda: {action: 0 for action in self.all_actions})
        company_edge_weights = defaultdict(int)  # counts unique user-user edges

        for src_user, tgt_user, data in user_graph.edges(data=True):
            src_c = user_to_company.get(src_user)
            tgt_c = user_to_company.get(tgt_user)
            if not src_c or not tgt_c:
                continue

            # Each unique user-user edge counts as 1 interaction (weight)
            company_edge_weights[(src_c, tgt_c)] += 1

            # Sum the total number of each action over all user-user edges
            for action in actions_to_include:
                company_edge_action_counts[(src_c, tgt_c)][action] += data.get(action, 0)

        G_company = nx.DiGraph()

        # Add nodes first to ensure all companies appear, even isolated ones
        all_companies = set(user_to_company.values())
        G_company.add_nodes_from(all_companies)

        # Add edges with aggregated attributes
        for (src_c, tgt_c), counts in company_edge_action_counts.items():
            weight = company_edge_weights.get((src_c, tgt_c), 0)
            if weight > 0:
                G_company.add_edge(src_c, tgt_c, weight=weight, **{a: counts[a] for a in actions_to_include})

        G_company = self.annotate_edges_with_intra_inter(G_company, level="company")

        # Add company_category attribute to nodes
        for node in G_company.nodes:
            info = self.company_category_map.get(node, {"category": "NA", "label": "NA"})
            G_company.nodes[node]['category'] = info.get('category', 'NA')
            G_company.nodes[node]['label'] = info.get('label', 'NA')

        return G_company

    def annotate_edges_with_intra_inter(self, G: nx.DiGraph, level="user") -> nx.DiGraph:
        if level == "user":
            user_to_company = {}
            for _, row in self.df_subset.iterrows():
                user_to_company[row["src"]] = row["src_company"]
                user_to_company[row["target"]] = row["target_company"]

            for u, v, d in G.edges(data=True):
                src_c = user_to_company.get(u)
                tgt_c = user_to_company.get(v)
                if src_c is None or tgt_c is None:
                    d["d_intra_level"] = 0
                    d["d_inter_level"] = 0
                    continue
                d["d_intra_level"] = 1 if src_c == tgt_c else 0
                d["d_inter_level"] = 1 if src_c != tgt_c else 0

        elif level == "company":
            for u, v, d in G.edges(data=True):
                d["d_intra_level"] = 1 if u == v else 0
                d["d_inter_level"] = 1 if u != v else 0

        else:
            raise ValueError("level must be 'user' or 'company'")

        return G

    def get_graph(self) -> nx.DiGraph:
        user_graph = self.build_user_graph()

        if self.graph_type == "attention":
            graph = self.aggregate_to_company_graph(user_graph, self.attention_actions)
        else:
            graph = self.aggregate_to_company_graph(user_graph, self.collaboration_actions)

        return graph


class NetworkVisualizer:
    def __init__(self, G, company_catego, company_catego_translate, node_colors):
        """
        Initializes the network visualizer.

        Parameters:
        - G: A NetworkX graph object (directed or undirected)
        - company_catego: Dictionary mapping nodes to company category codes
        - company_catego_translate: Dictionary translating category codes to readable labels
        - node_colors: Dictionary mapping category labels to color hex codes
        """
        self.G = G
        self.company_catego = company_catego
        self.company_catego_translate = company_catego_translate
        self.node_colors = node_colors

        self._add_node_attributes()

    def _add_node_attributes(self):
        """Adds company category labels to nodes."""
        for node in self.G.nodes:
            raw_cat = self.company_catego.get(node, "NA")
            label = self.company_catego_translate.get(raw_cat, "NA")
            self.G.nodes[node]["company_category"] = label

    def layout(self, layout_type="spring_layout", seed=170497, k=1):
        """
        Computes the layout of the graph.

        Parameters:
        - layout_type: Type of layout to compute (default: 'spring_layout')
        - seed: Seed for reproducibility
        - k: Optimal distance between nodes

        Returns:
        - pos: Dictionary of positions keyed by node
        """
        if layout_type == "spring_layout":
            return nx.spring_layout(
                self.G, seed=seed, k=k, iterations=50, weight="weight"
            )
        raise ValueError(f"Layout '{layout_type}' not supported.")

    def draw_nodes(self, pos, ax, alpha=1):
        """
        Draws graph nodes with colors and sizes based on degree.

        Parameters:
        - pos: Node positions
        - ax: Matplotlib axis
        - alpha: Transparency
        """
        node_size = [500 + (100 * self.G.degree[n]) for n in self.G]
        node_colors = [
            self.node_colors[self.G.nodes[n]["company_category"]] for n in self.G
        ]
        nx.draw_networkx_nodes(
            self.G,
            pos,
            ax=ax,
            node_color=node_colors,
            node_size=node_size,
            alpha=alpha,
            edgecolors="black",
        )

    def _filter_edges(self, edge_type):
        """Returns a list of inter- or intra-company edges."""
        if edge_type == "inter":
            return [
                (u, v, d)
                for u, v, d in self.G.edges(data=True)
                if d.get("d_inter_level") == 1
            ]
        if edge_type == "intra":
            return [
                (u, v, d)
                for u, v, d in self.G.edges(data=True)
                if d.get("d_intra_level") == 1
            ]
        raise ValueError("Edge type must be 'inter' or 'intra'")

    def _log_scale_weights(self, edges):
        """Applies log-scaling and normalization to edge weights."""
        log_weights = {(u, v): np.log(d["weight"] + 1) for u, v, d in edges}
        min_w, max_w = min(log_weights.values()), max(log_weights.values())
        if min_w == max_w:
            return {edge: 2 for edge in log_weights}
        return {
            edge: 1 + (w - min_w) / (max_w - min_w) * 3
            for edge, w in log_weights.items()
        }

    def draw_edges(self, pos, ax, alpha=1):
        """
        Draws both inter- and intra-company edges.

        Parameters:
        - pos: Node positions
        - ax: Matplotlib axis
        - alpha: Transparency
        """
        inter = self._filter_edges("inter")
        intra = self._filter_edges("intra")
        edge_widths = self._log_scale_weights(inter + intra)

        nx.set_edge_attributes(self.G, edge_widths, "edge_width")

        nx.draw_networkx_edges(
            self.G,
            pos,
            ax=ax,
            edgelist=inter,
            width=[edge_widths[(u, v)] for u, v, d in inter],
            edge_color="black",
            alpha=alpha,
            arrows=True,
            arrowstyle="->",
            connectionstyle="arc3,rad=0.1",
            arrowsize=40,
        )

        nx.draw_networkx_edges(
            self.G,
            pos,
            ax=ax,
            edgelist=intra,
            width=[edge_widths[(u, v)] for u, v, d in intra],
            edge_color="black",
            alpha=alpha,
            style="dashed",
            arrows=True,
            arrowstyle="->",
            arrowsize=20,
        )

    def draw_labels(
        self, pos, ax, verticalalignment="top", horizontalalignment="right"
    ):
        """Draws node labels."""
        labels = {n: n for n in self.G.nodes}
        nx.draw_networkx_labels(
            self.G,
            pos,
            labels,
            font_size=11,
            font_family="verdana",
            verticalalignment=verticalalignment,
            horizontalalignment=horizontalalignment,
            bbox=dict(facecolor="white", alpha=0.8, edgecolor="none"),
            font_weight="bold",
            ax=ax,
        )

    def get_legend_handles(self, wrap_width=30):
        """Returns legend handles for company categories."""

        def wrap_text(text):
            return "\n".join(textwrap.wrap(text, width=wrap_width))

        return [
            Line2D(
                [0],
                [0],
                marker="o",
                color="w",
                markerfacecolor=color,
                markersize=14,
                label=wrap_text(label),
            )
            for label, color in self.node_colors.items()
        ]

    def add_network_stats(self, ax, edgelist, pos=(0.02, 0.02), fontsize=16):
        """Adds text box with basic network statistics."""
        no_nodes = self.G.number_of_nodes()
        no_weighted_edges = self.G.number_of_edges()
        no_selfloops = edgelist[
            (edgelist["company_src"] == edgelist["company_target"])
        ].shape[0]
        no_companies = len(
            set(edgelist["company_src"]).union(edgelist["company_target"])
        )
        no_companies_w_inter = (
            edgelist.query("company_src != company_target")[
                ["company_src", "company_target"]
            ]
            .stack()
            .nunique()
        )

        extra_legend = [
            r"$\mathit{Network\ topology}$",
            f"",
            f"No. of user nodes: {no_nodes}",
            f"No. of weighted edges: {no_weighted_edges}",
            f"No. of self-loops (weighted edges): {no_selfloops}",
            f"No. of companies: {no_companies}",
            f"No. of companies with inter-company edges: {no_companies_w_inter}",
        ]
        ax.text(
            *pos,
            "\n".join(extra_legend),
            fontsize=fontsize,
            bbox=dict(facecolor="white", alpha=0, edgecolor="none"),
            transform=ax.transAxes,
        )

    def plot(
        self,
        edgelist,
        layout_type="spring_layout",
        figsize=(20, 20),
        seed=1704,
        k=1.5,
        title="Network",
    ):
        """
        Full network plotting pipeline.

        Parameters:
        - edgelist: DataFrame of edges to use for stats
        - layout_type: Layout algorithm name
        - figsize: Size of the matplotlib figure
        - seed: Layout randomness seed
        - k: Layout spacing parameter
        - title: Plot title
        """
        fig, ax = plt.subplots(figsize=figsize)
        pos = self.layout(layout_type=layout_type, seed=seed, k=k)
        self.draw_nodes(pos, ax)
        self.draw_edges(pos, ax)
        self.draw_labels(pos, ax)
        ax.set_axis_off()

        legend = ax.legend(
            handles=self.get_legend_handles(),
            title=r"$\mathit{Company\ categories}$",
            title_fontsize=16,
            fontsize=16,
            loc="upper right",
        )
        legend._legend_box.align = "left"

        self.add_network_stats(ax, edgelist)
        plt.title(title, fontsize=20)
        plt.show()

        return fig

class NetworkVisualizer2:
    DEFAULT_NODE_COLORS = {
        "1 Digital and marketing consultancies": '#003f5c',
        "2 Bespoke app companies": '#665191',
        "3 Data-broker- and infrastructure companies": '#d45087',
        "4 Companies with specific digital part/app as part of service/product": '#ff7c43',
    }
    ATTENTION_ACTIONS = {"follows", "stars", "watches"}
    COLLABORATION_ACTIONS = {"forks"}
    FONT_FAMILY = "verdana"

    def __init__(self, G, edgelist=None, graph_type: Literal["attention", "collaboration"]='attention'):
        self.G = G
        self.graph_type = graph_type
        self.edgelist = self.subset_edgelist(edgelist)
        self.node_colors = self.DEFAULT_NODE_COLORS

    def subset_edgelist(self, edgelist):
        attention_actions = ["follows", "stars", "watches"]
        collaboration_actions = ["forks"]
        if edgelist is None:
            return None
        if self.graph_type == "attention":
            return edgelist[edgelist["action"].isin(attention_actions)]
        elif self.graph_type == "collaboration":
            return edgelist[edgelist["action"].isin(collaboration_actions)]
        else:
            raise ValueError("graph_type must be 'attention' or 'collaboration'")

    def layout(self, layout_type="spring_layout", seed=170497, k=1):
        if layout_type == "spring_layout":
            return nx.spring_layout(self.G, seed=seed, k=k, iterations=50, weight="weight")
        raise ValueError(f"Layout '{layout_type}' not supported.")

    def _draw_nodes(self, pos, ax, alpha=1):
        degrees = dict(self.G.degree)
        node_sizes = [500 + 100 * degrees.get(n, 0) for n in self.G.nodes]

        labels = [self.G.nodes[n].get("label", "NA") for n in self.G.nodes]
        print(f"Node labels: {labels}")
        node_colors = [self.node_colors.get(label, "#000000") for label in labels]
        print(f"Node colors: {node_colors}")

        nx.draw_networkx_nodes(
            self.G,
            pos,
            ax=ax,
            node_color=node_colors,
            node_size=node_sizes,
            alpha=alpha,
            edgecolors="black",
        )

    def _filter_edges(self, edge_type):
        if edge_type == "inter":
            return [(u, v, d) for u, v, d in self.G.edges(data=True) if d.get("d_inter_level") == 1]
        if edge_type == "intra":
            return [(u, v, d) for u, v, d in self.G.edges(data=True) if d.get("d_intra_level") == 1]
        raise ValueError("Edge type must be 'inter' or 'intra'")

    def _log_scale_weights(self, edges):
        if not edges:
            return {}
        log_weights = {(u, v): np.log(d.get("weight", 1) + 1) for u, v, d in edges}
        min_w, max_w = min(log_weights.values()), max(log_weights.values())
        if min_w == max_w:
            return {edge: 2 for edge in log_weights}
        return {
            edge: 1 + (w - min_w) / (max_w - min_w) * 3
            for edge, w in log_weights.items()
        }

    def _draw_edges(self, pos, ax, alpha=1):
        inter_edges = self._filter_edges("inter")
        intra_edges = self._filter_edges("intra")

        all_edges = inter_edges + intra_edges
        edge_widths = self._log_scale_weights(all_edges)
        nx.set_edge_attributes(self.G, edge_widths, "edge_width")

        if inter_edges:
            nx.draw_networkx_edges(
                self.G,
                pos,
                ax=ax,
                edgelist=inter_edges,
                width=[edge_widths[(u, v)] for u, v, _ in inter_edges],
                edge_color="black",
                alpha=alpha,
                arrows=True,
                arrowstyle="->",
                connectionstyle="arc3,rad=0.1",
                arrowsize=40,
            )

        if intra_edges:
            nx.draw_networkx_edges(
                self.G,
                pos,
                ax=ax,
                edgelist=intra_edges,
                width=[edge_widths[(u, v)] for u, v, _ in intra_edges],
                edge_color="black",
                alpha=alpha,
                style="dashed",
                arrows=True,
                arrowstyle="->",
                arrowsize=20,
            )

    def _draw_labels(self, pos, ax, verticalalignment="top", horizontalalignment="right"):
        labels = {n: n for n in self.G.nodes}
        nx.draw_networkx_labels(
            self.G,
            pos,
            labels,
            font_size=11,
            font_family="verdana",
            verticalalignment=verticalalignment,
            horizontalalignment=horizontalalignment,
            bbox=dict(facecolor="white", alpha=0.8, edgecolor="none"),
            font_weight="bold",
            ax=ax,
        )

    def get_legend_handles(self, wrap_width=30):
        def wrap_text(text):
            return "\n".join(textwrap.wrap(text, width=wrap_width))

        return [
            Line2D(
                [0], [0],
                marker="o",
                color="w",
                markerfacecolor=color,
                markersize=14,
                label=wrap_text(label),
            )
            for label, color in self.node_colors.items()
        ]

    def add_network_stats(self, ax, edgelist, pos=(0.02, 0.02), fontsize=16):
        no_users = pd.unique(edgelist[['src', 'target']].values.ravel()).size
        no_edges = self.G.number_of_edges()
        total_weight = sum(d.get("weight", 1) for _, _, d in self.G.edges(data=True))
        no_selfloops = edgelist[(edgelist["src_company"] == edgelist["target_company"])].shape[0]
        no_companies = len(set(edgelist["src_company"]).union(edgelist["target_company"]))
        no_companies_w_inter = (
            edgelist.query("src_company != target_company")[["src_company", "target_company"]]
            .stack()
            .nunique()
        )

        stats_text = [
            r"$\mathit{Network\ topology}$",
            "",
            f"No. of users: {no_users}",
            f"No. of edges: {no_edges}",
            f"Total weight of edges: {total_weight:.2f}",
            f"No. of self-loops (weighted edges): {no_selfloops}",
            f"No. of companies: {no_companies}",
            f"No. of companies with inter-company edges: {no_companies_w_inter}",
        ]

        ax.text(
            *pos,
            "\n".join(stats_text),
            fontsize=fontsize,
            bbox=dict(facecolor="white", alpha=0, edgecolor="none"),
            transform=ax.transAxes,
        )

    def plot(self, layout_type="spring_layout", figsize=(20, 20), seed=1704, k=1.5, title="Network"):
        fig, ax = plt.subplots(figsize=figsize)
        pos = self.layout(layout_type=layout_type, seed=seed, k=k)
        self._draw_nodes(pos, ax)
        self._draw_edges(pos, ax)
        self._draw_labels(pos, ax)
        ax.set_axis_off()

        legend = ax.legend(
            handles=self.get_legend_handles(),
            title=r"$\mathit{Company\ categories}$",
            title_fontsize=16,
            fontsize=16,
            loc="upper right",
        )
        legend._legend_box.align = "left"  # type: ignore

        if self.edgelist is not None:
            self.add_network_stats(ax, self.edgelist)

        plt.title(title, fontsize=20)
        plt.show()

        return fig


class NetworkVisualizer3:
    DEFAULT_NODE_COLORS = {
        "1 Digital and marketing consultancies": '#003f5c',
        "2 Bespoke app companies": '#665191',
        "3 Data-broker- and infrastructure companies": '#d45087',
        "4 Companies with specific digital part/app as part of service/product": '#ff7c43',
    }

    ATTENTION_ACTIONS = {"follows", "stars", "watches"}
    COLLABORATION_ACTIONS = {"forks"}

    FONT_FAMILY = "verdana"
    FONT_SIZE = 11
    FONT_WEIGHT = "bold"

    def __init__(self, G, edgelist=None, graph_type: Literal["attention", "collaboration"] = 'attention'):
        self.G = G
        self.graph_type = graph_type
        self.edgelist = self._filter_edgelist(edgelist)
        self.node_colors = self.DEFAULT_NODE_COLORS

    def _filter_edgelist(self, edgelist):
        if edgelist is None:
            return None
        if self.graph_type == "attention":
            return edgelist[edgelist["action"].isin(self.ATTENTION_ACTIONS)]
        elif self.graph_type == "collaboration":
            return edgelist[edgelist["action"].isin(self.COLLABORATION_ACTIONS)]
        raise ValueError("graph_type must be 'attention' or 'collaboration'")

    def layout(self, layout_type="spring_layout", seed=170497, k=1):
        if layout_type == "spring_layout":
            return nx.spring_layout(self.G, seed=seed, k=k, iterations=50, weight="weight")
        raise ValueError(f"Layout '{layout_type}' is not supported. Try 'spring_layout'.")

    def draw_nodes(self, pos, ax, alpha=1):
        degrees = dict(self.G.degree)
        node_sizes = [500 + 100 * degrees.get(n, 0) for n in self.G.nodes]
        node_colors = [
            self.node_colors.get(self.G.nodes[n].get("label", ""), "#000000") for n in self.G.nodes
        ]

        nx.draw_networkx_nodes(
            self.G,
            pos,
            ax=ax,
            node_color=node_colors,
            node_size=node_sizes,
            alpha=alpha,
            edgecolors="black",
        )

    def _filter_edges(self, edge_type):
        key = f"d_{edge_type}_level"
        if edge_type not in {"inter", "intra"}:
            raise ValueError("Edge type must be either 'inter' or 'intra'")
        return [(u, v, d) for u, v, d in self.G.edges(data=True) if d.get(key) == 1]

    def _log_scale_weights(self, edges):
        if not edges:
            return {}
        log_weights = {(u, v): np.log(d.get("weight", 1) + 1) for u, v, d in edges}
        min_w, max_w = min(log_weights.values()), max(log_weights.values())
        if min_w == max_w:
            return {edge: 2 for edge in log_weights}
        return {
            edge: 1 + (w - min_w) / (max_w - min_w) * 3
            for edge, w in log_weights.items()
        }

    def draw_edges(self, pos, ax, alpha=1):
        inter_edges = self._filter_edges("inter")
        intra_edges = self._filter_edges("intra")
        all_edges = inter_edges + intra_edges

        edge_widths = self._log_scale_weights(all_edges)
        nx.set_edge_attributes(self.G, edge_widths, "edge_width")

        def draw(edge_list, style, arrowsize, connectionstyle=None):
            kwargs = dict(
                G=self.G,
                pos=pos,
                ax=ax,
                edgelist=edge_list,
                width=[edge_widths[(u, v)] for u, v, _ in edge_list],
                edge_color="black",
                alpha=alpha,
                style=style,
                arrows=True,
                arrowstyle="->",
                arrowsize=arrowsize,
            )
            if connectionstyle is not None:
                kwargs["connectionstyle"] = connectionstyle
            nx.draw_networkx_edges(**kwargs)

        if inter_edges:
            draw(inter_edges, style="solid", arrowsize=40, connectionstyle="arc3,rad=0.1")
        if intra_edges:
            draw(intra_edges, style="dashed", arrowsize=20)

    def draw_labels(self, pos, ax, verticalalignment="top", horizontalalignment="right"):
        labels = {n: n for n in self.G.nodes}
        nx.draw_networkx_labels(
            self.G,
            pos,
            labels,
            font_size=self.FONT_SIZE,
            font_family=self.FONT_FAMILY,
            verticalalignment=verticalalignment,
            horizontalalignment=horizontalalignment,
            bbox=dict(facecolor="white", alpha=0.8, edgecolor="none"),
            font_weight=self.FONT_WEIGHT,
            ax=ax,
        )

    def get_legend_handles(self, wrap_width=30):
        def wrap_text(text):
            return "\n".join(textwrap.wrap(text, width=wrap_width))

        return [
            Line2D(
                [0], [0],
                marker="o",
                color="w",
                markerfacecolor=color,
                markersize=14,
                label=wrap_text(label),
            )
            for label, color in self.node_colors.items()
        ]

    def add_network_stats(self, ax, edgelist, pos=(0.02, 0.02), fontsize=16):
        no_users = len(pd.unique(edgelist[['src', 'target']].values.ravel()))
        no_users_edge = int(sum(d.get("weight", 1) for _, _, d in self.G.edges(data=True)))
        no_inter_company_edges_directed = len([(u,v) for u, v, d in self.G.edges(data=True) if d.get("d_inter_level") == 1])
        # Total weight of inter-company edges (user-level, directed)
        inter_company_mask = edgelist['src_company'] != edgelist['target_company']
        no_inter_weight = edgelist[inter_company_mask]['action'].value_counts().sum()

        # Total weight of self-loop edges (src_company == tgt_company)
        selfloop_mask = edgelist['src_company'] == edgelist['target_company']
        no_selfloops = edgelist[selfloop_mask]['action'].value_counts().sum()
        no_companies = len(set(edgelist["src_company"]).union(edgelist["target_company"]))

        stats_text = [
            r"$\mathit{Network\ topology}$",
            "",
            f"No. users: {no_users}",
            f"User edges (directed): {no_users_edge}",
            f"Inter-company edges (directed): {no_inter_company_edges_directed}",
            f"Inter-company GH actions: {no_inter_weight}",
            f"Intra-company GH actions: {no_selfloops}",
            f"No. companies: {no_companies}",
        ]

        ax.text(
            *pos,
            "\n".join(stats_text),
            fontsize=fontsize,
            bbox=dict(facecolor="white", alpha=0, edgecolor="none"),
            transform=ax.transAxes,
        )

    def create_plot(self, layout_type="spring_layout", figsize=(20, 20), seed=1704, k=1.5, title="Network"):
        fig, ax = plt.subplots(figsize=figsize)
        pos = self.layout(layout_type=layout_type, seed=seed, k=k)
        self.draw_nodes(pos, ax)
        self.draw_edges(pos, ax)
        self.draw_labels(pos, ax)
        ax.set_axis_off()

        legend = ax.legend(
            handles=self.get_legend_handles(),
            title=r"$\mathit{Company\ categories}$",
            title_fontsize=16,
            fontsize=16,
            loc="upper right",
        )
        legend._legend_box.align = "left"  # type: ignore

        if self.edgelist is not None:
            self.add_network_stats(ax, self.edgelist)

        plt.title(title, fontsize=20)

        return fig
    
    def save_plot_as_png(self, fig, filename):
        """
        Saves the plot as a PNG file with high resolution.
        Parameters:
        - fig: The matplotlib figure object to save.
        - filename: The name of the file to save the plot as.
        """
        output_folder = fp_main_output / "network_plots"
        output_folder.mkdir(parents=True, exist_ok=True)
        _datetime = datetime.now().strftime("%Y%m%d_%H%M")
        filepath = output_folder / f"{filename}_{_datetime}.png" 
        fig.savefig(filepath, format='png', dpi=300, bbox_inches='tight')
        print(f"Plot saved as {filename}")