import os, sys, platform, subprocess
from pathlib import Path
from dotenv import load_dotenv
import logging
import uvicorn
from mcp.agents.document_merge_agent import app

# Load environment variables from .env file for configuration settings
load_dotenv()

# Configure logging to show detailed messages for debugging and monitoring
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

#checking Python Vesrion
def check_python_version():
    if sys.version_info < (3, 9):
        print("Error: Python 3.9 or higher is required")
        sys.exit(1)

#define the path of virtual environment
def get_venv_path():
    return Path(".venv")

#Creats the virtual environment if not available & install/upgrade the pip in .venv
def create_venv():
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

#Return the path of Python executable from .venv
def get_venv_python():
    venv_path = get_venv_path()
    if platform.system() == "Windows":
        return venv_path / "Scripts" / "python.exe"
    return venv_path / "bin" / "python"

#Install the required dependencies 
def install_dependencies():
    print("Installing dependencies...")
    python = get_venv_python()
    
    # First upgrade pip itself to ensure the latest version is used
    print("Upgrading pip...")
    subprocess.run([str(python), "-m", "pip", "install", "--upgrade", "pip"], check=True)
    
    # Then install the package in editable mode
    print("Installing MCP Document Merge Agent...")
    subprocess.run([str(python), "-m", "pip", "install", "-e", "."], capture_output=True, text=True)
    print("Installation of MCP Agent.")

#Run FastAPI through uvicorn
def start_agent():
    print("Starting MCP Document Merge Agent...")
    # Get the current project directory
    project_dir = Path(__file__).parent.parent.absolute()
    print(f"Watching directory: {project_dir}")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        reload=True,  # Enable auto-reload
        reload_dirs=[str(project_dir)],  # Watch the entire project directory
        reload_delay=1.0,  # Wait 1 second before reloading
        log_level="info"  # Show detailed logs
    )

#Orchestrate the setup chain if any error occurs return with proper error message
def main():
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