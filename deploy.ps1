$ErrorActionPreference = "Stop"

Write-Host "Checking for NVIDIA GPU..." -ForegroundColor Cyan
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    Write-Host "NVIDIA GPU detected! Enabling GPU support..." -ForegroundColor Green
    docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
} else {
    Write-Host "No NVIDIA GPU found. Falling back to CPU..." -ForegroundColor Yellow
    docker compose up -d
}

if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne $null) {
    Write-Host "[Error] Failed to start docker containers." -ForegroundColor Red
    exit 1
}

# Wait and run health checks
Write-Host "`nWaiting 5 seconds for services to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

Write-Host "Running HTTP health check on Gateway..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/status" -UseBasicParsing -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "[Success] Gateway backend is ONLINE (HTTP 200)" -ForegroundColor Green
        Write-Host "Capabilities Status:" -ForegroundColor Cyan
        $response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 5 | Write-Host
    }
} catch {
    Write-Host "[Warning] Gateway status endpoint error: $($_.Exception.Message) (it might still be starting up)" -ForegroundColor Yellow
}

# Cloudflare Tunnel Logic
$TUNNEL_RUNNING = $false
$PUBLIC_API_URL = ""

Write-Host "`nInitializing Cloudflare Quick Tunnel..." -ForegroundColor Cyan

$cloudflaredPath = "cloudflared"
if (-not (Get-Command $cloudflaredPath -ErrorAction SilentlyContinue)) {
    if (Test-Path "C:\Program Files (x86)\cloudflared\cloudflared.exe") {
        $cloudflaredPath = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
    }
}

if ($cloudflaredPath -eq "cloudflared" -and -not (Get-Command $cloudflaredPath -ErrorAction SilentlyContinue)) {
    Write-Host "[Warning] cloudflared CLI is not installed. Download it to enable tunneling." -ForegroundColor Yellow
} else {
    # 1. Kill any existing cloudflared instances
    Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Seconds 1 # Đợi một chút để OS nhả file lock
    if (Test-Path "cloudflare_tunnel.log") {
        Remove-Item "cloudflare_tunnel.log" -Force -ErrorAction SilentlyContinue
    }

    # 2. Start Quick Tunnel in the background
    Write-Host "Starting fresh tunnel in background..." -ForegroundColor Yellow
    Start-Process -FilePath $cloudflaredPath -ArgumentList "tunnel --url http://localhost:8000" -RedirectStandardError "cloudflare_tunnel.log" -RedirectStandardOutput "cloudflare_tunnel_out.log" -WindowStyle Hidden

    # 3. Poll the log file to extract the dynamically generated URL
    Write-Host "Waiting for Cloudflare to assign your public URL..." -ForegroundColor Yellow
    for ($i = 1; $i -le 5; $i++) {
        Start-Sleep -Seconds 1
        if (Test-Path "cloudflare_tunnel.log") {
            $content = Get-Content "cloudflare_tunnel.log" -Raw
            if ($content -match "(https://[a-zA-Z0-9.-]+\.trycloudflare\.com)") {
                $PUBLIC_API_URL = $matches[1] + "/api"
                $TUNNEL_RUNNING = $true
                break
            }
        }
    }

    if ($TUNNEL_RUNNING) {
        Write-Host "[Success] Cloudflare Tunnel is active!" -ForegroundColor Green
        Write-Host "   - Public API URL:  $PUBLIC_API_URL" -ForegroundColor Green
    } else {
        Write-Host "[Error] Failed to retrieve public URL. Check cloudflare_tunnel.log for details." -ForegroundColor Red
    }
}

Write-Host "`n=======================================================" -ForegroundColor Green
Write-Host "Deployment finished successfully!" -ForegroundColor Green
Write-Host "   - Frontend UI: http://localhost:5173" -ForegroundColor Cyan
Write-Host "   - Gateway API: http://localhost:8000" -ForegroundColor Cyan
if ($TUNNEL_RUNNING) {
    Write-Host "   - Public API (Tunnel): $PUBLIC_API_URL" -ForegroundColor Green
    Write-Host "     -> Copy the link above and paste it into the 'API Connection' field in Vercel!"
}
Write-Host "   - Gateway Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "`nUseful commands:"
Write-Host "   - View docker logs:   docker compose logs -f" -ForegroundColor Yellow
Write-Host "   - View tunnel logs:   Get-Content cloudflare_tunnel.log -Wait" -ForegroundColor Yellow
Write-Host "   - Stop application:   docker compose down; Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process" -ForegroundColor Yellow
Write-Host "=======================================================" -ForegroundColor Green
