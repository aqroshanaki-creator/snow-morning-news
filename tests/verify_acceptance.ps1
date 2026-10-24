# Acceptance Verification Script (PowerShell)
$ErrorActionPreference = "Stop"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " Snow Morning News - Acceptance Test" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$configPath = Join-Path $projectRoot "scripts\config.json"
$dataPath = Join-Path $projectRoot "web\data.json"
$htmlPath = Join-Path $projectRoot "web\index.html"
$cssPath = Join-Path $projectRoot "web\style.css"
$jsPath = Join-Path $projectRoot "web\app.js"
$manifestPath = Join-Path $projectRoot "web\manifest.json"
$swPath = Join-Path $projectRoot "web\sw.js"
$workflowPath = Join-Path $projectRoot ".github\workflows\update_news.yml"
$testDataPath = Join-Path $scriptDir "test_data.json"

$passed = 0
$failed = 0

function Assert-Condition($condition, $message) {
    if ($condition) {
        Write-Host "  [PASS] $message" -ForegroundColor Green
        $script:passed++
    } else {
        Write-Host "  [FAIL] $message" -ForegroundColor Red
        $script:failed++
    }
}

# --- Test 1: Check Required Files ---
Write-Host "`n1. File Structure Check..." -ForegroundColor Yellow
Assert-Condition (Test-Path $configPath) "config.json exists"
Assert-Condition (Test-Path $dataPath) "web/data.json exists"
Assert-Condition (Test-Path $htmlPath) "web/index.html exists"
Assert-Condition (Test-Path $cssPath) "web/style.css exists"
Assert-Condition (Test-Path $jsPath) "web/app.js exists"
Assert-Condition (Test-Path $manifestPath) "web/manifest.json exists"
Assert-Condition (Test-Path $swPath) "web/sw.js exists"
Assert-Condition (Test-Path $workflowPath) ".github/workflows/update_news.yml exists"

# --- Test 2: NG Word and Domain Filter Verification ---
Write-Host "`n2. NG Filtering Logic Verification..." -ForegroundColor Yellow
$configRaw = [System.IO.File]::ReadAllText($configPath, [System.Text.Encoding]::UTF8)
$config = $configRaw | ConvertFrom-Json
$ngKeywords = $config.filtering.ng_keywords
$ngDomains = $config.filtering.ng_domains

$testDataRaw = [System.IO.File]::ReadAllText($testDataPath, [System.Text.Encoding]::UTF8)
$testData = $testDataRaw | ConvertFrom-Json

function Test-IsNgArticle($title, $link) {
    foreach ($domain in $ngDomains) {
        if ($link.ToLower().Contains($domain.ToLower())) {
            return $true
        }
    }
    foreach ($kw in $ngKeywords) {
        if ($title.ToLower().Contains($kw.ToLower())) {
            return $true
        }
    }
    return $false
}

# Positive article test
$posArticle = $testData.positive_article
Assert-Condition (!(Test-IsNgArticle $posArticle.title $posArticle.link)) "Positive article passes cleanly"

# NG article tests
foreach ($ngArticle in $testData.ng_articles) {
    Assert-Condition (Test-IsNgArticle $ngArticle.title $ngArticle.link) "NG article properly rejected"
}

# NG domain test
$ngDomainArt = $testData.ng_domain_article
Assert-Condition (Test-IsNgArticle $ngDomainArt.title $ngDomainArt.link) "NG domain properly rejected"

# --- Test 3: Schema and Fallback Integrity ---
Write-Host "`n3. Schema and Fallback Integrity..." -ForegroundColor Yellow
$dataRaw = [System.IO.File]::ReadAllText($dataPath, [System.Text.Encoding]::UTF8)
$data = $dataRaw | ConvertFrom-Json

Assert-Condition ($data.updated_at -ne $null) "updated_at field exists"
Assert-Condition ($data.daily_quote -ne $null) "daily_quote exists"
Assert-Condition ($data.sakuma_news.Count -gt 0) "sakuma_news has articles"
Assert-Condition ($data.snowman_news.Count -gt 0) "snowman_news has articles"

$firstItem = $data.sakuma_news[0]
Assert-Condition ($firstItem.title -ne $null -and $firstItem.summary -ne $null -and $firstItem.link -ne $null) "Article card has title, summary, link"

# --- Test 4: Cost and Free Tier Configuration ---
Write-Host "`n4. Free-tier Configuration Verification..." -ForegroundColor Yellow
$modelName = $config.gemini_settings.model
Assert-Condition ($modelName.Contains("flash")) "Free-tier Flash model configured"

$workflowRaw = [System.IO.File]::ReadAllText($workflowPath, [System.Text.Encoding]::UTF8)
Assert-Condition ($workflowRaw.Contains("GEMINI_API_KEY")) "API key read from GitHub Secrets"
Assert-Condition ($workflowRaw.Contains("0 21 * * *")) "Cron scheduled at 06:00 JST (21:00 UTC)"

# --- Final Results ---
Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host " Results: $passed Passed / $failed Failed" -ForegroundColor $(if ($failed -eq 0) { "Green" } else { "Red" })
Write-Host "==================================================" -ForegroundColor Cyan

if ($failed -ne 0) {
    exit 1
}

