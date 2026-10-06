import requests
import json

BASE_URL = 'http://127.0.0.1:5000'
s = requests.Session()

def run_tests():
    print("Running Tests...")
    
    # 1. Staff Login
    r = s.post(f"{BASE_URL}/login", data={'username':'staff', 'password':'staff123'})
    assert 'Dashboard' in r.text, "Staff login failed"
    
    # 2. Secret Admin Auth
    r = s.post(f"{BASE_URL}/api/admin/auth", json={'username':'admin', 'password':'admin123'})
    assert r.json().get('success') == True, "Admin auth failed"
    
    # 3. Access Admin Dashboard
    r = s.get(f"{BASE_URL}/admin/dashboard")
    assert 'Good Morning, Admin!' in r.text, "Admin Dashboard failed"
    
    # 4. Access Admin Staff & Add Staff
    r = s.get(f"{BASE_URL}/admin/staff")
    assert 'Staff Management' in r.text, "Admin Staff UI failed"
    
    # 5. Exit Admin
    r = s.get(f"{BASE_URL}/admin/exit")
    assert 'Active Sessions' in r.text or 'Dashboard' in r.text, "Exit Admin failed to redirect to Staff Dashboard"
    
    # 6. Direct URL block check
    r_block = s.get(f"{BASE_URL}/admin/dashboard")
    assert 'Admin access required' in r_block.text or 'Login' in r_block.text or r_block.url.endswith('/login'), "Direct URL protection failed"
    
    # 7. Logout
    r = s.get(f"{BASE_URL}/logout")

if __name__ == '__main__':
    run_tests()
    print("Tests executed successfully.")
