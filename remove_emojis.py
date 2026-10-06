import os
import re

# We want to remove standard emojis and icons. We'll specifically target the ones found in the project.
# And we can also use a broad regex for emojis.
import sys

def remove_emojis_from_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # List of known emojis/symbols to remove
    emojis = [
        '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '',
        '', '', '', '', '', '', '', ''
    ]
    
    # We can also use a regex for typical emoji blocks
    # Emoticons: 1F600-1F64F
    # Misc Symbols: 2600-26FF
    # Dingbats: 2700-27BF
    # Supplemental Symbols and Pictographs: 1F900-1F9FF
    # Symbols & Pictographs Ext-A: 1FA70-1FAFF
    # Misc Symbols and Pictographs: 1F300-1F5FF
    # Transport and Map Symbols: 1F680-1F6FF
    
    # Let's just do a blanket regex for characters outside basic ASCII, 
    # EXCEPT for the Indian Rupee symbol (₹, \u20b9) and basic punctuation/arrows if any (we can keep basic latin).
    
    new_content = ""
    for char in content:
        code = ord(char)
        # Keep ASCII
        if code <= 127:
            new_content += char
        # Keep Rupee symbol
        elif char == '₹':
            new_content += char
        # Keep Copyright or similar standard latin-1 punctuation if needed
        elif code in [0xA9, 0xAE, 0xB0, 0x2013, 0x2014, 0x2018, 0x2019, 0x201C, 0x201D, 0x2022, 0x2026]: 
            new_content += char
        else:
            # Drop all other non-ASCII characters (which are mostly emojis in this codebase)
            pass

    if content != new_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Cleaned {filepath}")

if __name__ == '__main__':
    base_dir = 'c:\\Users\\sarka\\OneDrive\\Desktop\\cafe\\cyber-cafe-management-system'
    for root, dirs, files in os.walk(base_dir):
        if 'venv' in root or '.git' in root or '__pycache__' in root:
            continue
        for file in files:
            if file.endswith('.html') or file.endswith('.py') or file.endswith('.js') or file.endswith('.css'):
                filepath = os.path.join(root, file)
                remove_emojis_from_file(filepath)
    print("Done removing emojis.")
