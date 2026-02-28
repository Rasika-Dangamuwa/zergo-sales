import subprocess
import sys

# Run makemigrations with automatic "N" answers
process = subprocess.Popen(
    [sys.executable, 'manage.py', 'makemigrations', 'products'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# Auto-answer all rename questions with "N"
output, errors = process.communicate(input='N\n' * 20)
print(output)
if errors:
    print(errors, file=sys.stderr)
sys.exit(process.returncode)
