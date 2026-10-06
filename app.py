import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import csv
import io
import shutil

app = Flask(__name__)
app.secret_key = 'super_secret_cafe_key'
DATABASE = os.path.join(os.path.dirname(__file__), 'database', 'database.db')
SCHEMA = os.path.join(os.path.dirname(__file__), 'database', 'schema.sql')

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON;')
    return conn

def init_db():
    with app.app_context():
        # Check if database exists, if not create and seed
        if not os.path.exists(DATABASE):
            print("Initializing database...")
            conn = get_db_connection()
            with open(SCHEMA, 'r') as f:
                conn.executescript(f.read())
            
            # Seed data
            cursor = conn.cursor()
            
            # 1. Default Admin & Staff
            cursor.execute("INSERT INTO users (username, password_hash, role, name) VALUES (?, ?, ?, ?)",
                           ('admin', generate_password_hash('admin123'), 'admin', 'Admin'))
            cursor.execute("INSERT INTO users (username, password_hash, role, name) VALUES (?, ?, ?, ?)",
                           ('staff', generate_password_hash('staff123'), 'staff', 'Staff Member'))
            
            # 2. Sample Computers (24 PCs as per UI)
            for i in range(1, 25):
                pc_num = f"PC-{i:02d}"
                cursor.execute("INSERT INTO computers (computer_number, computer_name, hourly_rate, status) VALUES (?, ?, ?, ?)",
                               (pc_num, f"Computer {i}", 40.0, 'Available'))
            
            # 3. Default Services
            services = [
                ('B/W Printing', 3.0, 'page'),
                ('Colour Printing', 10.0, 'page'),
                ('Scanning', 10.0, 'page'),
                ('Photocopy', 2.0, 'page')
            ]
            for s in services:
                cursor.execute("INSERT INTO services (service_name, rate, unit) VALUES (?, ?, ?)", s)
                
            conn.commit()
            conn.close()
            print("Database initialized and seeded successfully.")

# --- Decorators for Role-Based Access ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        is_admin = session.get('role') == 'admin'
        has_admin_auth = session.get('admin_authenticated') == True
        if 'user_id' not in session or not (is_admin or has_admin_auth):
            flash('Admin access required.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def staff_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') not in ['staff', 'admin']:
            flash('Staff access required.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---
@app.route('/')
def index():
    if 'user_id' in session:
        if session.get('role') == 'admin' or session.get('admin_authenticated'):
            return redirect(url_for('admin_dashboard'))
        elif session.get('role') == 'staff':
            return redirect(url_for('staff_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            if user['is_active']:
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['role'] = user['role']
                session['name'] = user['name']
                return redirect(url_for('index'))
            else:
                flash('Account is deactivated.', 'error')
        else:
            flash('Invalid username or password.', 'error')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/admin/auth', methods=['POST'])
@login_required
def api_admin_auth():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ? AND role = "admin"', (username,)).fetchone()
    conn.close()
    
    if user and check_password_hash(user['password_hash'], password):
        if user['is_active']:
            # Do NOT overwrite existing Staff session ID/role.
            # Only set the authorization state.
            session['admin_authenticated'] = True
            session['admin_user_id'] = user['id']
            return jsonify({'success': True, 'message': 'Admin authenticated successfully.'})
        else:
            return jsonify({'success': False, 'message': 'Admin account is deactivated.'}), 403
    
    return jsonify({'success': False, 'message': 'Invalid admin credentials.'}), 401

@app.route('/admin/backup')
@admin_required
def admin_backup():
    try:
        backup_dir = os.path.join(os.path.dirname(__file__), 'backups')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f'database_backup_{timestamp}.db')
        
        shutil.copy2(DATABASE, backup_file)
        
        # We can directly return the file to download or just flash a message.
        # It's better to provide it as a download for the Admin
        return send_file(backup_file, as_attachment=True)
    except Exception as e:
        flash(f'Backup failed: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    
    # Dashboard Statistics
    total_customers = conn.execute('SELECT COUNT(*) FROM customers').fetchone()[0]
    total_pcs = conn.execute('SELECT COUNT(*) FROM computers').fetchone()[0]
    in_use_pcs = conn.execute("SELECT COUNT(*) FROM computers WHERE status = 'In Use'").fetchone()[0]
    available_pcs = conn.execute("SELECT COUNT(*) FROM computers WHERE status = 'Available'").fetchone()[0]
    maintenance_pcs = conn.execute("SELECT COUNT(*) FROM computers WHERE status = 'Maintenance'").fetchone()[0]
    
    # Today's Revenue and Sessions (naive today based on date string match)
    today = datetime.now().strftime('%Y-%m-%d')
    today_revenue = conn.execute("SELECT SUM(total_amount) FROM bills WHERE payment_status = 'Paid' AND date(created_at) = ?", (today,)).fetchone()[0] or 0.0
    today_sessions = conn.execute("SELECT COUNT(*) FROM sessions WHERE date(start_time) = ?", (today,)).fetchone()[0]
    
    # Recent Sessions
    recent_sessions = conn.execute('''
        SELECT s.id, c.name as customer_name, pc.computer_number, s.start_time, s.status, s.usage_charge
        FROM sessions s
        JOIN customers c ON s.customer_id = c.id
        JOIN computers pc ON s.computer_id = pc.id
        ORDER BY s.start_time DESC LIMIT 5
    ''').fetchall()
    
    # Recent Payments
    recent_payments = conn.execute('''
        SELECT b.id, c.name as customer_name, b.total_amount, b.payment_method, b.created_at, b.payment_status
        FROM bills b
        JOIN customers c ON b.customer_id = c.id
        ORDER BY b.created_at DESC LIMIT 5
    ''').fetchall()
    
    conn.close()
    
    return render_template('admin/dashboard.html', 
                           total_customers=total_customers,
                           total_pcs=total_pcs,
                           in_use_pcs=in_use_pcs,
                           available_pcs=available_pcs,
                           maintenance_pcs=maintenance_pcs,
                           today_revenue=today_revenue,
                           today_sessions=today_sessions,
                           recent_sessions=recent_sessions,
                           recent_payments=recent_payments)

@app.route('/staff/dashboard')
@staff_required
def staff_dashboard():
    conn = get_db_connection()
    
    # Staff Dashboard Statistics
    active_sessions_count = conn.execute("SELECT COUNT(*) FROM sessions WHERE status = 'Active'").fetchone()[0]
    available_pcs = conn.execute("SELECT COUNT(*) FROM computers WHERE status = 'Available'").fetchone()[0]
    in_use_pcs = conn.execute("SELECT COUNT(*) FROM computers WHERE status = 'In Use'").fetchone()[0]
    
    today = datetime.now().strftime('%Y-%m-%d')
    # Customers Today (distinct customers who started a session today)
    today_customers = conn.execute("SELECT COUNT(DISTINCT customer_id) FROM sessions WHERE date(start_time) = ?", (today,)).fetchone()[0]
    # Today's collection
    today_collection = conn.execute("SELECT SUM(total_amount) FROM bills WHERE payment_status = 'Paid' AND date(created_at) = ?", (today,)).fetchone()[0] or 0.0
    
    # Active Sessions (Ongoing)
    active_sessions = conn.execute('''
        SELECT s.id, c.name as customer_name, pc.computer_number, s.start_time
        FROM sessions s
        JOIN customers c ON s.customer_id = c.id
        JOIN computers pc ON s.computer_id = pc.id
        WHERE s.status = 'Active'
        ORDER BY s.start_time DESC
    ''').fetchall()
    
    conn.close()
    
    return render_template('staff/dashboard.html',
                           active_sessions_count=active_sessions_count,
                           available_pcs=available_pcs,
                           in_use_pcs=in_use_pcs,
                           today_customers=today_customers,
                           today_collection=today_collection,
                           active_sessions=active_sessions)

# --- Room View ---
@app.route('/room')
@login_required
def room_view():
    conn = get_db_connection()
    # Summary stats
    total_pcs = conn.execute('SELECT COUNT(*) FROM computers').fetchone()[0]
    available_pcs = conn.execute("SELECT COUNT(*) FROM computers WHERE status = 'Available'").fetchone()[0]
    in_use_pcs = conn.execute("SELECT COUNT(*) FROM computers WHERE status = 'In Use'").fetchone()[0]
    maintenance_pcs = conn.execute("SELECT COUNT(*) FROM computers WHERE status = 'Maintenance'").fetchone()[0]
    
    # Get all PCs
    computers = conn.execute('SELECT * FROM computers ORDER BY id ASC').fetchall()
    
    # Get active sessions for PCs to show in UI
    active_sessions = conn.execute('''
        SELECT s.id, s.computer_id, s.start_time, c.name as customer_name, c.customer_id as cust_ref
        FROM sessions s
        JOIN customers c ON s.customer_id = c.id
        WHERE s.status = 'Active'
    ''').fetchall()
    
    # Map active sessions by computer_id
    sessions_by_pc = {s['computer_id']: dict(s) for s in active_sessions}
    
    # All customers for the dropdown when starting a session
    customers = conn.execute('SELECT id, name, customer_id FROM customers ORDER BY name ASC').fetchall()
    
    conn.close()
    return render_template('room.html', 
                           computers=computers, 
                           sessions_by_pc=sessions_by_pc,
                           customers=customers,
                           total_pcs=total_pcs,
                           available_pcs=available_pcs,
                           in_use_pcs=in_use_pcs,
                           maintenance_pcs=maintenance_pcs)

# --- APIs for Session Management ---


@app.route('/api/session/start', methods=['POST'])
@login_required
def api_start_session():
    data = request.json
    computer_id = data.get('computer_id')
    customer_id = data.get('customer_id')
    
    if not computer_id or not customer_id:
        return jsonify({'success': False, 'message': 'Computer and Customer are required.'}), 400
        
    conn = get_db_connection()
    
    # Check computer status and get its current hourly rate
    pc = conn.execute('SELECT status, hourly_rate FROM computers WHERE id = ?', (computer_id,)).fetchone()
    if not pc or pc['status'] != 'Available':
        conn.close()
        return jsonify({'success': False, 'message': 'Computer is not available.'}), 400
        
    current_rate = pc['hourly_rate']
    
    # Start session
    try:
        start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute('INSERT INTO sessions (customer_id, computer_id, hourly_rate, start_time) VALUES (?, ?, ?, ?)', 
                     (customer_id, computer_id, current_rate, start_time))
        conn.execute("UPDATE computers SET status = 'In Use' WHERE id = ?", (computer_id,))
        conn.commit()
        success = True
        message = 'Session started successfully.'
    except Exception as e:
        conn.rollback()
        success = False
        message = str(e)
    finally:
        conn.close()
        
    return jsonify({'success': success, 'message': message})

@app.route('/api/session/end', methods=['POST'])
@login_required
def api_end_session():
    data = request.json
    session_id = data.get('session_id')
    
    if not session_id:
        return jsonify({'success': False, 'message': 'Session ID is required.'}), 400
        
    conn = get_db_connection()
    
    session_record = conn.execute('SELECT * FROM sessions WHERE id = ? AND status = "Active"', (session_id,)).fetchone()
    
    if not session_record:
        conn.close()
        return jsonify({'success': False, 'message': 'Active session not found.'}), 400
        
    try:
        # Calculate duration and charge using the historical rate stored in the session
        start_time = datetime.strptime(session_record['start_time'], '%Y-%m-%d %H:%M:%S')
        end_time = datetime.now()
        duration_minutes = max(1, int((end_time - start_time).total_seconds() / 60))
        
        hourly_rate = session_record['hourly_rate']
        usage_charge = round((duration_minutes / 60.0) * hourly_rate, 2)
        
        # Update session
        conn.execute('''
            UPDATE sessions 
            SET end_time = ?, duration_minutes = ?, usage_charge = ?, status = 'Completed'
            WHERE id = ?
        ''', (end_time.strftime('%Y-%m-%d %H:%M:%S'), duration_minutes, usage_charge, session_id))
        
        # Update computer
        conn.execute("UPDATE computers SET status = 'Available' WHERE id = ?", (session_record['computer_id'],))
        
        conn.commit()
        success = True
        message = 'Session ended successfully.'
    except Exception as e:
        conn.rollback()
        success = False
        message = str(e)
    finally:
        conn.close()
        
    return jsonify({'success': success, 'message': message})

# Admin only: Toggle maintenance
@app.route('/api/computer/<int:pc_id>/maintenance', methods=['POST'])
@admin_required
def api_toggle_maintenance(pc_id):
    conn = get_db_connection()
    pc = conn.execute('SELECT status FROM computers WHERE id = ?', (pc_id,)).fetchone()
    
    if not pc:
        conn.close()
        return jsonify({'success': False, 'message': 'Computer not found.'}), 404
        
    if pc['status'] == 'In Use':
        conn.close()
        return jsonify({'success': False, 'message': 'Cannot set maintenance while in use.'}), 400
        
    new_status = 'Available' if pc['status'] == 'Maintenance' else 'Maintenance'
    
    conn.execute("UPDATE computers SET status = ? WHERE id = ?", (new_status, pc_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'new_status': new_status})

# --- Admin Management Routes ---

@app.route('/admin/services')
@admin_required
def admin_services():
    conn = get_db_connection()
    services = conn.execute('SELECT * FROM services ORDER BY is_active DESC, service_name ASC').fetchall()
    conn.close()
    return render_template('admin/services.html', services=services)

@app.route('/api/service/add', methods=['POST'])
@admin_required
def api_add_service():
    data = request.json
    name = data.get('service_name')
    rate = data.get('rate')
    unit = data.get('unit')
    
    if not name or rate is None or not unit:
        return jsonify({'success': False, 'message': 'All fields are required.'}), 400
        
    try:
        rate = float(rate)
        if rate < 0:
            return jsonify({'success': False, 'message': 'Rate cannot be negative.'}), 400
            
        conn = get_db_connection()
        conn.execute('INSERT INTO services (service_name, rate, unit) VALUES (?, ?, ?)', (name, rate, unit))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Service added successfully.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/service/edit/<int:service_id>', methods=['POST'])
@admin_required
def api_edit_service(service_id):
    data = request.json
    name = data.get('service_name')
    rate = data.get('rate')
    unit = data.get('unit')
    
    if not name or rate is None or not unit:
        return jsonify({'success': False, 'message': 'All fields are required.'}), 400
        
    try:
        rate = float(rate)
        if rate < 0:
            return jsonify({'success': False, 'message': 'Rate cannot be negative.'}), 400
            
        conn = get_db_connection()
        conn.execute('UPDATE services SET service_name = ?, rate = ?, unit = ? WHERE id = ?', (name, rate, unit, service_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Service updated successfully.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/service/toggle/<int:service_id>', methods=['POST'])
@admin_required
def api_toggle_service(service_id):
    conn = get_db_connection()
    service = conn.execute('SELECT is_active FROM services WHERE id = ?', (service_id,)).fetchone()
    if not service:
        conn.close()
        return jsonify({'success': False, 'message': 'Service not found.'}), 404
        
    new_status = 0 if service['is_active'] == 1 else 1
    conn.execute('UPDATE services SET is_active = ? WHERE id = ?', (new_status, service_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'new_status': new_status})

@app.route('/admin/computers')
@admin_required
def admin_computers():
    conn = get_db_connection()
    computers = conn.execute('SELECT * FROM computers ORDER BY id ASC').fetchall()
    conn.close()
    return render_template('admin/computers.html', computers=computers)

@app.route('/api/computer/edit/<int:pc_id>', methods=['POST'])
@admin_required
def api_edit_computer(pc_id):
    data = request.json
    hourly_rate = data.get('hourly_rate')
    computer_name = data.get('computer_name')
    
    if hourly_rate is None:
        return jsonify({'success': False, 'message': 'Hourly rate is required.'}), 400
        
    try:
        rate = float(hourly_rate)
        if rate < 0:
            return jsonify({'success': False, 'message': 'Rate cannot be negative.'}), 400
            
        conn = get_db_connection()
        if computer_name:
            conn.execute('UPDATE computers SET hourly_rate = ?, computer_name = ? WHERE id = ?', (rate, computer_name, pc_id))
        else:
            conn.execute('UPDATE computers SET hourly_rate = ? WHERE id = ?', (rate, pc_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Computer updated successfully.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

# --- Customer Management Routes ---

@app.route('/customers')
@login_required
def customers_view():
    conn = get_db_connection()
    customers = conn.execute('SELECT * FROM customers ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('customers.html', customers=customers)

@app.route('/customer/<int:customer_id>')
@login_required
def customer_details(customer_id):
    conn = get_db_connection()
    customer = conn.execute('SELECT * FROM customers WHERE id = ?', (customer_id,)).fetchone()
    if not customer:
        conn.close()
        return "Customer not found", 404
        
    sessions = conn.execute('''
        SELECT s.*, c.computer_number 
        FROM sessions s 
        JOIN computers c ON s.computer_id = c.id 
        WHERE s.customer_id = ? 
        ORDER BY s.start_time DESC
    ''', (customer_id,)).fetchall()
    
    conn.close()
    return render_template('customer_details.html', customer=customer, sessions=sessions)

@app.route('/api/customer/add', methods=['POST'])
@login_required
def api_add_customer():
    data = request.json
    name = data.get('name')
    mobile = data.get('mobile')
    email = data.get('email', '')
    address = data.get('address', '')
    
    if not name or not mobile:
        return jsonify({'success': False, 'message': 'Name and Mobile are required.'}), 400
        
    try:
        conn = get_db_connection()
        # Generate a unique customer_id (e.g., CUST-1001)
        last_cust = conn.execute('SELECT id FROM customers ORDER BY id DESC LIMIT 1').fetchone()
        next_id = last_cust['id'] + 1 if last_cust else 1
        cust_ref = f"CUST-{1000 + next_id}"
        
        conn.execute('INSERT INTO customers (customer_id, name, mobile, email, address) VALUES (?, ?, ?, ?, ?)', 
                     (cust_ref, name, mobile, email, address))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Customer added successfully.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/customer/edit/<int:customer_id>', methods=['POST'])
@login_required
def api_edit_customer(customer_id):
    data = request.json
    name = data.get('name')
    mobile = data.get('mobile')
    email = data.get('email', '')
    address = data.get('address', '')
    
    if not name or not mobile:
        return jsonify({'success': False, 'message': 'Name and Mobile are required.'}), 400
        
    try:
        conn = get_db_connection()
        conn.execute('UPDATE customers SET name = ?, mobile = ?, email = ?, address = ? WHERE id = ?', 
                     (name, mobile, email, address, customer_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Customer updated successfully.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/search/customers')
@login_required
def api_search_customers():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'success': True, 'customers': []})
        
    search_term = f"%{query}%"
    conn = get_db_connection()
    customers = conn.execute('''
        SELECT id, customer_id, name, mobile 
        FROM customers 
        WHERE name LIKE ? OR mobile LIKE ? OR customer_id LIKE ?
        LIMIT 10
    ''', (search_term, search_term, search_term)).fetchall()
    conn.close()
    
    result = [dict(c) for c in customers]
    return jsonify({'success': True, 'customers': result})

@app.route('/settings')
@login_required
def settings_page():
    return render_template('settings.html')

@app.route('/messages')
@login_required
def messages_page():
    return render_template('messages.html')

@app.route('/billing')
@login_required
def billing_list():
    conn = get_db_connection()
    # Find all completed sessions that don't have a bill yet
    unbilled_sessions = conn.execute('''
        SELECT s.id as session_id, c.name as customer_name, c.customer_id as cust_ref,
               comp.computer_number, s.start_time, s.end_time, s.duration_minutes, s.usage_charge
        FROM sessions s
        JOIN customers c ON s.customer_id = c.id
        JOIN computers comp ON s.computer_id = comp.id
        LEFT JOIN bills b ON s.id = b.session_id
        WHERE s.status = 'Completed' AND b.id IS NULL
        ORDER BY s.end_time DESC
    ''').fetchall()
    conn.close()
    return render_template('billing.html', sessions=unbilled_sessions)

@app.route('/billing/create/<int:session_id>', methods=['GET', 'POST'])
@login_required
def create_bill(session_id):
    conn = get_db_connection()
    if request.method == 'GET':
        session_data = conn.execute('''
            SELECT s.*, c.name as customer_name, comp.computer_number
            FROM sessions s
            JOIN customers c ON s.customer_id = c.id
            JOIN computers comp ON s.computer_id = comp.id
            WHERE s.id = ? AND s.status = 'Completed'
        ''', (session_id,)).fetchone()
        
        if not session_data:
            conn.close()
            flash('Invalid session or session already billed.', 'error')
            return redirect(url_for('billing_list'))
            
        services = conn.execute('SELECT * FROM services WHERE is_active = 1').fetchall()
        conn.close()
        return render_template('billing_create.html', session_data=session_data, services=services)
        
    elif request.method == 'POST':
        # Verify the session is not already billed
        existing_bill = conn.execute('SELECT id FROM bills WHERE session_id = ?', (session_id,)).fetchone()
        if existing_bill:
            conn.close()
            flash('This session has already been billed.', 'error')
            return jsonify({'success': False, 'message': 'Session already billed', 'redirect_url': url_for('view_receipt', bill_id=existing_bill['id'])})
            
        try:
            data = request.json
            payment_method = data.get('payment_method', 'Cash')
            payment_status = data.get('payment_status', 'Paid')
            items = data.get('items', [])
            
            # Fetch session
            session_data = conn.execute('SELECT * FROM sessions WHERE id = ?', (session_id,)).fetchone()
            usage_charge = session_data['usage_charge']
            
            subtotal = usage_charge
            
            # Calculate services total securely from DB rates
            valid_items = []
            for item in items:
                service_id = item.get('service_id')
                quantity = int(item.get('quantity', 0))
                
                if quantity <= 0:
                    continue
                    
                service = conn.execute('SELECT rate FROM services WHERE id = ? AND is_active = 1', (service_id,)).fetchone()
                if service:
                    rate = service['rate']
                    amount = rate * quantity
                    subtotal += amount
                    valid_items.append({
                        'service_id': service_id,
                        'quantity': quantity,
                        'rate': rate,
                        'amount': amount
                    })
            
            # Insert Bill
            cursor = conn.execute('''
                INSERT INTO bills (session_id, customer_id, subtotal, total_amount, payment_method, payment_status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (session_id, session_data['customer_id'], usage_charge, subtotal, payment_method, payment_status))
            
            bill_id = cursor.lastrowid
            
            # Insert Bill Items
            for v_item in valid_items:
                conn.execute('''
                    INSERT INTO bill_items (bill_id, service_id, quantity, rate, amount)
                    VALUES (?, ?, ?, ?, ?)
                ''', (bill_id, v_item['service_id'], v_item['quantity'], v_item['rate'], v_item['amount']))
                
            conn.commit()
            success = True
            message = 'Bill created successfully.'
            redirect_url = url_for('view_receipt', bill_id=bill_id)
        except Exception as e:
            conn.rollback()
            success = False
            message = str(e)
            redirect_url = ''
            bill_id = None
        finally:
            conn.close()
            
        return jsonify({'success': success, 'message': message, 'redirect_url': redirect_url, 'bill_id': bill_id})

@app.route('/billing/history')
@login_required
def billing_history():
    conn = get_db_connection()
    bills = conn.execute('''
        SELECT b.id, b.total_amount, b.payment_method, b.payment_status, b.created_at,
               c.name as customer_name, comp.computer_number
        FROM bills b
        JOIN customers c ON b.customer_id = c.id
        JOIN sessions s ON b.session_id = s.id
        JOIN computers comp ON s.computer_id = comp.id
        ORDER BY b.created_at DESC
    ''').fetchall()
    conn.close()
    return render_template('billing_history.html', bills=bills)

@app.route('/billing/receipt/<int:bill_id>')
@login_required
def view_receipt(bill_id):
    conn = get_db_connection()
    bill = conn.execute('''
        SELECT b.*, c.name as customer_name, c.customer_id as cust_ref,
               s.start_time, s.end_time, s.duration_minutes, s.usage_charge, s.hourly_rate,
               comp.computer_number
        FROM bills b
        JOIN customers c ON b.customer_id = c.id
        JOIN sessions s ON b.session_id = s.id
        JOIN computers comp ON s.computer_id = comp.id
        WHERE b.id = ?
    ''', (bill_id,)).fetchone()
    
    if not bill:
        conn.close()
        flash('Bill not found.', 'error')
        return redirect(url_for('billing_history'))
        
    items = conn.execute('''
        SELECT bi.*, s.service_name 
        FROM bill_items bi
        JOIN services s ON bi.service_id = s.id
        WHERE bi.bill_id = ?
    ''', (bill_id,)).fetchall()
    
    conn.close()
    return render_template('receipt.html', bill=bill, items=items)

@app.route('/reports')
@admin_required
def admin_reports():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # Default to today if no dates provided
    if not start_date or not end_date:
        today = datetime.now().strftime('%Y-%m-%d')
        start_date = today
        end_date = today

    # For SQL BETWEEN we need the end date to include up to 23:59:59
    end_date_full = f"{end_date} 23:59:59"
    start_date_full = f"{start_date} 00:00:00"

    conn = get_db_connection()

    # 1. Revenue Summary
    revenue_summary = conn.execute('''
        SELECT 
            COUNT(id) as total_bills,
            SUM(CASE WHEN payment_status = 'Paid' THEN 1 ELSE 0 END) as paid_bills,
            SUM(CASE WHEN payment_status = 'Pending' THEN 1 ELSE 0 END) as pending_bills,
            SUM(CASE WHEN payment_status = 'Paid' THEN total_amount ELSE 0 END) as total_revenue
        FROM bills 
        WHERE created_at BETWEEN ? AND ?
    ''', (start_date_full, end_date_full)).fetchone()

    # Usage Revenue
    usage_revenue = conn.execute('''
        SELECT SUM(usage_charge) as total_usage_revenue
        FROM sessions
        WHERE start_time BETWEEN ? AND ? AND status = 'Completed'
    ''', (start_date_full, end_date_full)).fetchone()['total_usage_revenue'] or 0.0

    # Service Revenue
    service_revenue = conn.execute('''
        SELECT SUM(bi.amount) as total_service_revenue
        FROM bill_items bi
        JOIN bills b ON bi.bill_id = b.id
        WHERE b.created_at BETWEEN ? AND ? AND b.payment_status = 'Paid'
    ''', (start_date_full, end_date_full)).fetchone()['total_service_revenue'] or 0.0

    # 2. Session Summary
    session_summary = conn.execute('''
        SELECT 
            COUNT(id) as total_sessions,
            SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed_sessions,
            SUM(CASE WHEN status = 'Active' THEN 1 ELSE 0 END) as active_sessions,
            SUM(duration_minutes) as total_usage_minutes,
            AVG(duration_minutes) as avg_duration
        FROM sessions
        WHERE start_time BETWEEN ? AND ?
    ''', (start_date_full, end_date_full)).fetchone()

    total_usage_hours = round((session_summary['total_usage_minutes'] or 0) / 60, 2)
    avg_duration = round(session_summary['avg_duration'] or 0, 1)

    # 3. Computer Usage Report
    computer_usage = conn.execute('''
        SELECT 
            c.computer_number,
            COUNT(s.id) as total_sessions,
            SUM(s.duration_minutes) as total_minutes,
            SUM(s.usage_charge) as usage_revenue,
            c.status
        FROM computers c
        LEFT JOIN sessions s ON c.id = s.computer_id AND s.start_time BETWEEN ? AND ?
        GROUP BY c.id
        ORDER BY total_sessions DESC, usage_revenue DESC
    ''', (start_date_full, end_date_full)).fetchall()

    # 4. Service Usage Report
    service_usage = conn.execute('''
        SELECT 
            s.service_name,
            SUM(bi.quantity) as total_quantity,
            SUM(bi.amount) as total_revenue
        FROM services s
        JOIN bill_items bi ON s.id = bi.service_id
        JOIN bills b ON bi.bill_id = b.id
        WHERE b.created_at BETWEEN ? AND ? AND b.payment_status = 'Paid'
        GROUP BY s.id
        ORDER BY total_revenue DESC
    ''', (start_date_full, end_date_full)).fetchall()

    # 5. Payment Report
    payment_report = conn.execute('''
        SELECT 
            SUM(CASE WHEN payment_method = 'Cash' AND payment_status = 'Paid' THEN total_amount ELSE 0 END) as cash_revenue,
            SUM(CASE WHEN payment_method = 'UPI' AND payment_status = 'Paid' THEN total_amount ELSE 0 END) as upi_revenue,
            SUM(CASE WHEN payment_status = 'Pending' THEN total_amount ELSE 0 END) as pending_amount,
            SUM(CASE WHEN payment_method = 'Cash' AND payment_status = 'Paid' THEN 1 ELSE 0 END) as cash_count,
            SUM(CASE WHEN payment_method = 'UPI' AND payment_status = 'Paid' THEN 1 ELSE 0 END) as upi_count,
            SUM(CASE WHEN payment_status = 'Pending' THEN 1 ELSE 0 END) as pending_count
        FROM bills
        WHERE created_at BETWEEN ? AND ?
    ''', (start_date_full, end_date_full)).fetchone()

    # 6. Customer Report
    total_customers = conn.execute('SELECT COUNT(id) FROM customers').fetchone()[0]
    new_customers = conn.execute('SELECT COUNT(id) FROM customers WHERE created_at BETWEEN ? AND ?', (start_date_full, end_date_full)).fetchone()[0]
    
    customer_stats = conn.execute('''
        SELECT 
            COUNT(DISTINCT customer_id) as returning_customers,
            SUM(total_amount) as customer_revenue
        FROM bills
        WHERE created_at BETWEEN ? AND ? AND payment_status = 'Paid'
    ''', (start_date_full, end_date_full)).fetchone()
    
    # 7. Daily Revenue
    daily_revenue = conn.execute('''
        SELECT 
            DATE(created_at) as date,
            COUNT(id) as bills,
            SUM(total_amount) as revenue
        FROM bills
        WHERE created_at BETWEEN ? AND ? AND payment_status = 'Paid'
        GROUP BY DATE(created_at)
        ORDER BY date ASC
    ''', (start_date_full, end_date_full)).fetchall()

    conn.close()

    return render_template('admin/reports.html', 
                           start_date=start_date, 
                           end_date=end_date,
                           revenue_summary=revenue_summary,
                           usage_revenue=usage_revenue,
                           service_revenue=service_revenue,
                           session_summary=session_summary,
                           total_usage_hours=total_usage_hours,
                           avg_duration=avg_duration,
                           computer_usage=computer_usage,
                           service_usage=service_usage,
                           payment_report=payment_report,
                           total_customers=total_customers,
                           new_customers=new_customers,
                           customer_stats=customer_stats,
                           daily_revenue=daily_revenue)

@app.route('/reports/export')
@admin_required
def export_reports():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    report_type = request.args.get('type')

    if not start_date or not end_date or not report_type:
        flash('Missing parameters for export.', 'error')
        return redirect(url_for('admin_reports'))

    end_date_full = f"{end_date} 23:59:59"
    start_date_full = f"{start_date} 00:00:00"

    conn = get_db_connection()
    si = io.StringIO()
    cw = csv.writer(si)

    if report_type == 'revenue':
        cw.writerow(['Date', 'Bills', 'Revenue'])
        data = conn.execute('''
            SELECT DATE(created_at) as date, COUNT(id) as bills, SUM(total_amount) as revenue
            FROM bills
            WHERE created_at BETWEEN ? AND ? AND payment_status = 'Paid'
            GROUP BY DATE(created_at)
            ORDER BY date ASC
        ''', (start_date_full, end_date_full)).fetchall()
        for row in data:
            cw.writerow([row['date'], row['bills'], row['revenue']])
        filename = f"revenue_report_{start_date}_to_{end_date}.csv"

    elif report_type == 'computers':
        cw.writerow(['Computer Number', 'Total Sessions', 'Total Minutes', 'Usage Revenue'])
        data = conn.execute('''
            SELECT c.computer_number, COUNT(s.id) as total_sessions, SUM(s.duration_minutes) as total_minutes, SUM(s.usage_charge) as usage_revenue
            FROM computers c
            LEFT JOIN sessions s ON c.id = s.computer_id AND s.start_time BETWEEN ? AND ?
            GROUP BY c.id
            ORDER BY total_sessions DESC
        ''', (start_date_full, end_date_full)).fetchall()
        for row in data:
            cw.writerow([row['computer_number'], row['total_sessions'], row['total_minutes'] or 0, row['usage_revenue'] or 0])
        filename = f"computer_usage_report_{start_date}_to_{end_date}.csv"

    elif report_type == 'services':
        cw.writerow(['Service Name', 'Total Quantity', 'Total Revenue'])
        data = conn.execute('''
            SELECT s.service_name, SUM(bi.quantity) as total_quantity, SUM(bi.amount) as total_revenue
            FROM services s
            JOIN bill_items bi ON s.id = bi.service_id
            JOIN bills b ON bi.bill_id = b.id
            WHERE b.created_at BETWEEN ? AND ? AND b.payment_status = 'Paid'
            GROUP BY s.id
            ORDER BY total_revenue DESC
        ''', (start_date_full, end_date_full)).fetchall()
        for row in data:
            cw.writerow([row['service_name'], row['total_quantity'], row['total_revenue']])
        filename = f"service_usage_report_{start_date}_to_{end_date}.csv"
    
    elif report_type == 'payments':
        cw.writerow(['Payment Method', 'Count', 'Revenue'])
        data = conn.execute('''
            SELECT payment_method, COUNT(id) as count, SUM(total_amount) as revenue
            FROM bills
            WHERE created_at BETWEEN ? AND ? AND payment_status = 'Paid'
            GROUP BY payment_method
        ''', (start_date_full, end_date_full)).fetchall()
        for row in data:
            cw.writerow([row['payment_method'], row['count'], row['revenue']])
        filename = f"payment_report_{start_date}_to_{end_date}.csv"
    
    else:
        conn.close()
        flash('Invalid report type.', 'error')
        return redirect(url_for('admin_reports'))

    conn.close()
    
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename={filename}"
    output.headers["Content-type"] = "text/csv"
    return output

@app.route('/admin/exit')
def admin_exit():
    if 'admin_authenticated' in session:
        session.pop('admin_authenticated', None)
        session.pop('admin_user_id', None)
    return redirect(url_for('staff_dashboard'))

@app.route('/admin/staff')
@admin_required
def admin_staff():
    conn = get_db_connection()
    staff_members = conn.execute('SELECT * FROM users WHERE role = "staff" ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('admin/staff.html', staff=staff_members)

@app.route('/api/staff/add', methods=['POST'])
@admin_required
def api_add_staff():
    data = request.json
    name = data.get('name')
    username = data.get('username')
    password = data.get('password')
    
    if not name or not username or not password:
        return jsonify({'success': False, 'message': 'All fields are required.'}), 400
        
    conn = get_db_connection()
    try:
        # Check if username exists
        existing = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
        if existing:
            conn.close()
            return jsonify({'success': False, 'message': 'Username already exists.'}), 400
            
        hashed_pw = generate_password_hash(password)
        conn.execute('INSERT INTO users (username, password_hash, role, name) VALUES (?, ?, ?, ?)',
                     (username, hashed_pw, 'staff', name))
        conn.commit()
        return jsonify({'success': True, 'message': 'Staff member added successfully.'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400
    finally:
        conn.close()

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
