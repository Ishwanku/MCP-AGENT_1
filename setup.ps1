# MCP Document Merge Agent Setup Script

Write-Host ""
Write-Host "Setting up MCP Document Merge Agent"
Write-Host ""

# Check for Python installation
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
}
if (-not $pythonCmd) {
    Write-Host "Python not found. Please install Python 3.9 or higher."
    exit 1
}

Write-Host "Creating Python virtual environment '.venv'"
Start-Process -FilePath ($pythonCmd).Source -ArgumentList "-m venv .venv" -Wait -NoNewWindow

Write-Host ""
Write-Host "Activating virtual environment and installing dependencies"
Write-Host ""

$venvPythonPath = ".venv\Scripts\python.exe"
$venvPipPath = ".venv\Scripts\pip.exe"

# Upgrade pip in virtual environment
Start-Process -FilePath $venvPythonPath -ArgumentList "-m pip install --upgrade pip" -Wait -NoNewWindow

# Install the project with all optional dependencies
Start-Process -FilePath $venvPipPath -ArgumentList "install -e ." -Wait -NoNewWindow
# Continue even if exit code is non-zero, as installation might still succeed
Write-Host "Project installation attempted, proceeding with additional dependencies"

# Explicitly install individual optional dependencies to ensure they are available
Write-Host "Ensuring individual LLM provider dependencies are installed..."
Start-Process -FilePath $venvPipPath -ArgumentList "install google-ai-generativelanguage" -Wait -NoNewWindow
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to install google-ai-generativelanguage for Gemini support"
    Write-Host "Continuing setup, but Gemini functionality may not be available"
}

Write-Host ""
Write-Host "Starting MCP Document Merge Agent Server"
Write-Host ""

Start-Process -FilePath $venvPythonPath -ArgumentList "run.py" -Wait -NoNewWindow
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to start the server"
    exit $LASTEXITCODE
}

Write-Host "Setup complete. Server is running on http://0.0.0.0:8000 (or configured port)." 