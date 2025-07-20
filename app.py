import streamlit as st
import pandas as pd
import requests

API_BASE_URL = "http://localhost:8000/api/products/"
if "view_mode" not in st.session_state:
    st.session_state["view_mode"] = "View Products"
st.title("📦 Inventory Management System")


def fetch_products():
    """Fetches product data from the API endpoint specified by API_BASE_URL.

    Makes a GET request to the API and returns the JSON-decoded response containing product information. If the request is unsuccessful (i.e., status code is not 200), an error message is displayed using Streamlit and an empty list is returned.

    Returns:
        list or dict: The product data retrieved from the API, or an empty list if the request fails."""
    response = requests.get(API_BASE_URL)
    if response.status_code == 200:
        return response.json()
    else:
        st.error("Failed to fetch products.")
        return []


def display_products(products):
    """Displays a list of products in an interactive data table and issues stock level warnings.

    Args:
        products (list of dict): List of product dictionaries. Each dictionary must contain the keys
            'id', 'name', 'description', 'price', 'stock_level', and 'min_stock_level'.

    Returns:
        None

    This function uses Streamlit to display the product information in a tabular format. It also
    generates warning messages for any products whose current stock level is less than or equal to
    their minimum stock threshold."""
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
    """Displays a form for inputting new product details and submits them to the backend API.

    When the form is submitted, sends a POST request with the product data to the configured API endpoint (`API_BASE_URL`). On success (HTTP 201), shows a success message and updates `st.session_state["view_mode"]` to "View Products"; on failure, displays an error message.

    Uses Streamlit for UI components and relies on the global variables `API_BASE_URL` and `st.session_state`.

    Args:
        None

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
    """Displays a Streamlit interface for selecting and updating an existing product's details.

    Retrieves all products using `fetch_products()`, lets the user select one via a selectbox, and fetches its current details from the backend API. Presents a form pre-populated with product info (name, description, price, stock level, and minimum stock level) for editing. On form submission, sends an update request to the API. Displays success or error messages based on the update outcome and updates the session state's view mode upon success.

    Uses `API_BASE_URL` for API endpoints and `requests` for HTTP calls.

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
    """Prompts the user to select and delete a product from the current product list.

    Fetches products and displays them for selection in a dropdown. Allows the user to confirm deletion with a button click. Shows a warning if no products exist. On successful deletion, updates the session state to switch the view mode to "View Products"; otherwise, displays an error message.

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
