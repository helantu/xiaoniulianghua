import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('E:/xiaoniulianghua/logs/niuquant.log', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for line in lines:
    if ('2026-04-04 21:3' in line or '2026-04-04 21:4' in line or '2026-04-04 21:5' in line) \
       and ('AI' in line or '活跃' in line):
        print(line.rstrip())
