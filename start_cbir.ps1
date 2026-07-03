param(
    [int]$BackendPort = 8010,
    [int]$FrontendPort = 5173,
    [switch]$SkipEvaluateHealth
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"
$RuntimeDir = Join-Path $Root ".runtime"
$LogDir = Join-Path $RuntimeDir "logs"
$PidFile = Join-Path $RuntimeDir "cbir-dev-pids.json"
$BackendUrl = "http://127.0.0.1:$BackendPort"
$FrontendUrl = "http://localhost:$FrontendPort"

New-Item -ItemType Directory -Force -Path $RuntimeDir, $LogDir | Out-Null

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Stop-PortProcess {
    param([int]$Port)

    $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    $processIds = $connections | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($processId in $processIds) {
        if (-not $processId) {
            continue
        }
        $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if ($null -eq $process) {
            continue
        }
        Write-Host "Stopping process on port $Port`: $($process.ProcessName)($processId)"
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    }
}

function Stop-ProjectProcess {
    param(
        [string]$PathPart,
        [string[]]$Keywords
    )

    $escapedPath = [regex]::Escape($PathPart)
    $processes = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.ProcessId -ne $PID -and
            $_.CommandLine -and
            $_.CommandLine -match $escapedPath
        }

    foreach ($item in $processes) {
        $matched = $false
        foreach ($keyword in $Keywords) {
            if ($item.CommandLine -like "*$keyword*") {
                $matched = $true
                break
            }
        }
        if (-not $matched) {
            continue
        }
        Write-Host "Stopping project process: $($item.Name)($($item.ProcessId))"
        Stop-Process -Id $item.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

function Wait-HttpOk {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 60
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 3
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return $true
            }
        } catch {
            Start-Sleep -Milliseconds 800
            continue
        }
        Start-Sleep -Milliseconds 800
    }
    return $false
}

function Test-JsonEndpoint {
    param(
        [string]$Name,
        [string]$Url,
        [scriptblock]$Describe,
        [int]$TimeoutSeconds = 20
    )

    try {
        $data = Invoke-RestMethod -Uri $Url -TimeoutSec $TimeoutSeconds
        $detail = if ($Describe) { & $Describe $data } else { "OK" }
        [PSCustomObject]@{
            Name   = $Name
            Status = "OK"
            Detail = $detail
            Url    = $Url
        }
    } catch {
        [PSCustomObject]@{
            Name   = $Name
            Status = "FAIL"
            Detail = $_.Exception.Message
            Url    = $Url
        }
    }
}

Write-Step "Stop existing frontend/backend processes"
Stop-PortProcess -Port $BackendPort
Stop-PortProcess -Port $FrontendPort
Stop-ProjectProcess -PathPart $BackendDir -Keywords @(
    "uvicorn",
    "app.main:app",
    "scripts.download_file",
    "scripts.prepare_cifar_dataset",
    "scripts.train_cifar_cnn",
    "scripts.build_index",
    "scripts.run_evaluate"
)
Stop-ProjectProcess -PathPart $FrontendDir -Keywords @("vite", "npm.cmd run dev")
Start-Sleep -Seconds 1

Write-Step "Start backend"
$PythonExe = Join-Path $BackendDir ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    throw "Backend venv Python was not found: $PythonExe"
}
$BackendOut = Join-Path $LogDir "backend.out.log"
$BackendErr = Join-Path $LogDir "backend.err.log"
$BackendArgs = @(
    "-m", "uvicorn", "app.main:app",
    "--host", "127.0.0.1",
    "--port", "$BackendPort",
    "--reload"
)
$BackendProcess = Start-Process `
    -FilePath $PythonExe `
    -ArgumentList $BackendArgs `
    -WorkingDirectory $BackendDir `
    -WindowStyle Hidden `
    -RedirectStandardOutput $BackendOut `
    -RedirectStandardError $BackendErr `
    -PassThru
Write-Host "Backend PID: $($BackendProcess.Id)"

Write-Step "Start frontend"
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
    throw "npm.cmd was not found. Please install Node.js or make sure npm is in PATH."
}
$FrontendOut = Join-Path $LogDir "frontend.out.log"
$FrontendErr = Join-Path $LogDir "frontend.err.log"
$FrontendCommand = "set VITE_API_TARGET=$BackendUrl&& npm.cmd run dev -- --host 127.0.0.1 --port $FrontendPort"
$FrontendProcess = Start-Process `
    -FilePath "cmd.exe" `
    -ArgumentList @("/c", $FrontendCommand) `
    -WorkingDirectory $FrontendDir `
    -WindowStyle Hidden `
    -RedirectStandardOutput $FrontendOut `
    -RedirectStandardError $FrontendErr `
    -PassThru
Write-Host "Frontend PID: $($FrontendProcess.Id)"

@{
    backend_pid  = $BackendProcess.Id
    frontend_pid = $FrontendProcess.Id
    backend_url  = $BackendUrl
    frontend_url = $FrontendUrl
    started_at   = (Get-Date).ToString("s")
    logs         = @{
        backend_out  = $BackendOut
        backend_err  = $BackendErr
        frontend_out = $FrontendOut
        frontend_err = $FrontendErr
    }
} | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 $PidFile

Write-Step "Wait for services"
$BackendReady = Wait-HttpOk -Url "$BackendUrl/api/health" -TimeoutSeconds 90
$FrontendReady = Wait-HttpOk -Url "$FrontendUrl/pipeline" -TimeoutSeconds 90

$ImagesUrl = $BackendUrl + '/api/datasets/cifar10/images?page=1&size=1'
$HistogramUrl = $BackendUrl + '/api/histogram?dataset=cifar10&image_id=1&type=hsv'
$EvaluateUrl = $BackendUrl + '/api/evaluate?dataset=cifar10&feature=deep&metric=cosine&k=12&sample=1'

Write-Step "Backend API health checks"
$HealthResults = @()
$HealthResults += Test-JsonEndpoint -Name "Health" -Url "$BackendUrl/api/health" -Describe {
    param($data)
    "status=$($data.status); device=$($data.device.selected); gpu=$($data.device.cuda_device_name)"
}
$HealthResults += Test-JsonEndpoint -Name "OpenAPI" -Url "$BackendUrl/openapi.json" -Describe {
    param($data)
    "paths=$($data.paths.PSObject.Properties.Count)"
}
$HealthResults += Test-JsonEndpoint -Name "Datasets" -Url "$BackendUrl/api/datasets" -Describe {
    param($data)
    "datasets=$($data.Count)"
}
$HealthResults += Test-JsonEndpoint -Name "Gallery" -Url $ImagesUrl -Describe {
    param($data)
    "total=$($data.total)"
}
$HealthResults += Test-JsonEndpoint -Name "Categories" -Url "$BackendUrl/api/datasets/cifar10/categories" -Describe {
    param($data)
    "categories=$($data.Count)"
}
$HealthResults += Test-JsonEndpoint -Name "Histogram" -Url $HistogramUrl -Describe {
    param($data)
    "bins=$($data.bins.Count)"
}
$HealthResults += Test-JsonEndpoint -Name "PipelineTasks" -Url "$BackendUrl/api/pipeline/tasks" -Describe {
    param($data)
    "tasks=$($data.Count)"
}
if (-not $SkipEvaluateHealth) {
    $HealthResults += Test-JsonEndpoint -Name "Evaluate" -Url $EvaluateUrl -TimeoutSeconds 90 -Describe {
        param($data)
        "mAP=$([Math]::Round([double]$data.map, 4)); P@$($data.k)=$([Math]::Round([double]$data.p_at_k, 4))"
    }
}

$FrontendStatus = if ($FrontendReady) { "OK" } else { "FAIL" }
$BackendStatus = if ($BackendReady) { "OK" } else { "FAIL" }

Write-Host ""
Write-Host "Service status" -ForegroundColor Green
[PSCustomObject]@{
    Backend  = $BackendStatus
    Frontend = $FrontendStatus
    Logs     = $LogDir
} | Format-List

Write-Host "API health" -ForegroundColor Green
$HealthResults | Format-Table -AutoSize

Write-Host ""
Write-Host "Backend: $BackendUrl" -ForegroundColor Green
Write-Host "Frontend search: $FrontendUrl/search" -ForegroundColor Green
Write-Host "Pipeline: $FrontendUrl/pipeline" -ForegroundColor Green
Write-Host "API docs: $BackendUrl/docs" -ForegroundColor Green
Write-Host "Logs: $LogDir" -ForegroundColor Green
Write-Host "PID file: $PidFile" -ForegroundColor Green
