param(
    [switch]$SkipTests,
    [switch]$KeepReports
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Backend  = Join-Path $RepoRoot "backend"
$Frontend = Join-Path $RepoRoot "frontend"

Set-Location $RepoRoot
$InitialRepositoryState = @(git status --porcelain=v1 --untracked-files=all)
if ($LASTEXITCODE -ne 0) {
    throw "Unable to capture the initial repository state."
}

$ToolVenv = Join-Path $env:TEMP "legacyguard-sast-venv"
$ToolPython = Join-Path $ToolVenv "Scripts\python.exe"

$BackendTestVenv = Join-Path $env:TEMP "legacyguard-backend-test-venv"
$BackendTestPython = Join-Path $BackendTestVenv "Scripts\python.exe"

$Semgrep = Join-Path $ToolVenv "Scripts\semgrep.exe"
$Bandit  = Join-Path $ToolVenv "Scripts\bandit.exe"
$DetectSecrets = Join-Path $ToolVenv "Scripts\detect-secrets.exe"
$SecretBaseline = Join-Path $RepoRoot "docs\security-secrets-baseline.json"
$SecretReviewed = Join-Path $RepoRoot "docs\security-secrets-reviewed.json"

$ExpectedToolVersions = [ordered]@{
    semgrep = "1.178.0"
    bandit = "1.9.4"
    "detect-secrets" = "1.5.0"
    "pip-audit" = "2.10.1"
}

$ReportRoot = Join-Path $env:TEMP (
    "legacyguard-security-gate-" +
    (Get-Date -Format "yyyyMMdd-HHmmss")
)

New-Item -ItemType Directory -Force $ReportRoot | Out-Null

$Failures = [System.Collections.Generic.List[string]]::new()

function Test-Python312Interpreter {
    param([string]$Executable)

    if (-not (Test-Path $Executable)) {
        return $false
    }

    $version = & $Executable -c "import sys; print('%s.%s' % sys.version_info[:2])" 2>$null
    return $LASTEXITCODE -eq 0 -and ($version | Select-Object -Last 1).Trim() -eq "3.12"
}

function Resolve-Python312 {
    $launcher = Get-Command py -CommandType Application -ErrorAction SilentlyContinue
    if ($null -ne $launcher) {
        $executable = & $launcher.Source -3.12 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            $candidate = ($executable | Select-Object -Last 1).Trim()
            if (Test-Python312Interpreter $candidate) {
                return $candidate
            }
        }
    }

    foreach ($commandName in @("python3.12", "python")) {
        $command = Get-Command $commandName -CommandType Application -ErrorAction SilentlyContinue
        if ($null -ne $command -and (Test-Python312Interpreter $command.Source)) {
            return $command.Source
        }
    }

    throw "Python 3.12 is required for the local security gate. Install Python 3.12 and ensure it is available through 'py -3.12', 'python3.12', or a Python 3.12 'python' executable."
}

function Assert-Python312Environment {
    param(
        [string]$PythonPath,
        [string]$EnvironmentName
    )

    if (-not (Test-Python312Interpreter $PythonPath)) {
        $version = & $PythonPath -c "import sys; print('%s.%s' % sys.version_info[:2])" 2>$null
        $foundVersion = if ($LASTEXITCODE -eq 0) { ($version | Select-Object -Last 1).Trim() } else { "unavailable" }
        throw "$EnvironmentName must use Python 3.12; found Python $foundVersion at $PythonPath. Remove the temporary environment and rerun the gate."
    }
}

function Invoke-GateStep {
    param(
        [string]$Name,
        [scriptblock]$Command
    )

    Write-Host ""
    Write-Host "============================================================"
    Write-Host " $Name"
    Write-Host "============================================================"

    try {
        & $Command

        if ($LASTEXITCODE -ne 0) {
            throw "Exit code $LASTEXITCODE"
        }

        Write-Host "[PASS] $Name"
    }
    catch {
        Write-Host "[FAIL] $Name"
        Write-Host $_
        $script:Failures.Add($Name)
    }
}

function Ensure-SastTools {
    if (-not (Test-Path $ToolPython)) {
        & $Python312 -m venv $ToolVenv
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to create the local SAST tool environment at $ToolVenv."
        }
    }
    Assert-Python312Environment $ToolPython "The local SAST tool environment"

    $installedVersions = @{}
    foreach ($package in $ExpectedToolVersions.Keys) {
        $version = & $ToolPython -c "import importlib.metadata as m; print(m.version('$package'))" 2>$null
        if ($LASTEXITCODE -eq 0) {
            $installedVersions[$package] = ($version | Select-Object -Last 1).Trim()
        }
    }

    $needsInstall = @(
        $ExpectedToolVersions.Keys | Where-Object {
            -not $installedVersions.ContainsKey($_) -or
            $installedVersions[$_] -ne $ExpectedToolVersions[$_]
        }
    )

    if ($needsInstall.Count -gt 0) {
        $requirements = @(
            $ExpectedToolVersions.Keys | ForEach-Object { "$_==$($ExpectedToolVersions[$_])" }
        )
        & $ToolPython -m pip install --disable-pip-version-check @requirements
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to install pinned local security tools: $($requirements -join ', ')"
        }
    }
}

function Ensure-BackendTestEnvironment {
    if (-not (Test-Path $BackendTestPython)) {
        & $Python312 -m venv $BackendTestVenv
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to create the backend test environment at $BackendTestVenv."
        }
    }
    Assert-Python312Environment $BackendTestPython "The backend test environment"

    & $BackendTestPython -m pip install --disable-pip-version-check -r (Join-Path $Backend "requirements-test.txt")
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to install the declared backend application and test requirements."
    }
}

function Get-RelativeRepositoryPath {
    param([string]$Path)

    $repositoryRoot = ((Resolve-Path $RepoRoot).Path).TrimEnd('\') + '\'
    $fullPath = (Resolve-Path $Path).Path
    if (-not $fullPath.StartsWith($repositoryRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Path is outside the repository root: $Path"
    }

    return $fullPath.Substring($repositoryRoot.Length).Replace('\', '/')
}

function Test-ReviewedBanditFinding {
    param($Finding)

    $relativePath = Get-RelativeRepositoryPath $Finding.filename
    $reviewed = @(
        @{ Rule = "B101"; Path = "backend/app/schemas/asset_beneficiaries.py"; Line = 43 }
        @{ Rule = "B101"; Path = "backend/app/schemas/asset_beneficiaries.py"; Line = 49 }
        @{ Rule = "B101"; Path = "backend/app/schemas/asset_beneficiaries.py"; Line = 57 }
        @{ Rule = "B101"; Path = "backend/app/schemas/asset_beneficiaries.py"; Line = 62 }
        @{ Rule = "B101"; Path = "backend/app/schemas/assets.py"; Line = 19 }
        @{ Rule = "B101"; Path = "backend/app/schemas/assets.py"; Line = 20 }
        @{ Rule = "B101"; Path = "backend/app/schemas/beneficiaries.py"; Line = 19 }
        @{ Rule = "B101"; Path = "backend/app/schemas/beneficiaries.py"; Line = 24 }
        @{ Rule = "B101"; Path = "backend/app/schemas/discovery.py"; Line = 110 }
        @{ Rule = "B101"; Path = "backend/app/schemas/discovery.py"; Line = 117 }
        @{ Rule = "B101"; Path = "backend/app/schemas/discovery.py"; Line = 122 }
        @{ Rule = "B101"; Path = "backend/app/schemas/discovery.py"; Line = 133 }
        @{ Rule = "B101"; Path = "backend/app/schemas/discovery.py"; Line = 140 }
        @{ Rule = "B101"; Path = "backend/app/schemas/discovery.py"; Line = 227 }
        @{ Rule = "B101"; Path = "backend/app/schemas/discovery.py"; Line = 234 }
        @{ Rule = "B101"; Path = "backend/app/schemas/documents.py"; Line = 45 }
        @{ Rule = "B101"; Path = "backend/app/schemas/documents.py"; Line = 51 }
        @{ Rule = "B101"; Path = "backend/app/schemas/legacy.py"; Line = 18 }
        @{ Rule = "B101"; Path = "backend/app/schemas/legacy.py"; Line = 19 }
        @{ Rule = "B608"; Path = "backend/alembic/versions/20260711_asset_beneficiary_link_model_preparation.py"; Line = 28 }
        @{ Rule = "B608"; Path = "backend/alembic/versions/20260826_encrypt_legacy_sensitive_fields.py"; Line = 109 }
        @{ Rule = "B105"; Path = "backend/app/api/auth.py"; Line = 25 }
        @{ Rule = "B105"; Path = "backend/app/api/auth.py"; Line = 109 }
        @{ Rule = "B107"; Path = "backend/app/security/auth.py"; Line = 40 }
        @{ Rule = "B106"; Path = "backend/app/security/auth.py"; Line = 58 }
        @{ Rule = "B105"; Path = "backend/app/services/discovery_privacy.py"; Line = 12 }
    )

    return $null -ne ($reviewed | Where-Object {
        $_.Rule -eq $Finding.test_id -and
        $_.Path -eq $relativePath -and
        $_.Line -eq $Finding.line_number
    })
}

function Test-ReviewedSemgrepFinding {
    param($Finding)

    return $Finding.check_id -eq "python.sqlalchemy.security.audit.avoid-sqlalchemy-text.avoid-sqlalchemy-text" -and
        $Finding.path.Replace('\', '/') -eq "backend/alembic/versions/20260826_encrypt_legacy_sensitive_fields.py" -and
        $Finding.start.line -eq 108
}

function Test-ReviewedSecretFinding {
    param(
        $Finding,
        [array]$ReviewedFindings
    )

    return $null -ne ($ReviewedFindings | Where-Object {
        $_.type -eq $Finding.type -and
        $_.path.Replace('\', '/') -eq $Finding.filename.Replace('\', '/') -and
        $_.hashed_secret -eq $Finding.hashed_secret -and
        $_.line -eq $Finding.line_number
    })
}

$Python312 = Resolve-Python312
Ensure-SastTools

if (-not $SkipTests) {
    Ensure-BackendTestEnvironment
}

Set-Location $RepoRoot

Write-Host ""
Write-Host "LegacyGuard Local Security Gate"
Write-Host "Repository: $RepoRoot"
Write-Host "Commit:     $(git rev-parse HEAD)"
Write-Host "Branch:     $(git branch --show-current)"
Write-Host "Reports:    $ReportRoot"

# ------------------------------------------------------------
# 1. Semgrep
# ------------------------------------------------------------

Invoke-GateStep "Semgrep SAST" {

    if (-not (Test-Path $Semgrep)) {
        throw "Semgrep is not installed in $ToolVenv"
    }

    & $Semgrep scan `
        --config p/python `
        --config p/typescript `
        --config p/javascript `
        --config p/react `
        --metrics off `
        --json `
        --output (Join-Path $ReportRoot "semgrep.json") `
        backend frontend scripts

    $semgrepExitCode = $LASTEXITCODE
    if ($semgrepExitCode -ne 0) {
        throw "Semgrep execution failed with exit code $semgrepExitCode."
    }

    $semgrepReport = Get-Content (Join-Path $ReportRoot "semgrep.json") -Raw | ConvertFrom-Json
    $unreviewed = @($semgrepReport.results | Where-Object { -not (Test-ReviewedSemgrepFinding $_) })
    foreach ($finding in @($semgrepReport.results | Where-Object { Test-ReviewedSemgrepFinding $_ })) {
        Write-Host "[REVIEWED] Semgrep $($finding.check_id) at $($finding.path):$($finding.start.line)"
    }
    foreach ($finding in $unreviewed) {
        Write-Host "[FINDING] Semgrep $($finding.check_id) at $($finding.path):$($finding.start.line)"
    }
    if ($unreviewed.Count -gt 0) {
        throw "Semgrep reported $($unreviewed.Count) unreviewed finding(s)."
    }
}

# ------------------------------------------------------------
# 2. Bandit
#
# Tests are excluded because pytest assertions intentionally generate
# B101 findings and test fixtures intentionally contain synthetic values.
# Production findings remain visible for review.
# ------------------------------------------------------------

Invoke-GateStep "Bandit Python Security" {

    if (-not (Test-Path $Bandit)) {
        throw "Bandit is not installed in $ToolVenv"
    }

    & $Bandit `
        -r (Join-Path $Backend "app") `
           (Join-Path $Backend "alembic") `
        -x (Join-Path $Backend "tests") `
        --exit-zero `
        -f json `
        -o (Join-Path $ReportRoot "bandit.json")

    $banditExitCode = $LASTEXITCODE
    if ($banditExitCode -ne 0) {
        throw "Bandit execution failed with exit code $banditExitCode."
    }

    $banditReport = Get-Content (Join-Path $ReportRoot "bandit.json") -Raw | ConvertFrom-Json
    $unreviewed = @($banditReport.results | Where-Object { -not (Test-ReviewedBanditFinding $_) })
    foreach ($finding in @($banditReport.results | Where-Object { Test-ReviewedBanditFinding $_ })) {
        $path = Get-RelativeRepositoryPath $finding.filename
        Write-Host "[REVIEWED] Bandit $($finding.test_id) at ${path}:$($finding.line_number)"
    }
    foreach ($finding in $unreviewed) {
        $path = Get-RelativeRepositoryPath $finding.filename
        Write-Host "[FINDING] Bandit $($finding.test_id) at ${path}:$($finding.line_number)"
    }
    if ($unreviewed.Count -gt 0) {
        throw "Bandit reported $($unreviewed.Count) unreviewed finding(s)."
    }
}

# ------------------------------------------------------------
# 3. Python dependency audit
# ------------------------------------------------------------

Invoke-GateStep "Python Dependency Audit" {

    Push-Location $Backend

    try {
        & $ToolPython -m pip_audit -r requirements.txt
        if ($LASTEXITCODE -ne 0) {
            throw "Runtime dependency audit failed."
        }

        & $ToolPython -m pip_audit -r requirements-test.txt
        if ($LASTEXITCODE -ne 0) {
            throw "Test dependency audit failed."
        }
    }
    finally {
        Pop-Location
    }
}

# ------------------------------------------------------------
# 4. Frontend dependency audit
# ------------------------------------------------------------

Invoke-GateStep "Frontend Dependency Installation" {

    Push-Location $Frontend

    try {
        npm ci
        $npmCiExitCode = $LASTEXITCODE
        if ($npmCiExitCode -ne 0) {
            throw "npm ci failed with exit code $npmCiExitCode."
        }
    }
    finally {
        Pop-Location
    }
}

if ($Failures.Contains("Frontend Dependency Installation")) {
    Write-Host "[FAIL] Frontend checks stopped because npm ci failed."
    exit 1
}

Invoke-GateStep "Frontend Dependency Audit" {

    Push-Location $Frontend

    try {
        npm audit --audit-level=moderate
    }
    finally {
        Pop-Location
    }
}

# ------------------------------------------------------------
# 5. Local secret scanning
#
# detect-secrets runs locally and writes only to the temporary report folder.
# The machine baseline is candidate inventory only. Findings are authorized
# only by exact entries in the separately reviewed disposition manifest.
# ------------------------------------------------------------

Invoke-GateStep "Local Secret Scan" {

    if (-not (Test-Path $DetectSecrets)) {
        throw "detect-secrets is not installed in $ToolVenv"
    }
    if (-not (Test-Path $SecretBaseline)) {
        throw "Secret baseline is missing: $SecretBaseline"
    }
    if (-not (Test-Path $SecretReviewed)) {
        throw "Reviewed secret manifest is missing: $SecretReviewed"
    }

    $secretReportPath = Join-Path $ReportRoot "detect-secrets.json"
    $secretScanOutput = & $DetectSecrets scan `
        --all-files `
        --force-use-all-plugins `
        --exclude-files '(^|[\\/])\.git([\\/]|$)|(^|[\\/])\.venv([\\/]|$)|(^|[\\/])__pycache__([\\/]|$)|(^|[\\/])\.pytest_cache([\\/]|$)|(^|[\\/])node_modules([\\/]|$)|(^|[\\/])docs[\\/]security-secrets-baseline\.json$|(^|[\\/])docs[\\/]security-secrets-reviewed\.json$'
    $secretScanExitCode = $LASTEXITCODE
    if ($secretScanExitCode -ne 0) {
        throw "detect-secrets execution failed with exit code $secretScanExitCode."
    }
    [System.IO.File]::WriteAllText($secretReportPath, ($secretScanOutput -join [Environment]::NewLine))

    $secretReport = Get-Content $secretReportPath -Raw | ConvertFrom-Json
    $secretBaseline = Get-Content $SecretBaseline -Raw | ConvertFrom-Json
    $secretReviewedManifest = Get-Content $SecretReviewed -Raw | ConvertFrom-Json
    if ($null -eq $secretBaseline.results) {
        throw "Secret baseline has no results inventory."
    }
    if ($null -eq $secretReviewedManifest.entries) {
        throw "Reviewed secret manifest has no entries."
    }

    $baselineFindings = [System.Collections.Generic.List[object]]::new()
    foreach ($property in $secretBaseline.results.PSObject.Properties) {
        foreach ($finding in $property.Value) {
            $baselineFindings.Add($finding)
        }
    }
    $reviewedFindings = [System.Collections.Generic.List[object]]::new()
    $reviewedKeys = [System.Collections.Generic.HashSet[string]]::new()
    $allowedDispositions = @(
        "test-fixture",
        "synthetic-placeholder",
        "example-configuration",
        "migration-identifier",
        "workflow-reference",
        "documentation-example",
        "smoke-test-fixture",
        "redaction-marker",
        "other-reviewed-non-secret"
    )
    foreach ($entry in @($secretReviewedManifest.entries)) {
        foreach ($field in @("type", "path", "hashed_secret", "line", "disposition", "rationale")) {
            if ($null -eq $entry.$field -or [string]::IsNullOrWhiteSpace([string]$entry.$field)) {
                throw "Reviewed secret manifest entry is missing required field '$field'."
            }
        }
        if ($entry.PSObject.Properties.Name -contains "secret" -or
            $entry.PSObject.Properties.Name -contains "secret_value" -or
            $entry.PSObject.Properties.Name -contains "value") {
            throw "Reviewed secret manifest contains a plaintext-secret field."
        }
        if ($entry.path -match '(^|[\\/])node_modules([\\/])|(^|[\\/])\.venv([\\/])|(^|[\\/])__pycache__([\\/])|(^|[\\/])\.pytest_cache([\\/])') {
            throw "Reviewed secret manifest contains a generated-artifact path."
        }
        if ($entry.disposition -notin $allowedDispositions) {
            throw "Reviewed secret manifest contains an unknown disposition."
        }
        $key = "$($entry.type)|$($entry.path.Replace('\', '/'))|$($entry.hashed_secret)|$($entry.line)"
        if (-not $reviewedKeys.Add($key)) {
            throw "Reviewed secret manifest contains a duplicate entry."
        }
        $baselineMatch = @($baselineFindings | Where-Object {
            $_.type -eq $entry.type -and
            $_.filename.Replace('\', '/') -eq $entry.path.Replace('\', '/') -and
            $_.hashed_secret -eq $entry.hashed_secret -and
            $_.line_number -eq $entry.line
        })
        if ($baselineMatch.Count -ne 1) {
            throw "Reviewed secret manifest entry does not exactly match the machine baseline candidate inventory."
        }
        $reviewedFindings.Add($entry)
    }
    foreach ($finding in $baselineFindings) {
        $reviewedMatches = @($reviewedFindings | Where-Object {
            $_.type -eq $finding.type -and
            $_.path.Replace('\', '/') -eq $finding.filename.Replace('\', '/') -and
            $_.hashed_secret -eq $finding.hashed_secret -and
            $_.line -eq $finding.line_number
        })
        if ($reviewedMatches.Count -ne 1) {
            throw "Machine baseline candidate does not have exactly one reviewed disposition."
        }
    }
    $unreviewed = @(
        $secretReport.results.PSObject.Properties | ForEach-Object {
            $_.Value | Where-Object {
                -not (Test-ReviewedSecretFinding $_ $reviewedFindings)
            }
        }
    )
    if ($unreviewed.Count -gt 0) {
        foreach ($finding in $unreviewed) {
            Write-Host "[FINDING] detect-secrets $($finding.type) at $($finding.filename):$($finding.line_number)"
        }
        throw "Local secret scan reported $($unreviewed.Count) unreviewed finding(s)."
    }
}

# ------------------------------------------------------------
# 6. Backend tests
# ------------------------------------------------------------

if (-not $SkipTests) {

    Invoke-GateStep "Backend Tests" {

        Push-Location $Backend

        try {
            & $BackendTestPython -m pytest
        }
        finally {
            Pop-Location
        }
    }

    # --------------------------------------------------------
    # 7. Frontend tests
    # --------------------------------------------------------

    Invoke-GateStep "Frontend Tests" {

        Push-Location $Frontend

        try {
            npm test
        }
        finally {
            Pop-Location
        }
    }

    # --------------------------------------------------------
    # 8. Frontend production build
    # --------------------------------------------------------

    Invoke-GateStep "Frontend Production Build" {

        Push-Location $Frontend

        try {
            npm run build
        }
        finally {
            Pop-Location
        }
    }
}
else {
    Write-Host ""
    Write-Host "[SKIP] Backend/frontend tests and build requested."
}

# ------------------------------------------------------------
# Git integrity
# ------------------------------------------------------------

Invoke-GateStep "Repository Integrity" {

    Set-Location $RepoRoot

    $FinalRepositoryState = @(git status --porcelain=v1 --untracked-files=all)
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to capture the final repository state."
    }

    $RepositoryStateDifferences = Compare-Object `
        -ReferenceObject $InitialRepositoryState `
        -DifferenceObject $FinalRepositoryState

    if ($null -ne $RepositoryStateDifferences) {
        Write-Host "Repository state changed during the security gate:"
        $RepositoryStateDifferences | ForEach-Object { Write-Host $_ }
        throw "Security gate changed the repository state."
    }

    Write-Host "[INTEGRITY] Repository state is identical to the pre-run snapshot."
}

# ------------------------------------------------------------
# Result
# ------------------------------------------------------------

Write-Host ""
Write-Host "============================================================"
Write-Host " LEGACYGUARD SECURITY GATE RESULT"
Write-Host "============================================================"

if ($Failures.Count -eq 0) {

    Write-Host "PASS"
    Write-Host "All enabled security-gate checks completed successfully."

    if ($KeepReports) {
        Write-Host "Reports retained for this validation run:"
        Write-Host $ReportRoot
    }
    else {
        Remove-Item -LiteralPath $ReportRoot -Recurse -Force
        Write-Host "Temporary reports removed after successful validation."
    }

    exit 0
}

Write-Host "FAIL"

foreach ($Failure in $Failures) {
    Write-Host " - $Failure"
}

Write-Host ""
Write-Host "Reports:"
Write-Host $ReportRoot

exit 1
