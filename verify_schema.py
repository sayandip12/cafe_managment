import sqlite3

def verify_schema():
    conn = sqlite3.connect('database/database.db')
    conn.row_factory = sqlite3.Row
    
    tables = [r['name'] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print('Tables:', tables)
    
    for t in tables:
        cols = [r['name'] for r in conn.execute(f"PRAGMA table_info({t})").fetchall()]
        print(f'{t}: {cols}')
        
    conn.close()

if __name__ == '__main__':
    verify_schema()
