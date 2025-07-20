import streamlit as st
import requests

API_BASE_URL = "http://localhost:8000/api/products/"
st.title("Inventory Management Prototype")


def fetch_products():
    """Fetches product data from the API and displays each product's details using Streamlit.

    Retrieves the list of products from the configured API endpoint. For each product,
    displays its name, description, price, and stock level. If no products are found or
    if the API request fails, appropriate messages are shown in the Streamlit app."""
    response = requests.get(API_BASE_URL)
    if response.status_code == 200:
        products = response.json()
        if products:
            for product in products:
                st.write(f"**Name:** {product['name']}")
                st.write(f"Description: {product['description']}")
                st.write(f"Price: ${product['price']}")
                st.write(f"Stock Level: {product['stock_level']}")
                st.write("---")
        else:
            st.info("No products found.")
    else:
        st.error("Failed to fetch products")


def display_product_list():
    """Displays the current list of products within a Streamlit container.

    This function creates a container in the Streamlit app, adds a subheader titled
    "Current Products", and calls `fetch_products()` to retrieve and display the product list.

    Args:
        None

    Returns:
        None"""
    with st.container():
        st.subheader("Current Products")
        fetch_products()


placeholder = st.empty()
with placeholder.container():
    display_product_list()
if st.button("Update Stock List"):
    placeholder.empty()
    with placeholder.container():
        display_product_list()
st.header("Add New Product")
name = st.text_input("Product Name")
description = st.text_area("Description")
price = st.number_input("Price", min_value=0.0, step=10.0)
stock_level = st.number_input("Stock Level", min_value=0)
if st.button("Add Product"):
    product_data = {
        "name": name,
        "description": description,
        "price": price,
        "stock_level": stock_level,
    }
    response = requests.post(API_BASE_URL, json=product_data)
    if response.status_code == 201:
        st.success("Product added successfully!")
        placeholder.empty()
        with placeholder.container():
            display_product_list()
    else:
        st.error("Failed to add product.")
