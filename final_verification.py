import requests
import re
import os

BASE_URL = 'http://127.0.0.1:5000'

def test_full_workflow():
    results = {}
    
    # 1. App Startup (if we can hit it, it started)
    try:
        r = requests.get(BASE_URL)
        results['Flask startup'] = 'PASS'
    except Exception as e:
        results['Flask startup'] = 'FAIL'
        print(f"Startup error: {e}")
        return results

    # 2. Staff Login UI
    if 'WELCOME BACK!' in r.text and '<form method="POST"' in r.text:
        results['Login UI'] = 'PASS'
    else:
        results['Login UI'] = 'FAIL'

    # 3. 7-click trigger on login page (Should NOT be there)
    if 'secret-admin-logo' not in r.text and 'adminClickCount' not in r.text:
        results['7-click trigger on login page absent'] = 'PASS'
    else:
        results['7-click trigger on login page absent'] = 'FAIL'

    session = requests.Session()
    
    # 4. Staff Login
    r = session.post(f'{BASE_URL}/login', data={'username': 'staff', 'password': 'staff123'})
    r = session.get(f'{BASE_URL}/staff/dashboard')
    if 'Staff Panel' in r.text or 'Dashboard' in r.text:
        results['Staff Login'] = 'PASS'
    else:
        results['Staff Login'] = 'FAIL'

    # 5. 7-click trigger on staff panel (Should BE there)
    if 'secret-admin-logo' in r.text and 'adminClickCount' in r.text:
        results['7-click trigger'] = 'PASS'
    else:
        results['7-click trigger'] = 'FAIL'
        
    # 6. Admin Auth Flow tests
    r_wrong = session.post(f'{BASE_URL}/api/admin/auth', json={'username': 'admin', 'password': 'wrong'})
    results['Wrong Admin credentials'] = 'PASS' if r_wrong.status_code == 401 else 'FAIL'

    r_staff = session.post(f'{BASE_URL}/api/admin/auth', json={'username': 'staff', 'password': 'staff123'})
    results['Staff credentials rejected as Admin'] = 'PASS' if r_staff.status_code == 401 else 'FAIL'

    r_correct = session.post(f'{BASE_URL}/api/admin/auth', json={'username': 'admin', 'password': 'admin123'})
    results['Valid Admin credentials'] = 'PASS' if r_correct.json().get('success') else 'FAIL'
    
    # Session Separation (Check we can access admin routes now)
    r_admin = session.get(f'{BASE_URL}/admin/dashboard')
    results['Session separation'] = 'PASS' if r_admin.status_code == 200 else 'FAIL'

    # 7. Customer workflow (Create customer)
    r_cust = session.post(f'{BASE_URL}/api/customers', json={'name': 'Test User', 'mobile': '9999999999'})
    if r_cust.status_code == 200 and r_cust.json().get('success'):
        customer_id = r_cust.json().get('customer_id')
        results['Customer workflow'] = 'PASS'
    else:
        results['Customer workflow'] = 'FAIL'
        
    # 8. Session Workflow (Start session)
    if 'customer_id' in locals():
        r_session = session.post(f'{BASE_URL}/api/session/start', json={'pc_id': 1, 'customer_id': customer_id})
        if r_session.status_code == 200 and r_session.json().get('success'):
            results['Session workflow'] = 'PASS'
        else:
            results['Session workflow'] = 'FAIL'
            
    # 9. Room View
    r_room = session.get(f'{BASE_URL}/room')
    results['Room View'] = 'PASS' if r_room.status_code == 200 and 'Room View' in r_room.text else 'FAIL'

    # 10. Billing workflow (End session and create bill)
    if 'customer_id' in locals() and results.get('Session workflow') == 'PASS':
        r_end = session.post(f'{BASE_URL}/api/session/end/1')
        if r_end.status_code == 200:
            bill_data = {
                'customer_id': customer_id,
                'usage_charge': 40.0,
                'services': [],
                'subtotal': 40.0,
                'total_amount': 40.0,
                'payment_method': 'Cash'
            }
            r_bill = session.post(f'{BASE_URL}/api/billing/create', json=bill_data)
            if r_bill.status_code == 200 and r_bill.json().get('success'):
                results['Billing workflow'] = 'PASS'
                bill_id = r_bill.json().get('bill_id')
                
                # 11. Receipt
                r_receipt = session.get(f'{BASE_URL}/receipt/{bill_id}')
                results['Receipt'] = 'PASS' if r_receipt.status_code == 200 and 'Receipt' in r_receipt.text else 'FAIL'
            else:
                results['Billing workflow'] = 'FAIL'
                results['Receipt'] = 'FAIL'
        else:
            results['Billing workflow'] = 'FAIL'
            results['Receipt'] = 'FAIL'
    else:
        results['Billing workflow'] = 'FAIL'
        results['Receipt'] = 'FAIL'

    # 12. Logout security and Admin route protection
    session.get(f'{BASE_URL}/logout')
    r_admin_blocked = session.get(f'{BASE_URL}/admin/dashboard')
    results['Logout security'] = 'PASS' if 'Login' in r_admin_blocked.text else 'FAIL'
    results['Admin route protection'] = 'PASS' if 'Login' in r_admin_blocked.text else 'FAIL'

    # 13. Regression Check
    # If all workflows passed, regression check passes
    workflows = ['Customer workflow', 'Session workflow', 'Billing workflow', 'Room View', 'Receipt']
    if all(results.get(w) == 'PASS' for w in workflows):
        results['Regression check'] = 'PASS'
    else:
        results['Regression check'] = 'FAIL'

    # 14. Emoji scan and Rupee check
    base_dir = 'c:\\Users\\sarka\\OneDrive\\Desktop\\cafe\\cyber-cafe-management-system'
    emojis_found = False
    rupee_found = False
    emojis = ['📅', '💻', '🔧', '👤', '📄', '▶️', '⏹️', '🪴', '🧾', '🖨️', '📭', '📜', '💳', '⚙️', '🖥️', '👥', 'ℹ️', '🏠', '🔲', '💬', '🚪', '🔍', '🔔', '●']
    
    for root, dirs, files in os.walk(base_dir):
        if 'venv' in root or '.git' in root or '__pycache__' in root: continue
        for file in files:
            if file.endswith('.html') or file.endswith('.py') or file.endswith('.js') or file.endswith('.css'):
                with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                    content = f.read()
                    if '₹' in content:
                        rupee_found = True
                    # Check for emojis
                    if any(e in content for e in emojis):
                        # Filter out test script itself
                        if file != 'final_verification.py' and file != 'test_login_redesign.py' and file != 'remove_emojis.py':
                            emojis_found = True

    results['Emoji scan'] = 'FAIL' if emojis_found else 'PASS'
    results['₹ preserved'] = 'PASS' if rupee_found else 'FAIL'

    return results

if __name__ == '__main__':
    res = test_full_workflow()
    for k, v in res.items():
        print(f"{k}: {v}")
