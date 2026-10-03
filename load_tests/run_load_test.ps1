# PulseWatch Headless Load Test Runner
param (
    [string]$HostUrl = "http://localhost:8000",
    [int]$Users = 50,
    [int]$SpawnRate = 10,
    [string]$RunTime = "1m",
    [string]$ApiKey = ""
)

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "     PulseWatch Ingestion Load Test Suite    " -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "Target Host: $HostUrl"
Write-Host "Concurrency: $Users simulated clients"
Write-Host "Spawn Rate:  $SpawnRate users/sec"
Write-Host "Duration:    $RunTime"
Write-Host ""

if ($ApiKey) {
    $env:PULSEWATCH_API_KEY = $ApiKey
}

locust -f locustfile.py --host $HostUrl --headless -u $Users -r $SpawnRate --run-time $RunTime --csv=results_summary

Write-Host ""
Write-Host "Load test finished. Results written to results_summary_stats.csv" -ForegroundColor Green
