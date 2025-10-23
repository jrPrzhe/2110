# PowerShell script to upload Auto-Poster Bot to VDS
# Скрипт для загрузки бота на VDS с Windows

param(
    [Parameter(Mandatory=$true)]
    [string]$ServerIP,
    
    [Parameter(Mandatory=$false)]
    [string]$Username = "root",
    
    [Parameter(Mandatory=$false)]
    [string]$RemotePath = "/root/app-inst/"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Auto-Poster Bot - Upload to VDS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get current directory
$CurrentDir = Get-Location
$ProjectPath = Join-Path $CurrentDir "."

Write-Host "Project path: $ProjectPath" -ForegroundColor Yellow
Write-Host "Server: $Username@$ServerIP" -ForegroundColor Yellow
Write-Host "Remote path: $RemotePath" -ForegroundColor Yellow
Write-Host ""

# Check if SCP is available
try {
    scp 2>&1 | Out-Null
} catch {
    Write-Host "ERROR: SCP not found!" -ForegroundColor Red
    Write-Host "Install OpenSSH client or use WinSCP instead." -ForegroundColor Red
    exit 1
}

# Confirm upload
Write-Host "Files to upload:" -ForegroundColor Green
Write-Host "  - Python files (*.py)" -ForegroundColor Gray
Write-Host "  - Config files (*.txt, *.md, *.sh, *.service)" -ForegroundColor Gray
Write-Host "  - Directories: handlers/, services/, utils/" -ForegroundColor Gray
Write-Host ""
Write-Host "Files to EXCLUDE:" -ForegroundColor Yellow
Write-Host "  - venv/ (will be created on server)" -ForegroundColor Gray
Write-Host "  - __pycache__/ (temporary)" -ForegroundColor Gray
Write-Host "  - sessions/ (will be created on server)" -ForegroundColor Gray
Write-Host "  - uploads/ (will be created on server)" -ForegroundColor Gray
Write-Host ""

$confirm = Read-Host "Continue? (y/n)"
if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host "Upload cancelled." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Uploading project..." -ForegroundColor Cyan

# Create temporary directory for upload
$TempDir = New-Item -ItemType Directory -Force -Path "$env:TEMP\auto-poster-bot-upload"

# Copy files (excluding unwanted)
Write-Host "Preparing files..." -ForegroundColor Gray

# Copy Python files
Copy-Item -Path "$ProjectPath\*.py" -Destination $TempDir -Force
Copy-Item -Path "$ProjectPath\*.txt" -Destination $TempDir -Force
Copy-Item -Path "$ProjectPath\*.md" -Destination $TempDir -Force
Copy-Item -Path "$ProjectPath\*.sh" -Destination $TempDir -Force
Copy-Item -Path "$ProjectPath\*.service" -Destination $TempDir -Force
Copy-Item -Path "$ProjectPath\.gitignore" -Destination $TempDir -Force -ErrorAction SilentlyContinue
Copy-Item -Path "$ProjectPath\env.example" -Destination $TempDir -Force -ErrorAction SilentlyContinue

# Copy directories
Copy-Item -Path "$ProjectPath\handlers" -Destination $TempDir -Recurse -Force -Exclude "__pycache__"
Copy-Item -Path "$ProjectPath\services" -Destination $TempDir -Recurse -Force -Exclude "__pycache__"
Copy-Item -Path "$ProjectPath\utils" -Destination $TempDir -Recurse -Force -Exclude "__pycache__"

Write-Host "Files prepared in temp directory" -ForegroundColor Green

# Upload using SCP
Write-Host "Uploading to server..." -ForegroundColor Cyan
Write-Host "Command: scp -r $TempDir $Username@${ServerIP}:$RemotePath" -ForegroundColor Gray

scp -r "$TempDir\*" "$Username@${ServerIP}:$RemotePath/auto-poster-bot/"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Upload completed successfully!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Connect to server:" -ForegroundColor White
    Write-Host "   ssh $Username@$ServerIP" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. Navigate to project:" -ForegroundColor White
    Write-Host "   cd $RemotePath/auto-poster-bot" -ForegroundColor Gray
    Write-Host ""
    Write-Host "3. Run deployment script:" -ForegroundColor White
    Write-Host "   chmod +x deploy.sh" -ForegroundColor Gray
    Write-Host "   ./deploy.sh" -ForegroundColor Gray
    Write-Host ""
    Write-Host "4. Configure .env file:" -ForegroundColor White
    Write-Host "   nano .env" -ForegroundColor Gray
    Write-Host ""
    Write-Host "5. Start the bot:" -ForegroundColor White
    Write-Host "   systemctl start auto-poster-bot" -ForegroundColor Gray
    Write-Host ""
    Write-Host "See DEPLOYMENT.md for detailed instructions." -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "ERROR: Upload failed!" -ForegroundColor Red
    Write-Host "Check your connection and credentials." -ForegroundColor Red
    Write-Host ""
    Write-Host "Alternative: Use WinSCP (https://winscp.net/)" -ForegroundColor Yellow
}

# Cleanup
Remove-Item -Path $TempDir -Recurse -Force
Write-Host ""
Write-Host "Temporary files cleaned up." -ForegroundColor Gray


