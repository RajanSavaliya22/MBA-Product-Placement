import pandas as pd
from collections import defaultdict

def csv_to_baskets(
    csv_path,
    products_col=None,
    product_prefix="product"
):
    """
    Converts transaction CSV into basket format.

    Parameters
    ----------
    csv_path : str
        Path to CSV file
    products_col : str or None
        Name of column containing comma-separated products.
        Use None for wide format.
    product_prefix : str
        Prefix for wide product columns (default: 'product')

    Returns
    -------
    baskets : list[list[str]]
        List of baskets (each basket = list of products)
    """

    df = pd.read_csv(csv_path)

    # CASE 1 — single column with comma-separated products
    if products_col:
        baskets = (
            df[products_col]
            .dropna()
            .apply(
                lambda x: [
                    p.strip().lower()
                    for p in str(x).split(",")
                    if p.strip()
                ]
            )
            .tolist()
        )
        return baskets

    # CASE 2 — wide format (Product 1, Product 2, ...)
    product_cols = [
        c for c in df.columns
        if c.lower().startswith(product_prefix.lower())
    ]

    baskets = (
        df[product_cols]
        .apply(
            lambda row: [
                str(item).strip().lower()
                for item in row
                if pd.notna(item)
            ],
            axis=1
        )
        .tolist()
    )

    return baskets


# ------------------------------------------------------------------

from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import fpgrowth, association_rules

def mine_rules(baskets):
    te = TransactionEncoder()
    te_array = te.fit(baskets).transform(baskets)
    df = pd.DataFrame(te_array, columns=te.columns_)

    freq = fpgrowth(df, min_support=0.01, use_colnames=True)

    rules = association_rules(
        freq,
        metric="lift",
        min_threshold=1.3
    )

    return rules

# -----------------------------------------------------

import networkx as nx

def build_graph(baskets, rules):
    G = nx.Graph()

    for basket in baskets:
        for p in basket:
            G.add_node(p)

    for _, row in rules.iterrows():
        if row["lift"] >= 1.3:
            for a in row["antecedents"]:
                for c in row["consequents"]:
                    G.add_edge(a, c, weight=row["lift"])

    return G

# -------------------------------------------------------------

def extract_adjacency(G, max_neighbors=5):
    adjacency = {}

    for node in G.nodes:
        neighbors = sorted(
            G[node].items(),
            key=lambda x: x[1]["weight"],
            reverse=True
        )
        adjacency[node] = [n for n, _ in neighbors[:max_neighbors]]

    return adjacency

# -------------------------------------------------------------------------

def create_anchors(adjacency):
    ANCHOR_THRESHOLD = 3

    anchors = [
        p for p, neighbors in adjacency.items()
        if len(neighbors) >= ANCHOR_THRESHOLD
    ]

    return anchors

# -------------------------------------------------------------------

def assign_category(product,CATEGORY_RULES):
    p = product.lower()
    for category, keywords in CATEGORY_RULES.items():
        if any(k in p for k in keywords):
            return category
    return "other"

# ----------------------------------------------------------------------------

def create_zones(adjacency,anchors,CATEGORY_RULES):
    zones = {}

    for anchor in anchors:
        zones[anchor] = [anchor] + adjacency[anchor]

    assigned = set()
    final_zones = {}

    for anchor, products in zones.items():
        clean = []
        for p in products:
            if p not in assigned:
                clean.append(p)
                assigned.add(p)
        if clean:
            final_zones[anchor] = clean

    # assign category to unassigned products
    all_products = set(adjacency.keys())
    unassigned = all_products - assigned

    category_zones = defaultdict(list)

    for product in unassigned:
        category = assign_category(product,CATEGORY_RULES)
        category_zones[category].append(product)

    for category, products in category_zones.items():
        final_zones[f"category_{category}"] = products

    return final_zones


# -----------------------------------------------------------------------

def store_layout(final_zones, SHELF_CAPACITY=6):
    store_layout = {}

    for zone, products in final_zones.items():
        shelves = []
        for i in range(0, len(products), SHELF_CAPACITY):
            shelves.append(products[i:i + SHELF_CAPACITY])
        store_layout[zone] = shelves

    return store_layout



# --------------------------------------------------------------------
import requests
import json

API_KEY = "Ji3JXMyIG5LFmvmMvw53WRMGPLj0V6IXGpYlBT5LQ833YfcC5zC6QzqcxNdzWwvj"
def callProcess(image):
    endpoint = "https://api.tabscanner.com/api/2/process"

    payload = {"documentType": "receipt"}

    files = {
        "file": (
            image.name,
            image.getvalue(),
            image.type
        )
    }

    headers = {
        "apikey": API_KEY
    }

    response = requests.post(
        endpoint,
        files=files,
        data=payload,
        headers=headers
    )

    result = response.json()
    return result["token"]



# ----------------------------------------------------
import time

def callResult(token):
    url = "https://api.tabscanner.com/api/result/{0}"
    endpoint = url.format(token)

    headers = {'apikey': API_KEY}

    while True:
        response = requests.get(endpoint, headers=headers)
        result = json.loads(response.text)

        if result.get("status") == "done":
            return result

        if result.get("status") == "failed":
            raise RuntimeError(result)

        time.sleep(2)  # mandatory wait


def extract_items_from_tabscanner(result_json):
    """
    Extract grocery items from Tabscanner OCR result
    Returns a basket (list of product names)
    """

    items = result_json["result"]["lineItems"]

    basket = []

    for item in items:
        name = item.get("descClean", "").strip().lower()
        qty = item.get("qty", 0)

        # filter noise
        if not name:
            continue
        if any(x in name for x in ["total", "subtotal", "payment", "vat"]):
            continue

        basket.append(name)

    # remove duplicates
    basket = list(set(basket))

    return basket
