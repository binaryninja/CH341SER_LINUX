#!/usr/bin/env python3
"""
ESP Monitor Installation Verification Script
============================================
This script verifies that all files are present and the basic structure
is correct for the ESP Monitor database enhancement.

Usage:
    python3 verify_installation.py
"""

import os
import sys
from pathlib import Path

def check_file_exists(filepath, description):
    """Check if a file exists and return status"""
    if os.path.exists(filepath):
        size = os.path.getsize(filepath)
        print(f"✅ {description}: {filepath} ({size} bytes)")
        return True
    else:
        print(f"❌ {description}: {filepath} - NOT FOUND")
        return False

def check_python_version():
    """Check Python version requirements"""
    version = sys.version_info
    if version >= (3, 7):
        print(f"✅ Python version: {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"❌ Python version: {version.major}.{version.minor}.{version.micro} (requires 3.7+)")
        return False

def check_imports():
    """Check if imports work"""
    import_results = {}

    # Test standard library imports
    try:
        import sqlite3
        import json
        import datetime
        import threading
        print("✅ Standard library imports: OK")
        import_results['stdlib'] = True
    except ImportError as e:
        print(f"❌ Standard library imports failed: {e}")
        import_results['stdlib'] = False

    # Test optional imports
    optional_imports = {
        'pandas': 'pip install pandas',
        'matplotlib': 'pip install matplotlib',
        'seaborn': 'pip install seaborn',
        'jinja2': 'pip install jinja2',
        'serial': 'pip install pyserial'
    }

    for module, install_cmd in optional_imports.items():
        try:
            __import__(module)
            print(f"✅ Optional dependency: {module}")
            import_results[module] = True
        except ImportError:
            print(f"⚠️  Optional dependency missing: {module} (install with: {install_cmd})")
            import_results[module] = False

    return import_results

def check_file_structure():
    """Check if all required files are present"""
    files_to_check = [
        # Core files
        ("esp_monitor.py", "Main ESP Monitor script"),
        ("database_manager.py", "Database management module"),
        ("report_generator.py", "Report generation module"),

        # Configuration and setup
        ("requirements.txt", "Python dependencies"),
        ("install_dependencies.sh", "Installation script"),

        # Documentation
        ("DATABASE_FEATURES.md", "Database features documentation"),
        ("README_DATABASE_ENHANCEMENTS.md", "Enhancement summary"),

        # Examples and testing
        ("demo_database_features.py", "Interactive demo script"),
        ("test_database_features.py", "Unit tests"),
        ("usage_examples.py", "Usage examples"),
        ("verify_installation.py", "This verification script")
    ]

    print("\n📁 Checking file structure...")
    print("-" * 50)

    all_present = True
    for filepath, description in files_to_check:
        if not check_file_exists(filepath, description):
            all_present = False

    return all_present

def check_basic_functionality():
    """Test basic functionality without requiring all dependencies"""
    print("\n🧪 Testing basic functionality...")
    print("-" * 50)

    success = True

    # Test 1: Database manager import
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from database_manager import DatabaseManager
        print("✅ Database manager import successful")
    except ImportError as e:
        print(f"❌ Database manager import failed: {e}")
        success = False

    # Test 2: ESP monitor import
    try:
        from esp_monitor import ESPMonitor
        print("✅ ESP monitor import successful")
    except ImportError as e:
        print(f"❌ ESP monitor import failed: {e}")
        success = False

    # Test 3: Report generator import (may fail due to matplotlib)
    try:
        from report_generator import ReportGenerator
        print("✅ Report generator import successful")
    except ImportError as e:
        print(f"⚠️  Report generator import failed: {e}")
        print("   This is expected if matplotlib/seaborn are not installed")

    # Test 4: Basic database operations (if imports succeeded)
    if success:
        try:
            import tempfile
            temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
            temp_db.close()

            db = DatabaseManager(temp_db.name)
            print("✅ Database creation successful")

            # Test table creation
            cursor = db.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            expected_tables = ['connection_events', 'device_status', 'performance_metrics', 'performance_baselines']

            if all(table in tables for table in expected_tables):
                print("✅ Database schema creation successful")
            else:
                print("❌ Database schema incomplete")
                success = False

            db.close()
            os.unlink(temp_db.name)

        except Exception as e:
            print(f"❌ Database functionality test failed: {e}")
            success = False

    return success

def check_configuration():
    """Check if configuration file exists or can be created"""
    print("\n⚙️  Checking configuration...")
    print("-" * 50)

    config_file = "esp_config.json"

    if os.path.exists(config_file):
        print(f"✅ Configuration file exists: {config_file}")
        try:
            import json
            with open(config_file, 'r') as f:
                config = json.load(f)
            print("✅ Configuration file is valid JSON")
            return True
        except json.JSONDecodeError:
            print("❌ Configuration file has invalid JSON")
            return False
    else:
        print(f"⚠️  Configuration file not found: {config_file}")
        print("   Will be created automatically on first run")
        return True

def print_summary(results):
    """Print installation summary"""
    print("\n" + "="*60)
    print("INSTALLATION VERIFICATION SUMMARY")
    print("="*60)

    total_checks = len(results)
    passed_checks = sum(1 for result in results.values() if result)

    print(f"Total checks: {total_checks}")
    print(f"Passed: {passed_checks}")
    print(f"Failed: {total_checks - passed_checks}")

    if passed_checks == total_checks:
        print("\n🎉 All checks passed! Installation appears to be complete.")
        print("\nNext steps:")
        print("1. Install optional dependencies: pip install -r requirements.txt")
        print("2. Run demo: python3 demo_database_features.py")
        print("3. Start monitoring: python3 esp_monitor.py")
    else:
        print(f"\n⚠️  {total_checks - passed_checks} checks failed.")
        print("\nRecommended actions:")

        if not results.get('files'):
            print("• Some files are missing - check the installation")

        if not results.get('python_version'):
            print("• Upgrade Python to version 3.7 or higher")

        if not results.get('basic_functionality'):
            print("• Check for syntax errors in the Python files")

        if not results.get('imports', {}).get('pandas', True):
            print("• Install dependencies: pip install -r requirements.txt")
            print("• Or run: ./install_dependencies.sh")

def main():
    """Main verification function"""
    print("ESP Monitor Installation Verification")
    print("="*60)
    print("This script checks if the ESP Monitor database enhancement")
    print("is properly installed and ready to use.")
    print("="*60)

    results = {}

    # Check Python version
    results['python_version'] = check_python_version()

    # Check file structure
    results['files'] = check_file_structure()

    # Check imports
    results['imports'] = check_imports()

    # Check basic functionality
    results['basic_functionality'] = check_basic_functionality()

    # Check configuration
    results['configuration'] = check_configuration()

    # Print summary
    print_summary(results)

    # Return appropriate exit code
    if all(results.values()):
        return 0
    else:
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nVerification interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error during verification: {e}")
        sys.exit(1)
