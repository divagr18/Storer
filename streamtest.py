import streamlit as st
import requests

# Set the API URL
API_BASE_URL = "http://localhost:8000/api/products/"

st.title("Inventory Management Prototype")

# Fetch and display products
def fetch_products():
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

# Clear the product display area for refresh
def display_product_list():
    with st.container():
        st.subheader("Current Products")
        fetch_products()

# Initial display
placeholder = st.empty()
with placeholder.container():
    display_product_list()

# Fetch products when button is clicked
if st.button("Update Stock List"):
    placeholder.empty()  # Clear previous product display
    with placeholder.container():
        display_product_list()

# Add new product
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
        placeholder.empty()  # Clear and refresh the list
        with placeholder.container():
            display_product_list()
    else:
        st.error("Failed to add product.")
