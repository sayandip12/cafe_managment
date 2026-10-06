CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL, -- 'admin' or 'staff'
    name TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT UNIQUE NOT NULL, -- e.g., CC1001
    name TEXT NOT NULL,
    mobile TEXT UNIQUE NOT NULL,
    email TEXT,
    address TEXT,
    password_hash TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS computers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    computer_number TEXT UNIQUE NOT NULL,
    computer_name TEXT,
    hourly_rate REAL NOT NULL,
    status TEXT DEFAULT 'Available', -- 'Available', 'In Use', 'Maintenance'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_name TEXT NOT NULL,
    rate REAL NOT NULL,
    unit TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    computer_id INTEGER,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    duration_minutes INTEGER,
    usage_charge REAL,
    status TEXT DEFAULT 'Active', -- 'Active', 'Completed'
    FOREIGN KEY(customer_id) REFERENCES customers(id),
    FOREIGN KEY(computer_id) REFERENCES computers(id)
);

CREATE TABLE IF NOT EXISTS bills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    customer_id INTEGER,
    subtotal REAL,
    total REAL,
    payment_method TEXT, -- 'Cash', 'UPI'
    payment_status TEXT DEFAULT 'Pending', -- 'Pending', 'Paid'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(session_id) REFERENCES sessions(id),
    FOREIGN KEY(customer_id) REFERENCES customers(id)
);

CREATE TABLE IF NOT EXISTS bill_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id INTEGER,
    service_id INTEGER,
    quantity INTEGER,
    rate REAL,
    amount REAL,
    FOREIGN KEY(bill_id) REFERENCES bills(id),
    FOREIGN KEY(service_id) REFERENCES services(id)
);
