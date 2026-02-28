with open('templates/sales/eod_detail.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

with open('templates/sales/eod_detail.html', 'w', encoding='utf-8') as f:
    f.writelines(lines[:323] + lines[622:])

print("Fixed eod_detail.html - removed lines 324-622")
