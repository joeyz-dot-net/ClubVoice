# Test Flask startup with a longer timeout
$input_data = @"
27
26
"@

# Start the process and keep it running for 10 seconds
$process = Start-Process python -ArgumentList "run.py" -InputObject $input_data -PassThru -WindowStyle Normal

# Wait 10 seconds
Start-Sleep -Seconds 10

# Kill the process
Stop-Process -InputObject $process -Force -ErrorAction SilentlyContinue

Write-Host "Flask startup test completed"
