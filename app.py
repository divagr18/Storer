import streamlit as st
import pandas as pd
import requests

API_BASE_URL = "http://localhost:8000/api/products/"

if "view_mode" not in st.session_state:
    st.session_state["view_mode"] = "View Products"

st.title("📦 Inventory Management System")

def fetch_products():
    response = requests.get(API_BASE_URL)
    if response.status_code == 200:
        return response.json()
    else:
        st.error("Failed to fetch products.")
        return []

def display_products(products):
    if not products:
        st.warning("No products available.")
        return
    df = pd.DataFrame(products)
    df = df[["id", "name", "description", "price", "stock_level", "min_stock_level" ]]
    st.dataframe(df, use_container_width=True)

    for product in products:
        stock_level = product['stock_level']
        min_stock = product['min_stock_level']
        if stock_level <= min_stock:
            st.warning(f"⚠️ Low stock alert for {product['name']} (Stock Level: {stock_level})")
    

def create_product():
    with st.form("Create Product"):
        name = st.text_input("Product Name")
        description = st.text_area("Description")
        price = st.number_input("Price", min_value=0.0, step=1.0)
        stock_level = st.number_input("Stock Level", min_value=0)
        min_stock = st.number_input("Min Stock Level", min_value=0, step=1)
        submitted = st.form_submit_button("Add Product")

        if submitted:
            product_data = {
                "name": name,
                "description": description,
                "price": price,
                "stock_level": stock_level,
                "min_stock_level": min_stock,
            }
            response = requests.post(API_BASE_URL, json=product_data)
            if response.status_code == 201:
                st.success("Product added successfully!")
                st.session_state["view_mode"] = "View Products"
            else:
                st.error("Failed to add product.")

def update_product():
    products = fetch_products()
    if not products:
        st.warning("No products to update.")
        return

    product_names = [f"{p['name']} (ID: {p['id']})" for p in products]
    selected_product = st.selectbox("Select a Product to Update", product_names)

    if selected_product:
        product_id = int(selected_product.split("(ID: ")[-1].rstrip(")"))
        product_response = requests.get(f"{API_BASE_URL}{product_id}/")
        product = product_response.json()

        with st.form(f"Update Product {product_id}"):
            name = st.text_input("Product Name", product['name'])
            description = st.text_area("Description", product['description'])
            price = st.number_input("Price", min_value=0.0, value=float(product['price']), step=1.0)
            stock_level = st.number_input("Stock Level", min_value=0, value=product['stock_level'])
            min_stock = st.number_input("Min Stock Level", min_value=0, value=product['min_stock_level'])
            submitted = st.form_submit_button("Update Product")

            if submitted:
                updated_data = {
                    "name": name,
                    "description": description,
                    "price": price,
                    "stock_level": stock_level,
                    "min_stock_level": min_stock,
                }
                response = requests.put(f"{API_BASE_URL}{product_id}/", json=updated_data)
                if response.status_code == 200:
                    st.success("Product updated successfully!")
                    st.session_state["view_mode"] = "View Products"
                else:
                    st.error("Failed to update product.")

def delete_product():
    products = fetch_products()
    if not products:
        st.warning("No products to delete.")
        return

    product_names = [f"{p['name']} (ID: {p['id']})" for p in products]
    selected_product = st.selectbox("Select a Product to Delete", product_names)

    if selected_product and st.button("Delete Product"):
        product_id = int(selected_product.split("(ID: ")[-1].rstrip(")"))
        response = requests.delete(f"{API_BASE_URL}{product_id}/")
        if response.status_code == 204:
            st.success("Product deleted successfully!")
            st.session_state["view_mode"] = "View Products"
        else:
            st.error("Failed to delete product.")

with st.sidebar:
    st.header("Manage Products")
    action = st.selectbox("Select Action", ["View Products", "Add Product", "Update Product", "Delete Product"])
    st.session_state["view_mode"] = action

if st.session_state["view_mode"] == "View Products":
    products = fetch_products()
    display_products(products)
elif st.session_state["view_mode"] == "Add Product":
    create_product()
elif st.session_state["view_mode"] == "Update Product":
    update_product()
elif st.session_state["view_mode"] == "Delete Product":
    delete_product()
