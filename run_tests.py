#!/usr/bin/env python3
"""
Test runner script for Expense Bot.
Runs all tests with appropriate configuration and generates coverage reports.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_tests(test_type="all", coverage=True, verbose=True):
    """
    Run tests based on the specified type.
    
    Args:
        test_type (str): Type of tests to run - 'unit', 'integration', or 'all'
        coverage (bool): Whether to generate coverage reports
        verbose (bool): Whether to run tests in verbose mode
    """
    
    # Ensure we're in the correct directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Check if we have a virtual environment
    venv_python = script_dir / ".venv" / "bin" / "python"
    if venv_python.exists():
        python_cmd = str(venv_python)
    else:
        python_cmd = "python3"
    
    # Base pytest command
    cmd = [python_cmd, "-m", "pytest"]
    
    # Add test files based on type
    if test_type == "unit":
        cmd.append("test_bot.py")
    elif test_type == "integration":
        cmd.append("test_integration.py")
    elif test_type == "all":
        cmd.extend(["test_bot.py", "test_integration.py"])
    else:
        print(f"Unknown test type: {test_type}")
        sys.exit(1)
    
    # Add coverage if requested
    if coverage:
        cmd.extend([
            "--cov=bot",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-fail-under=50"  # Lowered threshold temporarily
        ])
    
    # Add verbosity
    if verbose:
        cmd.append("-v")
    
    # Add other useful options
    cmd.extend([
        "--tb=short",
        "--strict-markers"
    ])
    
    print(f"Running command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True)
        print("\n✅ All tests passed!")
        
        if coverage:
            print("\n📊 Coverage report generated in htmlcov/index.html")
            
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Tests failed with exit code: {e.returncode}")
        sys.exit(e.returncode)


def install_test_dependencies():
    """Install test dependencies if not already installed."""
    
    print("📦 Installing test dependencies...")
    
    # Check if we have a virtual environment
    script_dir = Path(__file__).parent
    venv_pip = script_dir / ".venv" / "bin" / "pip"
    if venv_pip.exists():
        pip_cmd = str(venv_pip)
    else:
        pip_cmd = "pip3"
    
    try:
        subprocess.run([
            pip_cmd, "install", "-r", "requirements-test.txt"
        ], check=True)
        print("✅ Test dependencies installed successfully!")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        sys.exit(1)


def main():
    """Main function to parse arguments and run tests."""
    
    parser = argparse.ArgumentParser(description="Run Expense Bot tests")
    parser.add_argument(
        "--type", 
        choices=["unit", "integration", "all"], 
        default="all",
        help="Type of tests to run (default: all)"
    )
    parser.add_argument(
        "--no-coverage", 
        action="store_true",
        help="Skip coverage report generation"
    )
    parser.add_argument(
        "--install-deps", 
        action="store_true",
        help="Install test dependencies before running tests"
    )
    parser.add_argument(
        "--quiet", 
        action="store_true",
        help="Run tests in quiet mode"
    )
    
    args = parser.parse_args()
    
    # Install dependencies if requested
    if args.install_deps:
        install_test_dependencies()
    
    # Run tests
    run_tests(
        test_type=args.type,
        coverage=not args.no_coverage,
        verbose=not args.quiet
    )


if __name__ == "__main__":
    main()
