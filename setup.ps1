Write-Host ""
Write-Host "Setting up MCP Document Merge Agent"
Write-Host ""

# Check for Python installation
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
}
if (-not $pythonCmd) {
    Write-Host "Python is not installed. Please install Python 3.8 or later."
    exit 1
}

# Check if virtual environment exists
$venvPath = ".venv"
$venvPythonPath = if ($IsWindows) {
    "$venvPath\Scripts\python.exe"
} else {
    "$venvPath/bin/python"
}

if (Test-Path $venvPythonPath) {
    Write-Host "Using existing virtual environment..."
    # Activate existing virtual environment
    if ($IsWindows) {
        .\.venv\Scripts\Activate.ps1
    } else {
        . ./.venv/bin/Activate.ps1
    }
} else {
    Write-Host "Creating new virtual environment..."
    # Create new virtual environment
    & $pythonCmd -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to create virtual environment"
        exit 1
    }
    
    # Activate new virtual environment
    if ($IsWindows) {
        .\.venv\Scripts\Activate.ps1
    } else {
        . ./.venv/bin/Activate.ps1
    }
}

# Install dependencies
Write-Host "Installing Python dependencies..."
& python -m pip install -e .
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to install Python dependencies"
    exit 1
}

if (-not (Test-Path ".env")) {
    Write-Host "`n⚠️  .env file not found. Please create it before running the application."
    exit 1
}

# Start the application
Write-Host "Starting the application..."
& python -m uvicorn src.run:app --reload --reload-dir .

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to start the application"
    exit 1
}

Write-Host "Setup complete. Server is running on http://0.0.0.0:8000 (or configured port)." 