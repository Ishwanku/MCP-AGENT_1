Write-Host ""
Write-Host "Setting up MCP Document Merge Agent"
Write-Host ""

# Check Python installation
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Python is not installed. Please install Python 3.8 or later."
    exit 1
}

# Extract version number and check if it's 3.8 or later
$versionMatch = $pythonVersion -match "Python (\d+\.\d+)"
if ($versionMatch) {
    $version = [version]$Matches[1]
    if ($version.Major -lt 3 -or ($version.Major -eq 3 -and $version.Minor -lt 8)) {
        Write-Error "Python 3.8 or later is required. Current version: $version"
        exit 1
    }
}

# Check and update pip version
Write-Host "Checking pip version..."
$pipVersion = python -m pip --version 2>&1
$currentPipVersion = $pipVersion -match "pip (\d+\.\d+\.\d+)"
if ($currentPipVersion) {
    $currentVersion = [version]$Matches[1]
    $latestVersion = [version]"25.1.1"  # Latest stable version
    
    if ($currentVersion -lt $latestVersion) {
        Write-Host "Updating pip from $currentVersion to $latestVersion..."
        python -m pip install --upgrade pip
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Failed to update pip. Continuing with current version..."
        } else {
            Write-Host "Pip updated successfully."
        }
    } else {
        Write-Host "Pip is up to date (version $currentVersion)."
    }
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
    & python -m venv .venv
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