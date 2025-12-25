import streamlit as st
import sqlite3
import hashlib
from datetime import datetime
import pandas as pd

# Page config MUST be first
st.set_page_config(page_title="Customer Records Manager", layout="wide", page_icon="📊")

# Database setup
DB_NAME = "customer_records.db"

def get_db_connection():
    """Get database connection with thread safety"""
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def hash_password(password):
    """Hash password using PBKDF2"""
    salt = b'money_records_salt_2024'
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000).hex()

def init_db():
    """Initialize database tables - called only once"""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  email TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS customers
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  name TEXT NOT NULL,
                  FOREIGN KEY (user_id) REFERENCES users(id))''')
    
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
    
    # Create default admin user
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

# Initialize session state
def init_session_state():
    """Initialize all session state variables"""
    if 'db_initialized' not in st.session_state:
        init_db()
        st.session_state.db_initialized = True
    
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'user_name' not in st.session_state:
        st.session_state.user_name = None
    if 'selected_customer_id' not in st.session_state:
        st.session_state.selected_customer_id = None
    if 'show_add_form' not in st.session_state:
        st.session_state.show_add_form = False
    if 'edit_transaction_id' not in st.session_state:
        st.session_state.edit_transaction_id = None
    if 'show_add_customer' not in st.session_state:
        st.session_state.show_add_customer = False

init_session_state()

# Database Functions
def register_user(name, email, password):
    """Register a new user"""
    try:
        conn = get_db_connection()
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
    conn = get_db_connection()
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
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, name FROM customers WHERE user_id = ? ORDER BY name",
              (user_id,))
    customers = c.fetchall()
    conn.close()
    return customers

def add_customer(user_id, name):
    """Add a new customer"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO customers (user_id, name) VALUES (?, ?)",
              (user_id, name))
    conn.commit()
    conn.close()

def get_transactions(customer_id, month_filter=None):
    """Get all transactions for a customer"""
    conn = get_db_connection()
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

def get_today_transactions(customer_id):
    """Get today's transactions for a customer"""
    conn = get_db_connection()
    c = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    c.execute("""SELECT date_time, type, total_amount 
                 FROM transactions 
                 WHERE customer_id = ? AND date(date_time) = ?
                 ORDER BY date_time DESC""",
              (customer_id, today))
    transactions = c.fetchall()
    conn.close()
    return transactions

def add_transaction(customer_id, trans_type, total_amount, amount_received, amount_left, note):
    """Add a new transaction"""
    conn = get_db_connection()
    c = conn.cursor()
    date_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute("""INSERT INTO transactions (customer_id, date_time, type, total_amount, amount_received, amount_left, note)
                 VALUES (?, ?, ?, ?, ?, ?, ?)""",
              (customer_id, date_time, trans_type, total_amount, amount_received, amount_left, note))
    conn.commit()
    conn.close()

def update_transaction(trans_id, trans_type, total_amount, amount_received, amount_left, note):
    """Update an existing transaction"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""UPDATE transactions 
                 SET type = ?, total_amount = ?, amount_received = ?, amount_left = ?, note = ?
                 WHERE id = ?""",
              (trans_type, total_amount, amount_received, amount_left, note, trans_id))
    conn.commit()
    conn.close()

def delete_transaction(trans_id):
    """Delete a transaction"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM transactions WHERE id = ?", (trans_id,))
    conn.commit()
    conn.close()

def get_available_months(customer_id):
    """Get list of months with transactions"""
    conn = get_db_connection()
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

# ==================== MAIN APP ====================

# AUTH SCREEN
if not st.session_state.logged_in:
    st.title("📊 Customer Records Manager")
    st.markdown("### Manage your customer transactions easily")
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        st.subheader("Login to Your Account")
        with st.form("login_form"):
            email = st.text_input("Email Address")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", type="primary", use_container_width=True)
            
            if submit:
                if email and password:
                    success, user_id, user_name = login_user(email, password)
                    if success:
                        st.session_state.logged_in = True
                        st.session_state.user_id = user_id
                        st.session_state.user_name = user_name
                        st.rerun()
                    else:
                        st.error("❌ Invalid email or password")
                else:
                    st.warning("⚠️ Please fill in all fields")
        
        st.info("💡 Demo account: **admin@example.com** / **admin123**")
    
    with tab2:
        st.subheader("Create New Account")
        with st.form("register_form"):
            name = st.text_input("Your Name")
            email = st.text_input("Email Address")
            password = st.text_input("Password (minimum 6 characters)", type="password")
            submit = st.form_submit_button("Create Account", type="primary", use_container_width=True)
            
            if submit:
                if name and email and password:
                    if len(password) < 6:
                        st.error("❌ Password must be at least 6 characters")
                    else:
                        success, user_id, user_name = register_user(name, email, password)
                        if success:
                            st.session_state.logged_in = True
                            st.session_state.user_id = user_id
                            st.session_state.user_name = user_name
                            st.success("✅ Account created successfully!")
                            st.rerun()
                        else:
                            st.error("❌ Email already exists")
                else:
                    st.warning("⚠️ Please fill in all fields")

# CUSTOMER SCREEN
else:
    # Header
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title(f"👋 Welcome, {st.session_state.user_name}!")
    with col2:
        if st.button("Logout", type="secondary", use_container_width=True):
            st.session_state.clear()
            st.rerun()
    
    st.markdown("---")
    
    # Customer Selection
    customers = get_customers(st.session_state.user_id)
    customer_dict = {c[1]: c[0] for c in customers}
    customer_names = list(customer_dict.keys())
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if customer_names:
            selected_name = st.selectbox(
                "Select Customer",
                [""] + customer_names,
                format_func=lambda x: "Please select a customer" if x == "" else x
            )
            if selected_name:
                st.session_state.selected_customer_id = customer_dict[selected_name]
            else:
                st.session_state.selected_customer_id = None
        else:
            st.info("No customers yet. Click 'Add New Customer' to get started.")
            st.session_state.selected_customer_id = None
    
    with col2:
        if st.button("➕ Add New Customer", type="primary", use_container_width=True):
            st.session_state.show_add_customer = True
    
    # Add Customer Form
    if st.session_state.show_add_customer:
        st.markdown("### ➕ Add New Customer")
        with st.form("add_customer_form"):
            new_customer_name = st.text_input("Customer Name", placeholder="Enter customer name")
            col1, col2 = st.columns(2)
            with col1:
                save_customer = st.form_submit_button("💾 Save Customer", type="primary", use_container_width=True)
            with col2:
                cancel_customer = st.form_submit_button("❌ Cancel", use_container_width=True)
            
            if save_customer:
                if new_customer_name.strip():
                    add_customer(st.session_state.user_id, new_customer_name.strip())
                    st.success(f"✅ Customer '{new_customer_name}' added successfully!")
                    st.session_state.show_add_customer = False
                    st.rerun()
                else:
                    st.error("❌ Please enter a customer name")
            
            if cancel_customer:
                st.session_state.show_add_customer = False
                st.rerun()
    
    # Show transactions if customer is selected
    if st.session_state.selected_customer_id:
        st.markdown("---")
        
        # Month Filter
        available_months = get_available_months(st.session_state.selected_customer_id)
        current_month = datetime.now().strftime('%Y-%m')
        
        if available_months:
            month_options = ["All Months"] + available_months
            default_index = month_options.index(current_month) if current_month in month_options else 0
            selected_month = st.selectbox("Filter by Month", month_options, index=default_index)
        else:
            selected_month = None
        
        # Get transactions
        transactions = get_transactions(st.session_state.selected_customer_id, selected_month)
        
        # Summary
        if transactions:
            total_received, total_given, balance = calculate_summary(transactions)
            
            st.markdown("### 📊 Financial Summary")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("💰 Total Received", f"₨ {total_received:,.2f}")
            with col2:
                st.metric("💸 Total Given", f"₨ {total_given:,.2f}")
            with col3:
                st.metric("📈 Net Balance", f"₨ {balance:,.2f}")
            
            # Download CSV
            st.write("")
            df = pd.DataFrame(transactions, columns=['ID', 'Date & Time', 'Type', 'Total Amount', 'Amount Received', 'Amount Left', 'Note'])
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download All Records (CSV)",
                data=csv,
                file_name=f"{selected_name}_records_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                type="secondary",
                use_container_width=True
            )
        
        # Today's Transactions
        today_trans = get_today_transactions(st.session_state.selected_customer_id)
        if today_trans:
            st.markdown("---")
            st.markdown("### 📅 Today's Activity")
            for trans in today_trans:
                date_time, trans_type, amount = trans
                time_only = datetime.strptime(date_time, '%Y-%m-%d %H:%M:%S').strftime('%I:%M %p')
                col1, col2 = st.columns([3, 1])
                with col1:
                    if trans_type == "Received":
                        st.success(f"✅ Payment Received: ₨ {amount:,.2f}")
                    else:
                        st.error(f"❌ Payment Given: ₨ {amount:,.2f}")
                with col2:
                    st.write(f"🕐 {time_only}")
        
        st.markdown("---")
        
        # Add Record Button
        if st.button("➕ Add Transaction", type="primary"):
            st.session_state.show_add_form = True
            st.session_state.edit_transaction_id = None
        
        # Add/Edit Form
        if st.session_state.show_add_form or st.session_state.edit_transaction_id:
            st.markdown("### " + ("✏️ Edit Transaction" if st.session_state.edit_transaction_id else "➕ Add New Transaction"))
            
            # Get existing transaction data if editing
            if st.session_state.edit_transaction_id:
                trans = [t for t in transactions if t[0] == st.session_state.edit_transaction_id][0]
                default_type = trans[2]
                default_total_amount = trans[3]
                default_amount_received = trans[4]
                default_note = trans[6] or ""
            else:
                default_type = "Received"
                default_total_amount = 0.0
                default_amount_received = 0.0
                default_note = ""
            
            with st.form("transaction_form"):
                trans_type = st.selectbox("Transaction Type", ["Received", "Given"], 
                                         index=0 if default_type == "Received" else 1,
                                         help="Select whether you received payment or gave payment")
                
                col1, col2 = st.columns(2)
                with col1:
                    total_amount = st.number_input("Total Amount (₨)", min_value=0.0, value=float(default_total_amount), step=0.01,
                                                  help="Enter the total transaction amount")
                with col2:
                    amount_received = st.number_input("Amount Received (₨)", min_value=0.0, value=float(default_amount_received), step=0.01,
                                                     help="Enter the amount actually received")
                
                amount_left = total_amount - amount_received
                st.number_input("Amount Remaining (₨)", value=float(amount_left), disabled=True,
                               help="Automatically calculated: Total - Received")
                
                note = st.text_area("Additional Notes (Optional)", value=default_note, 
                                   placeholder="Add any details or remarks about this transaction",
                                   help="You can add payment method, purpose, or any other details")
                
                st.write("")
                col1, col2 = st.columns(2)
                with col1:
                    save = st.form_submit_button("💾 Save Transaction", type="primary", use_container_width=True)
                with col2:
                    cancel = st.form_submit_button("❌ Cancel", use_container_width=True)
                
                if save:
                    if total_amount > 0:
                        if st.session_state.edit_transaction_id:
                            update_transaction(st.session_state.edit_transaction_id, trans_type, total_amount, amount_received, amount_left, note)
                            st.success("✅ Transaction updated successfully!")
                        else:
                            add_transaction(st.session_state.selected_customer_id, trans_type, total_amount, amount_received, amount_left, note)
                            st.success("✅ Transaction added successfully!")
                        st.session_state.show_add_form = False
                        st.session_state.edit_transaction_id = None
                        st.rerun()
                    else:
                        st.error("❌ Total Amount must be greater than 0")
                
                if cancel:
                    st.session_state.show_add_form = False
                    st.session_state.edit_transaction_id = None
                    st.rerun()
        
        # Display Transactions
        if transactions:
            st.markdown("---")
            st.markdown("### 📜 All Transactions")
            st.caption(f"Showing {len(transactions)} transaction(s)")
            
            for trans in transactions:
                trans_id, date_time, trans_type, total_amount, amount_received, amount_left, note = trans
                
                with st.container():
                    col1, col2, col3, col4, col5, col6, col7 = st.columns([2, 1, 1.2, 1.2, 1.2, 2.5, 0.8])
                    
                    with col1:
                        st.write(f"**📅 {date_time}**")
                    with col2:
                        if trans_type == "Received":
                            st.success("✅ Received")
                        else:
                            st.error("❌ Given")
                    with col3:
                        st.write(f"**Total: ₨ {total_amount:,.2f}**")
                    with col4:
                        st.write(f"Paid: ₨ {amount_received:,.2f}")
                    with col5:
                        st.write(f"Pending: ₨ {amount_left:,.2f}")
                    with col6:
                        st.write(note if note else "—")
                    with col7:
                        btn_col1, btn_col2 = st.columns(2)
                        with btn_col1:
                            if st.button("✏️", key=f"edit_{trans_id}", help="Edit this transaction"):
                                st.session_state.edit_transaction_id = trans_id
                                st.session_state.show_add_form = False
                                st.rerun()
                        with btn_col2:
                            if st.button("🗑️", key=f"del_{trans_id}", help="Delete this transaction"):
                                st.session_state[f'confirm_delete_{trans_id}'] = True
                                st.rerun()
                    
                    # Delete confirmation
                    if st.session_state.get(f'confirm_delete_{trans_id}', False):
                        st.warning("⚠️ **Are you sure?** This transaction will be permanently deleted.")
                        conf_col1, conf_col2 = st.columns(2)
                        with conf_col1:
                            if st.button("✅ Yes, Delete", key=f"confirm_yes_{trans_id}", type="primary", use_container_width=True):
                                delete_transaction(trans_id)
                                st.session_state[f'confirm_delete_{trans_id}'] = False
                                st.success("✅ Transaction deleted successfully!")
                                st.rerun()
                        with conf_col2:
                            if st.button("❌ Cancel", key=f"confirm_no_{trans_id}", use_container_width=True):
                                st.session_state[f'confirm_delete_{trans_id}'] = False
                                st.rerun()
                    
                    st.markdown("---")
        else:
            st.info("📝 No transactions found. Click 'Add Transaction' to record your first entry!")
    else:
        if customer_names:
            st.info("👆 Please select a customer to view and manage their records.")
