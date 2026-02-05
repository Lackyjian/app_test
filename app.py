import streamlit as st
from datetime import datetime, timezone
import pandas as pd
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "client" not in st.session_state:
    st.session_state.client = None
if st.session_state.authenticated and st.session_state.client is not None:
    db = st.session_state.client["c_app"]

    cash_transactions_db = db["cash_transactions"]
    products_db = db["products"]

    cash_transactions_df = pd.DataFrame(list(cash_transactions_db.find()))
    products = pd.DataFrame(list(products_db.find()))
    if cash_transactions_df.empty == False:
        if cash_transactions_df['DateTime'].dtype == 'O':
            cash_transactions_df['DateTime'] = pd.to_datetime(cash_transactions_df['DateTime'], errors='coerce')

def dataframe_from_mongo(data, collection):
    record = data.to_dict(orient='records')
    print(record)   
    collection.insert_one(record)

def cash_Records():
    st.title('Cash Transactions')
    tab1, tab2, tab3 = st.tabs(['Add Transaction', 'View Transactions', 'Customize'])
    with tab1:
        if 'rate' not in st.session_state:
            st.session_state.rate = 0
        if 'total' not in st.session_state:
            st.session_state.total = 0
        if 'paid_amount' not in st.session_state:
            st.session_state.paid_amount = 0
        if products.empty:
            st.warning("No products available. Please add products in the Customize tab.")
        else:
            cash_trasactions_form = st.form("cash_transactions")
            with cash_trasactions_form:
                if cash_transactions_df.empty:
                    id = 101
                else:
                    id = cash_transactions_df['ID'].max() + 1
                name = st.text_input("Name (optional)").lower()
                products_list = products['Product'].tolist()
                product = st.selectbox("Select Product", products_list)
                # rate = st.number_input("Rate", value = products[products['Product'] == product]['Rate'].values[0])
                amount = st.number_input("Amount(in Kg)", min_value=0.0)
                submit = st.form_submit_button("Submit")
                rate = products[products['Product'] == product]['Rate'].values[0]
            if submit:
                total = rate * amount
                st.write('Please confirm the details and edit if necessary and enter the paid amount')
                st.write('Product: ', product)
                st.write('Rate: ', rate)
                st.write('Amount: ', amount)
                st.write('Total: ', total)
                st.session_state.rate = rate
                st.session_state.total = total
            extended_form = st.form("extended_form")
            with extended_form:
                rate_updated = st.number_input("Rate", value = st.session_state.rate)
                total_updated = st.number_input("Total", value = st.session_state.total)
                paid_amount = st.number_input("Paid", value = 0)
                submit2 = st.form_submit_button("Confirm Transaction")
            if submit2:
                balance = total_updated - paid_amount
                st.success("Transaction added!")
                if name != '':
                    st.write("Name:", name)
                st.write("Product:", product)
                st.write("Rate:", rate_updated)
                st.write("Amount:", amount, 'kg')
                st.write("Total:", total_updated)
                st.write("Paid Amount:", paid_amount)
                st.write("Balance:", balance)
                date_time = datetime.now()
                new_transaction = pd.DataFrame({
                    'ID': [id],
                    'DateTime': [date_time],
                    'Name': [name],
                    'Product': [product],
                    'Rate': [rate_updated],
                    'Amount': [amount],
                    'Total': [total_updated],
                    'Paid_amount': [paid_amount],
                    'Balance': [balance]
                })
                cash_transactions_db.insert_one(new_transaction.to_dict(orient='records')[0])


    with tab2:
        st.header('Dashboard')
        if cash_transactions_df.empty:
            st.warning("No transactions to display")
        elif products.empty:
            st.warning("No products available. Please add products in the Customize tab.")
        else:
            prod_list = products['Product'].unique().tolist()
            prod_list.insert(0, 'All')
            col1, col2, col3 = st.columns(3)
            today = datetime.now().date()
            with col1:
                selected_product = st.selectbox("Select product to view", prod_list)
            with col2:
                lower_date = st.date_input("Start date", value=today)
            with col3:
                upper_date = st.date_input("End date", value=today)
            
            start_date, end_date = lower_date, upper_date
            start = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
            end = datetime.combine(end_date, datetime.min.time(), tzinfo=timezone.utc)
            st.write('Showing data for transactions between',start, 'and ', end)
            query = {
                "DateTime": {
                    "$gte": start,
                    "$lt": end
                }
            }

            docs = list(cash_transactions_db.find(query))
            df = pd.DataFrame(docs)
            if df.empty:
                st.warning("No transactions in the selected date range")
            else:
                if selected_product != 'All':
                    filtered_df = df[df['Product'] == selected_product]
                else:
                    filtered_df = df.copy()
                st.write('Total Sale: ', filtered_df['Total'].sum())
                st.write('Total Paid Amount: ', filtered_df['Paid_amount'].sum())
                st.write('Total Balance: ', filtered_df['Balance'].sum())
                st.divider()
                sales_per_product = (
                                filtered_df
                                .groupby("Product", as_index=False)["Amount"]
                                .sum()
                                )
                if sales_per_product.empty:
                    st.warning("No sales data to display")
                else:
                    st.bar_chart(sales_per_product, x = 'Product', y = 'Amount', height=400,)
                    st.divider()
                    # filtered_df['Datetime'] = pd.to_datetime(filtered_df['Date'].astype(str) + ' ' + filtered_df['Time'].astype(str))
                    filtered_df['DateTime'] = pd.to_datetime(filtered_df['DateTime'], utc=True)
                    filtered_df['DateTime_IST'] = filtered_df['DateTime'].dt.tz_convert('Asia/Kolkata')
                    hourly_sales = (
                                filtered_df
                                .groupby(filtered_df['DateTime_IST'].dt.hour)['Total']
                                .sum()
                                )
                    st.bar_chart(hourly_sales, height=400)
                    st.divider()
                    st.write('Transactions history:')
                    # filtered_df = filtered_df.drop(columns=['DateTime'])
                    st.write(filtered_df)


    with tab3:

        show_products = st.button("Show products and rates")
        if show_products:
            st.write(products)

        st.divider()

        add_product_form = st.form("Add product")
        with add_product_form:
            new_product = st.text_input("Product name")
            new_rate = st.number_input("Rate", min_value=0.0)
            submit_product = st.form_submit_button("Add Product")
        if submit_product:
            if products.empty:
                new_entry = pd.DataFrame({
                    'Product': [new_product],
                    'Rate': [new_rate]
                })
                products_db.insert_one(new_entry.to_dict(orient='records')[0])
                # new_entry.to_csv('products.csv', index=False)
                st.success("Product added")
            else:
                if new_product in products['Product'].values:
                    st.error("Product already exists")
                else:
                    new_entry = pd.DataFrame({
                        'Product': [new_product],
                        'Rate': [new_rate]
                    })
                    products_db.insert_one(new_entry.to_dict(orient='records')[0])
                    st.success("Product added")
        
        st.divider()
        if products.empty:
            st.warning("No products available to edit or delete.")
        else:

            edit_product_form = st.form("Edit a product")
            with edit_product_form:
                product_to_edit = st.selectbox("Select product to edit", products['Product'].tolist())
                new_rate = st.number_input("New rate", min_value=0.0)
                submit_edit = st.form_submit_button("Edit Product")

                if submit_edit:
                    products_db.update_one({'Product': product_to_edit}, {'$set': {'Rate': new_rate}})
                    st.success("Product updated")
            delete_product_form = st.form("Delete a product")
            with delete_product_form:
                product_to_delete = st.selectbox("Select product to delete", products['Product'].tolist())
                submit_delete = st.form_submit_button("Delete Product")

                if submit_delete:
                    if product_to_delete not in products['Product'].values:
                        st.error("Product does not exist")
                    else:
                        products_db.delete_one({'Product': product_to_delete})
                        st.success("Product deleted")

def login():
    username = st.text_input("Enter MongoDB username")
    password = st.text_input("Enter MongoDB password", type="password")
    login_button = st.button("Login to MongoDB")
    if login_button:
        with st.spinner("Connecting to MongoDB..."):
            uri = f"mongodb+srv://{username}:{password}@cluster0.xsjedbg.mongodb.net/?appName=Cluster0" 
            client = MongoClient(uri)
            
        try:
            client.admin.command('ping')
            st.success("Connected to MongoDB!")
            st.session_state.authenticated = True
            st.session_state.client = client
            st.rerun()
        except Exception as e:
            st.error(f"Failed to connect to MongoDB: {e}")
def app():
    bar = st.sidebar

    bar.write("Select option")

    # options = ["A", "Cash Records", "C"]
    options = ['Cash Records']

    box = bar.selectbox("Pick an option", options)

    if box == "Cash Records":
        cash_Records()
    
    logout = bar.button("Logout")
    if logout:
        st.session_state.authenticated = False
        st.rerun()


if st.session_state.authenticated:
    app()
else:
    login()




