import streamlit as st
import pandas as pd
import requests

API_BASE_URL = "http://localhost:8000/api/products/"
if "view_mode" not in st.session_state:
    st.session_state["view_mode"] = "View Products"
st.title("📦 Inventory Management System")


def fetch_products():
    """Fetches product data from the API endpoint defined by API_BASE_URL.

    Makes a GET request to the specified API URL and returns the product data as a JSON-decoded list or dictionary if the request is successful (HTTP status 200). If the request fails, displays an error message using Streamlit and returns an empty list.

    Returns:
        list or dict: The product data retrieved from the API, or an empty list if the request fails."""
    response = requests.get(API_BASE_URL)
    if response.status_code == 200:
        return response.json()
    else:
        st.error("Failed to fetch products.")
        return []


def display_products(products):
    """Displays a list of products in a data table with stock level warnings.

    Args:
        products (list of dict): A list where each dict represents a product with keys
            including 'id', 'name', 'description', 'price', 'stock_level', and 'min_stock_level'.

    Returns:
        None"""
    if not products:
        st.warning("No products available.")
        return
    df = pd.DataFrame(products)
    df = df[["id", "name", "description", "price", "stock_level", "min_stock_level"]]
    st.dataframe(df, use_container_width=True)
    for product in products:
        stock_level = product["stock_level"]
        min_stock = product["min_stock_level"]
        if stock_level <= min_stock:
            st.warning(
                f"⚠️ Low stock alert for {product['name']} (Stock Level: {stock_level})"
            )


def create_product():
    """Displays a form to input new product details and submits them to the backend API.

    When the form is submitted, the function sends a POST request with the product data to the configured API endpoint. If the product is added successfully, it shows a success message and updates the app's view state; otherwise, it displays an error.

    Uses Streamlit for UI elements and interacts with global variables such as API_BASE_URL and st.session_state.

    No arguments.

    Returns:
        None"""
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
    """Displays an interface to select and update an existing product's details.

    Fetches the list of products and allows the user to pick one for editing via a Streamlit selectbox. Upon selection, it fetches the product details from the API and displays a form pre-filled with current product information. Users can modify fields such as name, description, price, stock level, and minimum stock level. Submitting the form sends an update request to the backend API. Success or failure messages are shown accordingly, and the view mode in the session state is updated on success.

    Uses:
    - `fetch_products()` to retrieve all products.
    - `API_BASE_URL` for API requests.
    - Streamlit (`st`) for UI rendering and user interaction.
    - `requests` for HTTP calls.

    Returns:
        None"""
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
            name = st.text_input("Product Name", product["name"])
            description = st.text_area("Description", product["description"])
            price = st.number_input(
                "Price", min_value=0.0, value=float(product["price"]), step=1.0
            )
            stock_level = st.number_input(
                "Stock Level", min_value=0, value=product["stock_level"]
            )
            min_stock = st.number_input(
                "Min Stock Level", min_value=0, value=product["min_stock_level"]
            )
            submitted = st.form_submit_button("Update Product")
            if submitted:
                updated_data = {
                    "name": name,
                    "description": description,
                    "price": price,
                    "stock_level": stock_level,
                    "min_stock_level": min_stock,
                }
                response = requests.put(
                    f"{API_BASE_URL}{product_id}/", json=updated_data
                )
                if response.status_code == 200:
                    st.success("Product updated successfully!")
                    st.session_state["view_mode"] = "View Products"
                else:
                    st.error("Failed to update product.")


def delete_product():
    """Prompts the user to select and delete a product from the available list.

    Fetches the current list of products, displays them in a dropdown for selection,
    and provides a button to confirm deletion. If no products exist, a warning is shown.
    Upon deletion, updates the view mode to "View Products" on success or shows an error message otherwise.

    Args:
        None

    Returns:
        None"""
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
    action = st.selectbox(
        "Select Action",
        ["View Products", "Add Product", "Update Product", "Delete Product"],
    )
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
