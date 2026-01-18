"""
Setup validation script to check environment and dependencies
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from config import config


def check_python_version():
    """Check Python version is 3.8+"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        return False, f"Python 3.8+ required, found {version.major}.{version.minor}"
    return True, f"Python {version.major}.{version.minor}.{version.micro}"


def check_dependencies():
    """Check if key dependencies are installed"""
    required = [
        'requests',
        'web3',
        'sqlalchemy',
        'dotenv'
    ]

    missing = []
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)

    if missing:
        return False, f"Missing packages: {', '.join(missing)}"
    return True, "All Phase 1 packages installed"


def check_environment_variables():
    """Check if critical environment variables are set"""
    critical = []
    warnings = []

    # Critical checks
    if not config.DATABASE_URL or 'localhost' in config.DATABASE_URL:
        warnings.append("DATABASE_URL uses default/localhost value")

    if not config.POLYGON_RPC_URL or 'YOUR_KEY' in str(config.POLYGON_RPC_URL):
        warnings.append("POLYGON_RPC_URL not configured")

    if not config.POLYMARKET_API_KEY or config.POLYMARKET_API_KEY == 'your_api_key_here':
        warnings.append("POLYMARKET_API_KEY not configured")

    if not config.TELEGRAM_BOT_TOKEN or config.TELEGRAM_BOT_TOKEN == 'your_token':
        critical.append("TELEGRAM_BOT_TOKEN not configured")

    if not config.TELEGRAM_CHAT_ID or config.TELEGRAM_CHAT_ID == 'your_chat_id':
        critical.append("TELEGRAM_CHAT_ID not configured")

    status = "PASS"
    message = "Environment configured"

    if critical:
        status = "FAIL"
        message = f"Critical: {', '.join(critical)}"
    elif warnings:
        status = "WARN"
        message = f"Warnings: {', '.join(warnings)}"

    return status, message


def check_directories():
    """Check if required directories exist"""
    required_dirs = [
        config.DATA_DIR,
        config.LOGS_DIR,
    ]

    missing = [d for d in required_dirs if not d.exists()]

    if missing:
        # Try to create them
        try:
            for d in missing:
                d.mkdir(parents=True, exist_ok=True)
            return True, "Created missing directories"
        except Exception as e:
            return False, f"Failed to create directories: {e}"

    return True, "All directories exist"


def main():
    """Run all validation checks"""
    print("=" * 60)
    print("Geopolitical Insider Trading Detection System")
    print("Setup Validation")
    print("=" * 60)
    print()

    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Environment Variables", check_environment_variables),
        ("Directories", check_directories),
    ]

    results = []
    for name, check_func in checks:
        try:
            success, message = check_func()
            if isinstance(success, str):  # For check_environment_variables
                status = success
            else:
                status = "+ PASS" if success else "X FAIL"
            results.append((name, status, message))
        except Exception as e:
            results.append((name, "X ERROR", str(e)))

    # Print results
    max_name_len = max(len(name) for name, _, _ in results)
    for name, status, message in results:
        print(f"{name:<{max_name_len + 2}} [{status}] {message}")

    print()

    # Overall status
    failed = any("FAIL" in status or "ERROR" in status for _, status, _ in results)
    warnings = any("WARN" in status for _, status, _ in results)

    if failed:
        print("[FAILED] Setup validation FAILED - please fix errors above")
        return 1
    elif warnings:
        print("[WARNING]  Setup validation passed with WARNINGS")
        print("   System will work but some features may be limited")
        return 0
    else:
        print("[SUCCESS] Setup validation PASSED - system ready to run")
        return 0


if __name__ == '__main__':
    sys.exit(main())
