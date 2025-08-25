param([string]$ApiUrl = "http://127.0.0.1:8080")
Write-Host "Healthz:"
irm "$ApiUrl/healthz" | ConvertTo-Json -Depth 5
Write-Host "`nPredict:"
$body = @{ features = @(0.1,0.2,0.3,0.4,0.5); threshold = 0.5 } | ConvertTo-Json -Compress
irm -Method Post -Uri "$ApiUrl/predict" -ContentType 'application/json' -Body $body | ConvertTo-Json -Depth 5
Write-Host "`nMetrics (first 10 lines):"
$metrics = (iwr "$ApiUrl/metrics").Content -split "`n"
$metrics[0..([Math]::Min(9, $metrics.Length-1))] -join "`n"
