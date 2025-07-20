import streamlit as st
import requests

API_BASE_URL = "http://localhost:8000/api/products/"
st.title("Inventory Management Prototype")


def fetch_products():
    """Fetches product data from the API and displays product details in a Streamlit app.

    Makes a GET request to the configured API endpoint to retrieve a list of products.
    For each product, its name, description, price, and stock level are displayed using
    Streamlit components. If the product list is empty or the API request fails, an
    informative message is shown in the app.

    Args:
        None

    Returns:
        None"""
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
    """Displays the current list of products in a Streamlit container.

    Creates a container in the Streamlit app with a subheader "Current Products"
    and retrieves the product list by calling `fetch_products()`.

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
