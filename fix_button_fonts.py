# Read the file
with open('rek_game.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Split by lines to process button stylesheets
lines = content.split('\n')
new_lines = []

for i, line in enumerate(lines):
    # Check if this line contains QPushButton style definition
    if 'QPushButton' in line and 'font-family' in line:
        # Replace SiemReap with Muol Light in button styles
        if 'Khmer OS SiemReap' in line:
            line = line.replace('Khmer OS SiemReap', 'Khmer OS Muol Light')
        # Also handle FONT_KHMER variable
        if '{FONT_KHMER}' in line and 'QPushButton' in line:
            line = line.replace('{FONT_KHMER}', "'Khmer OS Muol Light'")
    
    new_lines.append(line)

content = '\n'.join(new_lines)

# Write back
with open('rek_game.py', 'w', encoding='utf-8') as f:
    f.write(content)

# Count instances
muol_count = content.count('Khmer OS Muol Light')
siem_count = content.count('Khmer OS SiemReap')

print(f'Buttons reverted to Khmer OS Muol Light')
print(f'Khmer OS Muol Light total: {muol_count}')
print(f'Khmer OS SiemReap total: {siem_count}')
