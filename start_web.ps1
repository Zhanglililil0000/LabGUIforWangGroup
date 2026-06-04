# SFG/SRS Web GUI one-click launcher
param($Port = 8081)

Write-Host ""
Write-Host "SFG/SRS Web GUI Control Panel" -ForegroundColor Cyan
Write-Host "URL: http://localhost:$Port" -ForegroundColor Yellow
Write-Host ""

Start-Process "http://localhost:$Port"
python -m uvicorn web.app:app --host 0.0.0.0 --port $Port
pause
