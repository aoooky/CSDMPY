
import subprocess
import sys


def run_command(cmd, description):
    """Выполнить команду и показать результат"""
    print(f"\n{'='*60}")
    print(f"⏳ {description}...")
    print(f"{'='*60}")
    print(f"Command: {cmd}")
    print()
    
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=False,
        text=True
    )
    
    if result.returncode == 0:
        print(f"✅ {description} - SUCCESS")
        return True
    else:
        print(f"❌ {description} - FAILED")
        return False


def main():
    print("="*60)
    print("CS Demo Manager - Dependency Fix Script")
    print("="*60)
    print()
    print("This script will:")
    print("1. Uninstall conflicting packages (numpy, pandas)")
    print("2. Install compatible versions")
    print()
    
    response = input("Continue? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return
    
    steps = [
        (
            f"{sys.executable} -m pip uninstall numpy pandas -y",
            "Uninstalling numpy and pandas"
        ),
        (
            f"{sys.executable} -m pip install numpy==1.26.4",
            "Installing numpy 1.26.4"
        ),
        (
            f"{sys.executable} -m pip install pandas==2.2.0",
            "Installing pandas 2.2.0"
        ),
    ]
    
    success_count = 0
    for cmd, desc in steps:
        if run_command(cmd, desc):
            success_count += 1
    
    print()
    print("="*60)
    if success_count == len(steps):
        print("✅ All fixes applied successfully!")
        print("="*60)
        print()
        print("Next steps:")
        print("1. Test imports:")
        print("   python -c \"from src.core.models import Match; print('✓ OK')\"")
        print()
        print("2. Run parser test:")
        print("   python test_parser.py demos/test.dem")
        return 0
    else:
        print(f"⚠️  Some steps failed ({success_count}/{len(steps)} succeeded)")
        print("="*60)
        print()
        print("Try manual installation:")
        print("  pip uninstall numpy pandas -y")
        print("  pip install numpy==1.26.4 pandas==2.2.0")
        return 1


if __name__ == "__main__":
    sys.exit(main())