"""
Quick check of Phase 1 environment variables (without exposing values)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from config import config

print("Phase 1 Environment Variable Check")
print("=" * 50)

# Check Phase 1 critical variables
checks = [
    ("POLYMARKET_API_KEY", config.POLYMARKET_API_KEY),
    ("POLYGON_RPC_URL", config.POLYGON_RPC_URL),
    ("DATABASE_URL", config.DATABASE_URL),
]

all_good = True
for name, value in checks:
    if not value or value in ['your_api_key_here', 'your_token', 'postgresql://user:password@localhost:5432/geoint']:
        print(f"[X] {name:<25} NOT SET or using default value")
        all_good = False
    else:
        # Show first 10 chars to verify it's set, hide the rest
        preview = str(value)[:10] + "..." if len(str(value)) > 10 else str(value)
        print(f"[+] {name:<25} CONFIGURED ({preview})")

print()
if all_good:
    print("[SUCCESS] All Phase 1 environment variables configured!")
    print("Ready to start API integration.")
else:
    print("[WARNING] Some variables not configured.")
    print("You can still proceed - we'll use default/test values.")

print()
print("Note: Telegram credentials are optional for Phase 1")
