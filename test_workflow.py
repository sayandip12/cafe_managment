import requests
import time

BASE_URL = 'http://127.0.0.1:5000'

def test():
    # 1. Login as staff to get session cookie
    session = requests.Session()
    r = session.post(f'{BASE_URL}/login', data={'username': 'staff', 'password': 'staff123'})
    
    # 2. Add Customer A
    r = session.post(f'{BASE_URL}/api/customer/add', json={
        'name': 'Customer A', 'mobile': '1111111111', 'email': '', 'address': ''
    })
    print("Add Cust A:", r.json())
    
    # 3. Add Customer B
    r = session.post(f'{BASE_URL}/api/customer/add', json={
        'name': 'Customer B', 'mobile': '2222222222', 'email': '', 'address': ''
    })
    print("Add Cust B:", r.json())
    
    # Get customers list to find their IDs
    r = session.get(f'{BASE_URL}/api/search/customers?q=Customer')
    customers = r.json()['customers']
    cust_a = next(c for c in customers if c['name'] == 'Customer A')['id']
    cust_b = next(c for c in customers if c['name'] == 'Customer B')['id']
    print(f"IDs - CustA: {cust_a}, CustB: {cust_b}")
    
    # 4. Start Session A (PC 1)
    r = session.post(f'{BASE_URL}/api/session/start', json={
        'computer_id': 1, 'customer_id': cust_a
    })
    print("Start Session A:", r.json())
    
    # 5. Start Session B (PC 2)
    r = session.post(f'{BASE_URL}/api/session/start', json={
        'computer_id': 2, 'customer_id': cust_b
    })
    print("Start Session B:", r.json())
    
    # We need to end sessions. The endpoint requires session_id. 
    # We can fetch the active sessions from the DB.
    import sqlite3
    conn = sqlite3.connect('database/database.db')
    conn.row_factory = sqlite3.Row
    active = conn.execute('SELECT id, customer_id FROM sessions WHERE status="Active"').fetchall()
    
    sess_a_id = next(s['id'] for s in active if s['customer_id'] == cust_a)
    sess_b_id = next(s['id'] for s in active if s['customer_id'] == cust_b)
    
    time.sleep(1) # wait a bit
    
    # 6. End Session A
    r = session.post(f'{BASE_URL}/api/session/end', json={'session_id': sess_a_id})
    print("End Session A:", r.json())
    
    # 7. End Session B
    r = session.post(f'{BASE_URL}/api/session/end', json={'session_id': sess_b_id})
    print("End Session B:", r.json())
    
    # 8. Create Bill A
    r = session.post(f'{BASE_URL}/billing/create/{sess_a_id}', json={
        'payment_method': 'Cash', 'payment_status': 'Paid', 'items': []
    })
    bill_a_id = r.json()['bill_id']
    print("Bill A:", r.json())
    
    # 9. Create Bill B
    r = session.post(f'{BASE_URL}/billing/create/{sess_b_id}', json={
        'payment_method': 'UPI', 'payment_status': 'Paid', 'items': []
    })
    bill_b_id = r.json()['bill_id']
    print("Bill B:", r.json())
    
    # Verify Receipt A doesn't contain Customer B
    r = session.get(f'{BASE_URL}/billing/receipt/{bill_a_id}')
    assert 'Customer B' not in r.text
    assert 'Customer A' in r.text
    print("Receipt A verified")
    
    # Verify Receipt B doesn't contain Customer A
    r = session.get(f'{BASE_URL}/billing/receipt/{bill_b_id}')
    assert 'Customer A' not in r.text
    assert 'Customer B' in r.text
    print("Receipt B verified")
    print("SUCCESS: End to end billing isolation works!")

if __name__ == '__main__':
    test()
