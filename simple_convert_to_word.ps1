# Simple Word Document Converter
Write-Host "Creating Word document from markdown..." -ForegroundColor Cyan

try {
    # Create Word application
    $word = New-Object -ComObject Word.Application
    $word.Visible = $true  # Make visible so user can see progress
    
    # Open the markdown file
    $mdPath = Join-Path (Get-Location) "PROJECT_COMPLETE_EXPLANATION.md"
    $doc = $word.Documents.Open($mdPath)
    
    Write-Host "✅ Document opened in Word" -ForegroundColor Green
    Write-Host "`nNow in Word:" -ForegroundColor Yellow
    Write-Host "1. The document is open" -ForegroundColor White
    Write-Host "2. Go to File > Save As" -ForegroundColor White
    Write-Host "3. Choose 'Word Document (*.docx)' as the format" -ForegroundColor White
    Write-Host "4. Click Save" -ForegroundColor White
    Write-Host "`nOr simply press Ctrl+S and choose .docx format" -ForegroundColor Cyan
    
} catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
    Write-Host "`nTrying alternative method..." -ForegroundColor Yellow
    
    # Alternative: Just open with Word
    $mdPath = Join-Path (Get-Location) "PROJECT_COMPLETE_EXPLANATION.md"
    Start-Process "winword.exe" -ArgumentList "`"$mdPath`""
    
    Write-Host "✅ Opened in Word" -ForegroundColor Green
    Write-Host "Save as .docx from Word (File > Save As)" -ForegroundColor Cyan
}
