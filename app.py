import pandas as pd
import streamlit as st
from helper import csv_to_baskets, mine_rules,build_graph, extract_adjacency,create_anchors,create_zones,store_layout,callProcess,callResult,extract_items_from_tabscanner
import pickle
import os

WINDOW_SIZE = 5000  # last N transactions
BASKET_PATH = "basket/baskets.pkl"
LAYOUT_PATH = "layout/store_layout.pkl"
CATEGORY_RULES = {
        "dairy": [
            "milk", "cheese", "butter", "cream", "yogurt", "curd"
        ],
        "bakery": [
            "bread", "buns", "roll", "bakery", "pastry", "cake"
        ],
        "meat": [
            "meat", "chicken", "beef", "pork", "sausage", "turkey", "ham"
        ],
        "produce": [
            "fruit", "vegetable", "onion", "berries", "grapes", "herbs"
        ],
        "snacks": [
            "snack", "chocolate", "candy", "popcorn", "waffles", "nuts"
        ],
        "beverages": [
            "water", "juice", "soda", "coffee", "tea", "beverages"
        ],
        "frozen": [
            "frozen", "ice cream"
        ],
        "household": [
            "cleaner", "detergent", "soap", "napkins", "towels",
            "dishes", "softener", "decalcifier"
        ],
        "alcohol": [
            "wine", "beer", "liquor", "rum", "whisky", "prosecco", "brandy"
        ],
        "pet": [
            "dog", "cat", "pet"
        ],
        "baby": [
            "baby"
        ]
    }
uploaded_file = None
uploaded_image = None
st.set_page_config(page_title="Product Placement", layout="wide")

mode = st.radio(
    "Input type",
    options=["Upload CSV", "Upload Receipt Image"],
    horizontal=True
)

st.divider()

uploaded_file = None
uploaded_image = None

if mode == "Upload CSV":
    with st.container(border=True):
        st.subheader("Upload CSV")
        uploaded_file = st.file_uploader(
            "Product data (CSV)",
            type=["csv"],
            accept_multiple_files=False
        )

        if uploaded_file:
            st.success("CSV uploaded")

elif mode == "Upload Receipt Image":
    with st.container(border=True):
        st.subheader("Upload Receipt Image")
        uploaded_image = st.file_uploader(
            "Receipt image",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=False
        )

        if uploaded_image:
            st.image(uploaded_image, caption="Uploaded Receipt", width=300)
            st.success("Image uploaded")

if uploaded_image is not None:
    with st.spinner("Processing receipt…"):
        token = callProcess(uploaded_image)
        raw_response = callResult(token)
        result = extract_items_from_tabscanner(raw_response)
    new_baskets = [item.lower() for item in result]
    if os.path.exists(BASKET_PATH):
        with open(BASKET_PATH, "rb") as f:
            baskets = pickle.load(f)
        baskets.extend(new_baskets)
        baskets = baskets[-WINDOW_SIZE:]
    else:
        baskets = new_baskets

    with open(BASKET_PATH, "wb") as f:
        pickle.dump(baskets, f)


if uploaded_file is not None:
    new_baskets = csv_to_baskets(uploaded_file)

    if os.path.exists(BASKET_PATH):
        with open(BASKET_PATH, "rb") as f:
            baskets = pickle.load(f)
        baskets.extend(new_baskets)
        baskets = baskets[-WINDOW_SIZE:]
    else:
        baskets = new_baskets

    with open(BASKET_PATH, "wb") as f:
        pickle.dump(baskets, f)

    with st.spinner("Processing data…"):
        rules = mine_rules(baskets)
        G = build_graph(baskets, rules)
        adjacency = extract_adjacency(G)
        anchors = create_anchors(adjacency)
        final_zones = create_zones(adjacency,anchors,CATEGORY_RULES)
        store_layout = store_layout(final_zones)

    with open(LAYOUT_PATH, "wb") as f:
        pickle.dump(store_layout, f)


if os.path.exists(LAYOUT_PATH):
    with open(LAYOUT_PATH, "rb") as f:
        store_layout = pickle.load(f)
    for zone, shelves in store_layout.items():
        with st.expander(zone.replace("_", " ").title()):
            for i, shelf in enumerate(shelves):
                st.markdown(f"**Shelf {i + 1}**")
                cols = st.columns(len(shelf))
                for col, product in zip(cols, shelf):
                    col.markdown(
                        f"""
                        <div style="
                            border:1px solid #ccc;
                            padding:10px;
                            text-align:center;
                            border-radius:6px;
                            background:#f9f9f9;
                            color:black;
                            margin-bottom: 10px;
                            margin-top: 10px;
                        ">
                            {product}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )