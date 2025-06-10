"""
MCP Document Merge Agent Server Entry Point

This script serves as the main entry point for starting the MCP Document Merge Agent server.
It configures the environment, installs necessary dependencies, and launches the FastAPI server
to handle document merging requests.

Key Features:
- Configures logging for detailed output during server operation.
- Checks and installs dependencies, including optional LLM providers for summarization.
- Starts the server on a specified port (default: 8000 or as configured).

Usage:
    Run this script with `python run.py` to start the server. Ensure that the virtual
    environment is activated and dependencies are installed (via setup.ps1 or manual installation).

Configuration:
    Environment variables and settings are loaded from a `.env` file or system environment.
    Key settings include DOCUMENT_AGENT_PORT for server port configuration.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path
from dotenv import load_dotenv
import logging
import uvicorn
from mcp.agents.document_merge_agent import app

# Load environment variables from .env file for configuration settings
load_dotenv()

# Configure logging to show detailed messages for debugging and monitoring
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def check_python_version():
    """Check if Python version is compatible with the MCP Agent.
    
    The function exits the script with an error code if the Python version is less than 3.9,
    as the MCP Agent requires features and libraries compatible with Python 3.9 or higher.
    """
    if sys.version_info < (3, 9):
        print("Error: Python 3.9 or higher is required")
        sys.exit(1)

def get_venv_path():
    """Get the path to the virtual environment directory.
    
    Returns:
        Path: The filesystem path where the virtual environment should be located.
    """
    return Path(".venv")

def create_venv():
    """Create a virtual environment if it doesn't already exist.
    
    This function sets up a new virtual environment in the .venv directory using the
    current Python executable. It also ensures that pip is installed and upgraded
    within the virtual environment for dependency management.
    """
    venv_path = get_venv_path()
    if not venv_path.exists():
        print("Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
        
        # Ensure pip is installed in the virtual environment for package installation
        python = get_venv_python()
        print("Ensuring pip is installed...")
        try:
            # First try to upgrade pip to the latest version
            subprocess.run([str(python), "-m", "ensurepip", "--upgrade"], check=True)
        except subprocess.CalledProcessError:
            # If upgrade fails, try a basic installation of pip
            subprocess.run([str(python), "-m", "ensurepip"], check=True)

def get_venv_python():
    """Get the path to the Python executable within the virtual environment.
    
    This function determines the correct path based on the operating system (Windows or Unix-like)
    to ensure compatibility across platforms.
    
    Returns:
        Path: Path to the Python executable in the virtual environment.
    """
    venv_path = get_venv_path()
    if platform.system() == "Windows":
        return venv_path / "Scripts" / "python.exe"
    return venv_path / "bin" / "python"

def install_dependencies():
    """Install required dependencies into the virtual environment.
    
    This function upgrades pip within the virtual environment and then installs
    the MCP Agent package and its dependencies using an editable installation,
    allowing for local development changes to be reflected immediately.
    """
    print("Installing dependencies...")
    python = get_venv_python()
    
    # First upgrade pip itself to ensure the latest version is used
    print("Upgrading pip...")
    subprocess.run([str(python), "-m", "pip", "install", "--upgrade", "pip"], check=True)
    
    # Then install the package in editable mode with all optional dependencies for development
    print("Installing MCP Document Merge Agent with all optional LLM providers...")
    result = subprocess.run([str(python), "-m", "pip", "install", "-e", ".[all]"], capture_output=True, text=True)
    if result.returncode != 0 or "WARNING: mcp-agent 0.1.0 does not provide the extra 'all'" in result.stderr:
        print("Warning detected or installation failed for 'all' extra. Falling back to individual dependency installation...")
        for dep in ["ollama", "openai", "google-ai-generativelanguage"]:
            print(f"Installing {dep}...")
            subprocess.run([str(python), "-m", "pip", "install", dep], check=False)
    else:
        print("Installation of MCP Agent with all extras completed.")

def start_agent():
    """Start the MCP Document Merge Agent server.
    
    This function launches the agent using the Python executable from the virtual environment,
    running the document_merge_agent module which hosts the FastAPI server on the specified port.
    """
    print("Starting MCP Document Merge Agent...")
    python = get_venv_python()
    uvicorn.run(app, host="0.0.0.0", port=8000)

def main():
    """Main function to orchestrate the setup and start the MCP Agent server.
    
    This function calls all necessary setup steps in order: checking Python version,
    creating a virtual environment, installing dependencies, and starting the agent.
    It includes error handling to provide feedback if any step fails.
    """
    try:
        print("Setting up MCP Document Merge Agent...")
        check_python_version()
        create_venv()
        install_dependencies()
        start_agent()
    except subprocess.CalledProcessError as e:
        # Handle errors from subprocess commands (e.g., failed installations)
        print(f"Error during setup: {e}")
        print("\nTroubleshooting steps:")
        print("1. Make sure you have Python 3.9 or higher installed")
        print("2. Try deleting the .venv folder and running the script again")
        print("3. Check if you have write permissions in the current directory")
        sys.exit(1)
    except Exception as e:
        # Handle any other unexpected errors during setup
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Entry point of the script to initiate the main setup and run process
    main()