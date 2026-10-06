# Cyber Cafe Management System

A complete, college-level functional management system for a single physical cyber cafe. Built completely from scratch using purely vanilla technologies, maintaining high performance, security, and portability without any cloud dependencies.

## Features
- **Role-Based Authentication**: Secure access for 'Admin' and 'Staff' users.
- **Room View & PC Management**: Interactive grid mapped to 24 local computers (arranged in custom 2-2-2 configuration).
- **Session Tracking**: Automatic time calculation, snapshotting hourly rates, and generating usage charges.
- **Services Management**: Configurable pricing for B/W Printing, Colour Printing, Scanning, and Photocopying.
- **Robust Billing & Receipts**: Combine PC usage and additional services into atomic bills with printing capabilities.
- **Reports & Analytics**: Full suite of metrics, charts, payment breakdown (Cash/UPI), and date-filtering.
- **Secure Export & Backup**: Admin-only CSV extraction and SQLite database backup options.

## Technology Stack
- **Frontend**: HTML5, CSS3, Vanilla JavaScript.
- **Backend**: Python 3, Flask.
- **Database**: SQLite.

## Folder Structure
```
cyber-cafe-management-system/
├── app.py                   # Main Flask application and business logic
├── database/
│   ├── database.db          # Live SQLite database
│   └── schema.sql           # Database schema definition
├── backups/                 # Local directory where Admin backups are saved
├── static/                  # (Optional) CSS/JS/Images if externalized
├── templates/               # HTML templates (Jinja2)
│   ├── admin/               # Admin specific views (dashboard, reports)
│   ├── staff/               # Staff specific views (dashboard)
│   ├── base.html            # Shared layout container
│   ├── login.html           # Authentication page
│   ├── room.html            # Live computer arrangement view
│   ├── customers.html       # Customer list and addition
│   └── customer_details.html# Individual customer history
└── README.md
```

## How to Install and Run
1. Ensure Python 3 is installed on your local machine.
2. Clone or download this repository.
3. Open a terminal/command prompt in the `cyber-cafe-management-system/` directory.
4. Install Flask (if not already installed):
   ```bash
   pip install flask
   ```
5. Run the application:
   ```bash
   python app.py
   ```
6. Open your web browser and navigate to: `http://127.0.0.1:5000`

## Default Credentials
When the application runs for the very first time, it automatically creates the `database.db` file and seeds it with default users:

**Admin Login**
- Username: `admin`
- Password: `admin123`

**Staff Login**
- Username: `staff`
- Password: `staff123`

## Main Workflows
### Creating a Bill
1. **Start a Session**: Go to "Room View", click an "Available" PC, select a Customer, and start the timer.
2. **End a Session**: Once finished, click the "In Use" PC to stop the timer. This frees the PC and saves the calculated usage charge.
3. *(Phase 6 note: The Billing screens are part of the core logic processing; simply process the session through the designated billing endpoints, attaching extra services where needed, marking Cash or UPI).*
4. **Print Receipt**: Access the Bill History or Customer Details to view a printer-friendly A4 receipt.

### Reports & Backup (Admin Only)
- **Reports**: Admins can view complete revenue, usage, and service analytics by selecting "Reports" on the sidebar.
- **Backup**: Admins can navigate to `/admin/backup` to automatically download a snapshot of the live SQLite database.

## Security Overview
- **Strict Role Boundaries**: Staff accounts are securely locked out of all analytical, settings, and rate-editing routes via server-side session validation.
- **Atomic Transactions**: Multi-table insertions (like finalizing a bill and its items) are protected by `rollback()` mechanisms.
- **Historical Accuracy**: Changing a computer's hourly rate today will **not** modify past completed bills, as snapshot data is aggressively stored in `sessions` and `bill_items` logs.
- **Foreign Key Integrity**: Enforced strictly at the database connector level (`PRAGMA foreign_keys = ON`).
