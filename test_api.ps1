# Bloomy API Test Script for PowerShell

$BaseUrl = "http://localhost:5000"

Write-Host "╔════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  🌿 Bloomy API Tester (PowerShell)     ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Green

# Test 1: Health Check
Write-Host "`n1️⃣  Testing Health Check..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$BaseUrl/api/health" -Method GET
    Write-Host "Status: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "Response: $($response.Content)" -ForegroundColor Cyan
} catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
}

# Test 2: API Docs
Write-Host "`n2️⃣  Testing API Documentation..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$BaseUrl/api/docs" -Method GET
    $json = $response.Content | ConvertFrom-Json
    Write-Host "Status: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "API Version: $($json.version)" -ForegroundColor Cyan
    Write-Host "Endpoints available: $($json.endpoints.PSObject.Properties.Count)" -ForegroundColor Cyan
} catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
}

# Test 3: Register User
Write-Host "`n3️⃣  Testing User Registration..." -ForegroundColor Yellow
try {
    $body = @{
        email = "test@example.com"
        password = "testpassword123"
        display_name = "Test User"
    } | ConvertTo-Json

    $response = Invoke-WebRequest -Uri "$BaseUrl/api/auth/register" `
        -Method POST `
        -ContentType "application/json" `
        -Body $body

    Write-Host "Status: $($response.StatusCode)" -ForegroundColor Green
    $result = $response.Content | ConvertFrom-Json
    Write-Host "Response:" -ForegroundColor Cyan
    $result | ConvertTo-Json | Write-Host

    if ($response.StatusCode -eq 201) {
        Write-Host "`n✅ User created successfully!" -ForegroundColor Green
        Write-Host "UID: $($result.uid)" -ForegroundColor Cyan
    }
} catch {
    Write-Host "Status: $($_.Exception.Response.StatusCode.Value)" -ForegroundColor Yellow
    try {
        $errorContent = $_.Exception.Response.Content.ReadAsStream()
        $reader = [System.IO.StreamReader]::new($errorContent)
        $errorBody = $reader.ReadToEnd()
        Write-Host "Error: $errorBody" -ForegroundColor Red
    } catch {
        Write-Host "Error: $_" -ForegroundColor Red
    }
}

Write-Host "`n" -ForegroundColor White
Write-Host "════════════════════════════════════════" -ForegroundColor Green
Write-Host "✅ Tests complete!" -ForegroundColor Green
Write-Host "════════════════════════════════════════" -ForegroundColor Green
