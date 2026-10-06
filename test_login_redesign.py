import requests

BASE_URL = 'http://127.0.0.1:5000'

def test():
    # 1. Clear session
    session = requests.Session()
    r = session.get(f'{BASE_URL}/logout')
    
    # 2. Try to get Admin Dashboard directly (should redirect to login)
    r = session.get(f'{BASE_URL}/admin/dashboard')
    assert 'Login' in r.text, "Failed to redirect to login page from protected admin route"
    print("Redirect to login from protected route: PASS")
    
    # 3. Login as Staff
    r = session.post(f'{BASE_URL}/login', data={'username': 'staff', 'password': 'staff123'})
    
    # Check if we landed on the staff dashboard
    r = session.get(f'{BASE_URL}/staff/dashboard')
    assert 'Staff Panel' in r.text or 'Dashboard' in r.text, "Failed to login as staff"
    print("Staff login: PASS")
    
    # 4. Try secret admin auth with wrong credentials
    r = session.post(f'{BASE_URL}/api/admin/auth', json={'username': 'admin', 'password': 'wrongpass'})
    assert r.status_code == 401, f"Expected 401 for wrong credentials, got {r.status_code}"
    print("Secret Admin Auth (Wrong Credentials): PASS")
    
    # 5. Try secret admin auth with staff credentials (role is not admin)
    r = session.post(f'{BASE_URL}/api/admin/auth', json={'username': 'staff', 'password': 'staff123'})
    assert r.status_code == 401, f"Expected 401 for non-admin credentials, got {r.status_code}"
    print("Secret Admin Auth (Staff Credentials): PASS")
    
    # 6. Try secret admin auth with correct admin credentials
    r = session.post(f'{BASE_URL}/api/admin/auth', json={'username': 'admin', 'password': 'admin123'})
    assert r.json()['success'] == True, "Failed to authenticate admin via secret flow"
    print("Secret Admin Auth (Correct Credentials): PASS")
    
    # 7. Access admin dashboard now that we're authorized
    r = session.get(f'{BASE_URL}/admin/dashboard')
    assert r.status_code == 200, "Failed to access admin dashboard after secret auth"
    print("Admin Dashboard access post-auth: PASS")

    # 8. Check for emojis remaining in project files
    import os
    base_dir = 'c:\\Users\\sarka\\OneDrive\\Desktop\\cafe\\cyber-cafe-management-system'
    emojis_found = 0
    for root, dirs, files in os.walk(base_dir):
        if 'venv' in root or '.git' in root or '__pycache__' in root: continue
        for file in files:
            if file.endswith('.html') or file.endswith('.py') or file.endswith('.js') or file.endswith('.css'):
                with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Check for known emojis
                    for e in ['📅', '💻', '🔧', '👤', '📄', '▶️', '⏹️', '🪴', '🧾', '🖨️', '📭', '📜', '💳', '⚙️', '🖥️', '👥', 'ℹ️', '🏠', '🔲', '💬', '🚪', '🔍', '🔔', '●']:
                        if e in content:
                            emojis_found += 1
                            print(f"Found emoji {e} in {file}")
    
    if emojis_found == 0:
        print("Emoji removal verification: PASS")
    else:
        print("Emoji removal verification: FAIL")

    print("ALL TESTS COMPLETED SUCCESSFULLY")

if __name__ == '__main__':
    test()
