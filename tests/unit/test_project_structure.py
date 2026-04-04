"""
Unit tests for project structure validation.

Tests to verify that all required __init__.py files exist in expected directories,
requirements.txt is properly configured, pytest.ini exists, and main.py exists.
"""

import os
from pathlib import Path
import pytest


class TestProjectStructure:
    """Test class for validating project structure."""

    @pytest.fixture
    def project_root(self):
        """Get the project root directory."""
        return Path(__file__).parent.parent.parent

    def test_all_init_files_exist(self, project_root):
        """Test that all __init__.py files exist in expected directories."""
        expected_init_files = [
            "core/__init__.py",
            "core/align/__init__.py", 
            "core/inspection/__init__.py",
            "core/evaluation/__init__.py",
            "core/analyzers/__init__.py",
            "core/providers/__init__.py",
            "ui/__init__.py",
            "ui/pages/__init__.py",
            "ui/dialogs/__init__.py", 
            "ui/components/__init__.py",
            "config/__init__.py",
            "tests/__init__.py",
            "tests/unit/__init__.py",
            "tests/integration/__init__.py"
        ]
        
        for init_file in expected_init_files:
            init_path = project_root / init_file
            assert init_path.exists(), f"Missing __init__.py file: {init_file}"
            assert init_path.is_file(), f"Path is not a file: {init_file}"

    def test_requirements_txt_exists_and_not_empty(self, project_root):
        """Test that requirements.txt exists and is not empty."""
        requirements_file = project_root / "requirements.txt"
        assert requirements_file.exists(), "requirements.txt file is missing"
        assert requirements_file.is_file(), "requirements.txt is not a file"
        
        content = requirements_file.read_text().strip()
        assert content, "requirements.txt is empty"
        
        # Check for essential dependencies
        assert "opencv-python-headless" in content
        assert "PyQt6" in content
        assert "pytest" in content

    def test_pytest_ini_exists(self, project_root):
        """Test that pytest.ini exists."""
        pytest_ini = project_root / "pytest.ini"
        assert pytest_ini.exists(), "pytest.ini file is missing"
        assert pytest_ini.is_file(), "pytest.ini is not a file"

    def test_main_py_exists(self, project_root):
        """Test that main.py exists."""
        main_file = project_root / "main.py"
        assert main_file.exists(), "main.py file is missing"
        assert main_file.is_file(), "main.py is not a file"
        
        # Verify main.py has basic content
        content = main_file.read_text()
        assert "def main():" in content, "main.py missing main() function"
        assert 'if __name__ == "__main__":' in content, "main.py missing main guard"

    def test_pyproject_toml_exists(self, project_root):
        """Test that pyproject.toml exists and has proper structure."""
        pyproject_file = project_root / "pyproject.toml"
        assert pyproject_file.exists(), "pyproject.toml file is missing"
        assert pyproject_file.is_file(), "pyproject.toml is not a file"
        
        content = pyproject_file.read_text()
        assert 'name = "argos"' in content, "Project name not set in pyproject.toml"
        assert ">=3.11" in content, "Python version requirement not set correctly"

    def test_gitignore_exists(self, project_root):
        """Test that .gitignore exists."""
        gitignore_file = project_root / ".gitignore"
        assert gitignore_file.exists(), ".gitignore file is missing"
        assert gitignore_file.is_file(), ".gitignore is not a file"
        
        content = gitignore_file.read_text()
        assert "__pycache__/" in content, ".gitignore missing Python cache entries"
        assert ("*.pyc" in content or "*.py[cod]" in content), ".gitignore missing pyc entries"

    def test_folder_structure_integrity(self, project_root):
        """Test that all expected directories exist."""
        expected_dirs = [
            "core",
            "core/align",
            "core/inspection", 
            "core/evaluation",
            "core/analyzers",
            "core/providers",
            "ui",
            "ui/pages",
            "ui/dialogs",
            "ui/components",
            "ui/assets",
            "config",
            "tests",
            "tests/unit",
            "tests/integration",
            "tests/fixtures",
            "logs",
            "output",
            "docs"
        ]
        
        for expected_dir in expected_dirs:
            dir_path = project_root / expected_dir
            assert dir_path.exists(), f"Missing directory: {expected_dir}"
            assert dir_path.is_dir(), f"Path is not a directory: {expected_dir}"