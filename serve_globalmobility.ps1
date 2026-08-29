$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Python environment not found. Follow the README setup steps first."
}

Write-Host "Starting the private GlobalMobility EDU service..."
$backendProcess = Start-Process `
    -FilePath $pythonPath `
    -ArgumentList "serve_backend.py" `
    -WorkingDirectory $projectRoot `
    -WindowStyle Hidden `
    -PassThru

try {
    $backendReady = $false

    for ($attempt = 1; $attempt -le 180; $attempt++) {
        if ($backendProcess.HasExited) {
            throw "The policy engine stopped during startup."
        }

        try {
            $health = Invoke-RestMethod `
                -Uri "http://127.0.0.1:8000/health" `
                -TimeoutSec 2

            if ($health.status -eq "ready") {
                $backendReady = $true
                break
            }
        }
        catch {
            # Model initialization can take several minutes on first launch.
        }

        if ($attempt % 5 -eq 0) {
            Write-Host "Still loading the local models..."
        }
        Start-Sleep -Seconds 2
    }

    if (-not $backendReady) {
        throw "The policy engine did not become ready within six minutes."
    }

    Write-Host "Policy engine ready. Opening http://localhost:8501"
    Write-Host "Press Ctrl+C to stop both services."

    & $pythonPath -m streamlit run app.py `
        --server.address 127.0.0.1 `
        --server.port 8501 `
        --browser.gatherUsageStats false
}
finally {
    if ($null -ne $backendProcess -and -not $backendProcess.HasExited) {
        Stop-Process -Id $backendProcess.Id
    }
}
