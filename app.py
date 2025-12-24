import streamlit as st
import sqlite3
import hashlib
import os
from datetime import datetime
import pandas as pd

# Page config must be first
st.set_page_config(page_title="Money Records Manager", layout="wide")

# Database setup
DB_NAME = "money_records.db"

def hash_password(password):
    """Hash password using PBKDF2"""
    salt = b'money_records_salt_2024'
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000).hex()

def init_db():
    """Initialize database tables"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  email TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL)''')
    
    # Customers table
    c.execute('''CREATE TABLE IF NOT EXISTS customers
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  name TEXT NOT NULL,
                  FOREIGN KEY (user_id) REFERENCES users(id))''')
    
    # Transactions table
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  customer_id INTEGER NOT NULL,
                  date_time TEXT NOT NULL,
                  type TEXT NOT NULL,
                  total_amount REAL DEFAULT 0,
                  amount_received REAL DEFAULT 0,
                  amount_left REAL DEFAULT 0,
                  note TEXT,
                  FOREIGN KEY (customer_id) REFERENCES customers(id))''')
    
    # Create default admin user if not exists
    try:
        c.execute("SELECT * FROM users WHERE email = ?", ('admin@example.com',))
        if not c.fetchone():
            hashed = hash_password('admin123')
            c.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                      ('Admin User', 'admin@example.com', hashed))
            conn.commit()
    except:
        pass
    
    conn.close()

# Initialize database only once
if 'db_initialized' not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'user_name' not in st.session_state:
    st.session_state.user_name = None
if 'selected_customer' not in st.session_state:
    st.session_state.selected_customer = None
if 'show_add_form' not in st.session_state:
    st.session_state.show_add_form = False
if 'edit_transaction_id' not in st.session_state:
    st.session_state.edit_transaction_id = None
if 'show_add_customer' not in st.session_state:
    st.session_state.show_add_customer = False

def register_user(name, email, password):
    """Register a new user"""
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        hashed = hash_password(password)
        c.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                  (name, email, hashed))
        user_id = c.lastrowid
        conn.commit()
        conn.close()
        return True, user_id, name
    except sqlite3.IntegrityError:
        return False, None, None

def login_user(email, password):
    """Login user"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    hashed = hash_password(password)
    c.execute("SELECT id, name FROM users WHERE email = ? AND password = ?",
              (email, hashed))
    result = c.fetchone()
    conn.close()
    if result:
        return True, result[0], result[1]
    return False, None, None

def get_customers(user_id):
    """Get all customers for a user"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, name FROM customers WHERE user_id = ? ORDER BY name",
              (user_id,))
    customers = c.fetchall()
    conn.close()
    return customers

def add_customer(user_id, name):
    """Add a new customer"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO customers (user_id, name) VALUES (?, ?)",
              (user_id, name))
    conn.commit()
    conn.close()

def get_transactions(customer_id, month_filter=None):
    """Get all transactions for a customer"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    if month_filter and month_filter != "All Months":
        c.execute("""SELECT id, date_time, type, total_amount, amount_received, amount_left, note 
                     FROM transactions 
                     WHERE customer_id = ? AND strftime('%Y-%m', date_time) = ?
                     ORDER BY date_time DESC""",
                  (customer_id, month_filter))
    else:
        c.execute("""SELECT id, date_time, type, total_amount, amount_received, amount_left, note 
                     FROM transactions 
                     WHERE customer_id = ?
                     ORDER BY date_time DESC""",
                  (customer_id,))
    
    transactions = c.fetchall()
    conn.close()
    return transactions

def add_transaction(customer_id, trans_type, total_amount, amount_received, amount_left, note):
    """Add a new transaction"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    date_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute("""INSERT INTO transactions (customer_id, date_time, type, total_amount, amount_received, amount_left, note)
                 VALUES (?, ?, ?, ?, ?, ?, ?)""",
              (customer_id, date_time, trans_type, total_amount, amount_received, amount_left, note))
    conn.commit()
    conn.close()

def update_transaction(trans_id, trans_type, total_amount, amount_received, amount_left, note):
    """Update an existing transaction"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""UPDATE transactions 
                 SET type = ?, total_amount = ?, amount_received = ?, amount_left = ?, note = ?
                 WHERE id = ?""",
              (trans_type, total_amount, amount_received, amount_left, note, trans_id))
    conn.commit()
    conn.close()

def delete_transaction(trans_id):
    """Delete a transaction"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM transactions WHERE id = ?", (trans_id,))
    conn.commit()
    conn.close()

def get_available_months(customer_id):
    """Get list of months with transactions"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""SELECT DISTINCT strftime('%Y-%m', date_time) as month
                 FROM transactions 
                 WHERE customer_id = ?
                 ORDER BY month DESC""",
              (customer_id,))
    months = [row[0] for row in c.fetchall()]
    conn.close()
    return months

def calculate_summary(transactions):
    """Calculate total received, given, and balance"""
    total_received = sum(t[3] for t in transactions if t[2] == 'Received')
    total_given = sum(t[3] for t in transactions if t[2] == 'Given')
    balance = total_received - total_given
    return total_received, total_given, balance

# Main App
# No need for set_page_config here as it's already at the top

# AUTH SCREEN
if not st.session_state.logged_in:
    st.title("💰 Money Records Manager")
    st.markdown("### Welcome! Please login or register to continue.")
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        st.subheader("Login")
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submit = st.form_submit_button("Login")
            
            if submit:
                if email and password:
                    success, user_id, user_name = login_user(email, password)
                    if success:
                        st.session_state.logged_in = True
                        st.session_state.user_id = user_id
                        st.session_state.user_name = user_name
                        st.rerun()
                    else:
                        st.error("Invalid email or password")
                else:
                    st.warning("Please fill in all fields")
        
        st.info("💡 Default login: admin@example.com / admin123")
    
    with tab2:
        st.subheader("Register")
        with st.form("register_form"):
            name = st.text_input("Name", key="reg_name")
            email = st.text_input("Email", key="reg_email")
            password = st.text_input("Password", type="password", key="reg_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm")
            submit = st.form_submit_button("Register")
            
            if submit:
                if name and email and password and confirm_password:
                    if password != confirm_password:
                        st.error("Passwords do not match")
                    elif len(password) < 6:
                        st.error("Password must be at least 6 characters")
                    else:
                        success, user_id, user_name = register_user(name, email, password)
                        if success:
                            st.session_state.logged_in = True
                            st.session_state.user_id = user_id
                            st.session_state.user_name = user_name
                            st.success("Registration successful!")
                            st.rerun()
                        else:
                            st.error("Email already exists")
                else:
                    st.warning("Please fill in all fields")

# CUSTOMER SCREEN
else:
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title(f"👋 Welcome, {st.session_state.user_name}!")
    with col2:
        if st.button("Logout", type="secondary"):
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.session_state.user_name = None
            st.session_state.selected_customer = None
            st.rerun()
    
    st.markdown("---")
    
    # Customer Selection
    col1, col2 = st.columns([3, 1])
    
    with col1:
        customers = get_customers(st.session_state.user_id)
        customer_options = ["-- Select Customer --"] + [c[1] for c in customers]
        customer_dict = {c[1]: c[0] for c in customers}
        
        selected = st.selectbox(
            "Select Customer",
            customer_options,
            key="customer_select"
        )
        
        if selected != "-- Select Customer --":
            st.session_state.selected_customer = customer_dict[selected]
        else:
            st.session_state.selected_customer = None
    
    with col2:
        st.write("")
        st.write("")
        if st.button("➕ Add New Customer", type="primary"):
            st.session_state.show_add_customer = True
    
    # Add Customer Form
    if st.session_state.show_add_customer:
        st.markdown("### Add New Customer")
        with st.form("add_customer_form"):
            new_customer_name = st.text_input("Customer Name")
            col1, col2 = st.columns(2)
            with col1:
                save_customer = st.form_submit_button("💾 Save", type="primary")
            with col2:
                cancel_customer = st.form_submit_button("❌ Cancel")
            
            if save_customer:
                if new_customer_name.strip():
                    add_customer(st.session_state.user_id, new_customer_name.strip())
                    st.success(f"Customer '{new_customer_name}' added!")
                    st.session_state.show_add_customer = False
                    st.rerun()
                else:
                    st.error("Please enter a customer name")
            
            if cancel_customer:
                st.session_state.show_add_customer = False
                st.rerun()
    
    # Show transactions if customer is selected
    if st.session_state.selected_customer:
        st.markdown("---")
        
        # Month Filter
        available_months = get_available_months(st.session_state.selected_customer)
        if available_months:
            month_options = ["All Months"] + available_months
            selected_month = st.selectbox("Filter by Month", month_options, key="month_filter")
        else:
            selected_month = None
        
        # Get transactions
        transactions = get_transactions(st.session_state.selected_customer, selected_month)
        
        # Summary
        if transactions:
            total_received, total_given, balance = calculate_summary(transactions)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Received", f"₨ {total_received:,.2f}")
            with col2:
                st.metric("Total Given", f"₨ {total_given:,.2f}")
            with col3:
                balance_color = "normal" if balance >= 0 else "inverse"
                st.metric("Balance", f"₨ {balance:,.2f}", delta_color=balance_color)
            
            # Download CSV button
            st.write("")
            df = pd.DataFrame(transactions, columns=['ID', 'Date & Time', 'Type', 'Total Amount', 'Amount Received', 'Amount Left', 'Note'])
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"records_{selected}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                type="secondary"
            )
        
        st.markdown("---")
        
        # Add Record Button
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("➕ Add Record", type="primary"):
                st.session_state.show_add_form = True
                st.session_state.edit_transaction_id = None
        
        # Add/Edit Form
        if st.session_state.show_add_form or st.session_state.edit_transaction_id:
            st.markdown("### " + ("Edit Transaction" if st.session_state.edit_transaction_id else "Add New Record"))
            
            # Get existing transaction data if editing
            if st.session_state.edit_transaction_id:
                trans = [t for t in transactions if t[0] == st.session_state.edit_transaction_id][0]
                default_type = trans[2]
                default_total_amount = trans[3] if len(trans) > 3 else 0.0
                default_amount_received = trans[4] if len(trans) > 4 else 0.0
                default_note = trans[6] if len(trans) > 6 else ""
            else:
                default_type = "Received"
                default_total_amount = 0.0
                default_amount_received = 0.0
                default_note = ""
            
            with st.form("transaction_form"):
                trans_type = st.selectbox("Type", ["Received", "Given"], 
                                         index=0 if default_type == "Received" else 1)
                
                col1, col2 = st.columns(2)
                with col1:
                    total_amount = st.number_input("Total Amount", min_value=0.0, value=float(default_total_amount), step=0.01)
                with col2:
                    amount_received = st.number_input("Amount Received", min_value=0.0, value=float(default_amount_received), step=0.01)
                
                # Calculate Amount Left automatically
                amount_left = total_amount - amount_received
                st.number_input("Amount Left", value=float(amount_left), disabled=True)
                
                note = st.text_area("Note (optional)", value=default_note)
                
                col1, col2 = st.columns(2)
                with col1:
                    save = st.form_submit_button("💾 Save", type="primary")
                with col2:
                    cancel = st.form_submit_button("❌ Cancel")
                
                if save:
                    if total_amount > 0:
                        if st.session_state.edit_transaction_id:
                            update_transaction(st.session_state.edit_transaction_id, trans_type, total_amount, amount_received, amount_left, note)
                            st.success("Transaction updated!")
                        else:
                            add_transaction(st.session_state.selected_customer, trans_type, total_amount, amount_received, amount_left, note)
                            st.success("Transaction added!")
                        st.session_state.show_add_form = False
                        st.session_state.edit_transaction_id = None
                        st.rerun()
                    else:
                        st.error("Total Amount must be greater than 0")
                
                if cancel:
                    st.session_state.show_add_form = False
                    st.session_state.edit_transaction_id = None
                    st.rerun()
        
        # Display Transactions
        if transactions:
            st.markdown("### Transaction History")
            
            for trans in transactions:
                trans_id, date_time, trans_type, total_amount, amount_received, amount_left, note = trans
                
                col1, col2, col3, col4, col5, col6, col7 = st.columns([1.5, 1, 1.2, 1.2, 1.2, 2, 0.5])
                
                with col1:
                    st.write(f"**{date_time}**")
                with col2:
                    if trans_type == "Received":
                        st.success(f"✅ {trans_type}")
                    else:
                        st.error(f"❌ {trans_type}")
                with col3:
                    st.write(f"**₨ {total_amount:,.2f}**")
                with col4:
                    st.write(f"₨ {amount_received:,.2f}")
                with col5:
                    st.write(f"₨ {amount_left:,.2f}")
                with col6:
                    st.write(note or "—")
                with col7:
                    edit_col, delete_col = st.columns(2)
                    with edit_col:
                        if st.button("✏️", key=f"edit_{trans_id}"):
                            st.session_state.edit_transaction_id = trans_id
                            st.session_state.show_add_form = False
                            st.rerun()
                    with delete_col:
                        if st.button("🗑️", key=f"delete_{trans_id}"):
                            delete_transaction(trans_id)
                            st.success("Transaction deleted!")
                            st.rerun()
                
                st.markdown("---")
        else:
            st.info("No transactions yet. Click 'Add Record' to create the first one!")
    else:
        st.info("👆 Please select a customer to view and manage their records.")
