# Convert Markdown to Word Document
Write-Host "Converting PROJECT_COMPLETE_EXPLANATION.md to Word document..." -ForegroundColor Cyan

try {
    # Create Word application object
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    
    # Create new document
    $doc = $word.Documents.Add()
    
    # Read markdown file
    $content = Get-Content "PROJECT_COMPLETE_EXPLANATION.md" -Raw
    
    # Add content to document
    $selection = $word.Selection
    $selection.TypeText($content)
    
    # Format the document
    Write-Host "Formatting document..." -ForegroundColor Yellow
    
    # Set font
    $doc.Content.Font.Name = "Calibri"
    $doc.Content.Font.Size = 11
    
    # Format headings (lines starting with #)
    $paragraphs = $doc.Paragraphs
    foreach ($para in $paragraphs) {
        $text = $para.Range.Text
        
        # Main heading (# )
        if ($text -match "^# [^#]") {
            $para.Range.Font.Size = 24
            $para.Range.Font.Bold = $true
            $para.Range.Font.Color = 0x0000FF  # Blue
            $para.SpaceAfter = 12
        }
        # Sub heading (## )
        elseif ($text -match "^## ") {
            $para.Range.Font.Size = 18
            $para.Range.Font.Bold = $true
            $para.Range.Font.Color = 0x000080  # Dark Blue
            $para.SpaceAfter = 10
        }
        # Sub-sub heading (### )
        elseif ($text -match "^### ") {
            $para.Range.Font.Size = 14
            $para.Range.Font.Bold = $true
            $para.Range.Font.Color = 0x404040  # Dark Gray
            $para.SpaceAfter = 8
        }
        # Sub-sub-sub heading (#### )
        elseif ($text -match "^#### ") {
            $para.Range.Font.Size = 12
            $para.Range.Font.Bold = $true
            $para.SpaceAfter = 6
        }
    }
    
    # Save document
    $outputPath = Join-Path (Get-Location) "PROJECT_COMPLETE_EXPLANATION.docx"
    $doc.SaveAs([ref]$outputPath, [ref]16)  # 16 = wdFormatDocumentDefault
    
    Write-Host "✅ Document saved successfully!" -ForegroundColor Green
    Write-Host "Location: $outputPath" -ForegroundColor Cyan
    
    # Close document and Word
    $doc.Close()
    $word.Quit()
    
    # Release COM objects
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($doc) | Out-Null
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($word) | Out-Null
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
    
    Write-Host "`n✅ Conversion complete!" -ForegroundColor Green
    Write-Host "You can now open: PROJECT_COMPLETE_EXPLANATION.docx" -ForegroundColor White
    
    # Ask if user wants to open it
    $open = Read-Host "`nDo you want to open the document now? (Y/N)"
    if ($open -eq "Y" -or $open -eq "y") {
        Start-Process $outputPath
    }
    
} catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
    Write-Host "`nAlternative method: Opening in Word directly..." -ForegroundColor Yellow
    
    # Try alternative method - open markdown in Word
    try {
        $mdPath = Join-Path (Get-Location) "PROJECT_COMPLETE_EXPLANATION.md"
        Start-Process "winword.exe" -ArgumentList $mdPath
        Write-Host "✅ Opened in Word. You can save it as .docx from Word." -ForegroundColor Green
    } catch {
        Write-Host "❌ Could not open Word. Please open the file manually." -ForegroundColor Red
    }
}
