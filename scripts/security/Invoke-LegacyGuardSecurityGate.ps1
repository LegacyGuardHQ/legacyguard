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
        if ($_.ScriptStackTrace) {
            Write-Host $_.ScriptStackTrace
        }
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

$ReviewedBanditFindings = @(
    @{ Rule = "B101"; Path = "backend/app/schemas/asset_beneficiaries.py"; Fingerprint = "ab7822b1-3b23c8da-86f9b1f2-e3ade489-fe94cf68-b6068214-2d04d793-229b2c10" }
    @{ Rule = "B101"; Path = "backend/app/schemas/asset_beneficiaries.py"; Fingerprint = "d59bca56-5e534def-1ce9737d-12d6622a-f8e4d0dd-2a53504f-0136c460-810e1d4d" }
    @{ Rule = "B101"; Path = "backend/app/schemas/asset_beneficiaries.py"; Fingerprint = "d97f7275-d0edd2bf-62b8ee5d-99fc4dd6-d3ee00d4-0078a424-682dacc7-88c7eee5" }
    @{ Rule = "B101"; Path = "backend/app/schemas/asset_beneficiaries.py"; Fingerprint = "f8e62258-752184a5-ebf8356b-8a6955ae-3d3875a9-a4d38244-7d493105-4bb3d4be" }
    @{ Rule = "B101"; Path = "backend/app/schemas/assets.py"; Fingerprint = "ac4a1ad1-3dfdcc21-4b978461-69deddd9-e4c0bc0a-b9a4f876-d33f7784-a5217ec9" }
    @{ Rule = "B101"; Path = "backend/app/schemas/assets.py"; Fingerprint = "7c45c0e1-f5c50c68-5a5f87a6-94896a67-b4a52ace-8861898a-d26c2771-3684cfe1" }
    @{ Rule = "B101"; Path = "backend/app/schemas/beneficiaries.py"; Fingerprint = "4dd8ea36-c1720747-dfd40aaa-19bbfa49-4fec81df-62952c0c-92f79b7b-cc6cf3e1" }
    @{ Rule = "B101"; Path = "backend/app/schemas/beneficiaries.py"; Fingerprint = "2d2766bc-f1bfa72c-9a67152e-b099c148-926795e0-40b5b122-4df74cd8-12f4a3d3" }
    @{ Rule = "B101"; Path = "backend/app/schemas/discovery.py"; Fingerprint = "bf631780-1b0600c5-8f6b892e-75cb985e-4acd6a24-8305ded7-7dd50f63-ba949032" }
    @{ Rule = "B101"; Path = "backend/app/schemas/discovery.py"; Fingerprint = "4d14babb-2a57d2cb-fa6aea98-2444ad4d-1379385d-0b093a2f-07edc115-c67e03a5" }
    @{ Rule = "B101"; Path = "backend/app/schemas/discovery.py"; Fingerprint = "7a859bbd-f5880126-3448a22d-120c21f8-175b7699-f95d890b-94839836-e934cada" }
    @{ Rule = "B101"; Path = "backend/app/schemas/discovery.py"; Fingerprint = "c83f2b28-fc1ca7dd-314232d2-493733f2-ec38c4d1-29bfdc3c-928f48c6-f64bd067" }
    @{ Rule = "B101"; Path = "backend/app/schemas/discovery.py"; Fingerprint = "9a6e92fd-6394d76e-86d90139-dcd35f93-3af00702-65383926-c587f63f-b6ec5e30" }
    @{ Rule = "B101"; Path = "backend/app/schemas/discovery.py"; Fingerprint = "8ab30700-f00d942b-23f9af2f-d402777b-5b634a41-3332a537-46a6b624-5ccb7f6e" }
    @{ Rule = "B101"; Path = "backend/app/schemas/discovery.py"; Fingerprint = "acf10b90-200a6c68-e06d4f7d-0a647ae9-95dd10bc-e96f7164-175fa489-458c9f25" }
    @{ Rule = "B101"; Path = "backend/app/schemas/documents.py"; Fingerprint = "37b4939a-e8c246b9-85da3f1e-12ccc53e-efc5786e-44b7d0bd-c488d48c-7ee79163" }
    @{ Rule = "B101"; Path = "backend/app/schemas/documents.py"; Fingerprint = "6363ae19-719dc6eb-dc1d29b2-df5bd18b-321758c8-aae82012-2786ce15-12391b15" }
    @{ Rule = "B101"; Path = "backend/app/schemas/legacy.py"; Fingerprint = "ac4a1ad1-3dfdcc21-4b978461-69deddd9-e4c0bc0a-b9a4f876-d33f7784-a5217ec9" }
    @{ Rule = "B101"; Path = "backend/app/schemas/legacy.py"; Fingerprint = "6698fc08-03c357e4-3dda9d38-bb0a7c99-f4be8dab-50597ff2-7cfdb293-2ed80e84" }
    @{ Rule = "B608"; Path = "backend/alembic/versions/20260711_asset_beneficiary_link_model_preparation.py"; Fingerprint = "2152da2d-25b68596-b3e00277-cfaecb23-7da247cb-57f992cd-f3d48a94-c6720c58" }
    @{ Rule = "B608"; Path = "backend/alembic/versions/20260826_encrypt_legacy_sensitive_fields.py"; Fingerprint = "419f0fe6-686aae2d-6b534671-59ef6354-340ff378-ea90fbf7-0f1b385f-54295010" }
    @{ Rule = "B105"; Path = "backend/app/api/auth.py"; Fingerprint = "7dff91c4-53884f91-2f46e0d3-619e7f63-e86ee87e-c7c053cd-18793e1b-fe9ff96d" }
    @{ Rule = "B105"; Path = "backend/app/api/auth.py"; Fingerprint = "551f8dec-ece3f640-a779aa33-2acc3217-ed9b1d49-25c67277-828f928f-edac3bc7" }
    @{ Rule = "B107"; Path = "backend/app/security/auth.py"; Fingerprint = "ab9a5c92-a628959b-57c23446-7d494b59-8c307009-bc781576-488df822-6a96f998" }
    @{ Rule = "B106"; Path = "backend/app/security/auth.py"; Fingerprint = "08771bb5-6c1f6c0f-d3062a7c-ea2f6e36-5ce105d4-edc266af-8943280a-533d24d6" }
    @{ Rule = "B105"; Path = "backend/app/services/discovery_privacy.py"; Fingerprint = "23bef051-e7d00134-96d73ab2-a46e5bfe-a4fc0660-82a3bcc6-14a6e883-bacb288c" }
)

$ReviewedSemgrepFindings = @(
    @{ Rule = "python.sqlalchemy.security.audit.avoid-sqlalchemy-text.avoid-sqlalchemy-text"; Path = "backend/alembic/versions/20260826_encrypt_legacy_sensitive_fields.py"; Fingerprint = "419f0fe6-686aae2d-6b534671-59ef6354-340ff378-ea90fbf7-0f1b385f-54295010" }
)

function Assert-ReviewedSastManifest {
    param(
        [array]$Entries,
        [string]$Scanner
    )

    $seen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::Ordinal)
    foreach ($entry in $Entries) {
        if ([string]::IsNullOrWhiteSpace([string]$entry.Rule) -or
            [string]::IsNullOrWhiteSpace([string]$entry.Path) -or
            $entry.Fingerprint -notmatch '^[0-9a-f]{8}(-[0-9a-f]{8}){7}$') {
            throw "$Scanner reviewed SAST entry is missing a valid rule, path, or SHA-256 fingerprint."
        }
        $normalizedFingerprint = $entry.Fingerprint -replace '-', ''
        $key = "$($entry.Rule)|$($entry.Path)|$normalizedFingerprint"
        if (-not $seen.Add($key)) {
            throw "$Scanner reviewed SAST manifest contains a duplicate fingerprint entry: $key"
        }
        $null = Get-RelativeRepositoryPath (Join-Path $RepoRoot $entry.Path)
    }
}

function Get-ReviewedSastEvaluation {
    param(
        $Finding,
        [ValidateSet("Bandit", "Semgrep")]
        [string]$Scanner,
        [System.Collections.Generic.HashSet[string]]$MatchedFindings
    )

    if ($Scanner -eq "Bandit") {
        $rule = [string]$Finding.test_id
        $relativePath = Get-RelativeRepositoryPath $Finding.filename
        $startLine = [int]$Finding.line_number
        $endLine = $startLine
        $entries = $script:ReviewedBanditFindings
    }
    else {
        $rule = [string]$Finding.check_id
        $relativePath = Get-RelativeRepositoryPath $Finding.path
        $startLine = [int]$Finding.start.line
        $endLine = [int]$Finding.end.line
        $entries = $script:ReviewedSemgrepFindings
    }

    $candidates = @($entries | Where-Object { $_.Rule -ceq $rule -and $_.Path -ceq $relativePath })
    if ($candidates.Count -eq 0) {
        return [pscustomobject]@{ Reviewed = $false; Fingerprint = $null; Source = $null; Path = $relativePath }
    }

    $sourcePath = Join-Path $RepoRoot $relativePath
    $helperPath = Join-Path $PSScriptRoot "reviewed_sast_fingerprint.py"
    if (-not (Test-Path $helperPath)) {
        throw "Reviewed SAST fingerprint helper is missing: $helperPath"
    }
    $fingerprintOutput = & $ToolPython $helperPath $sourcePath $startLine $endLine 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to fingerprint repository source for $Scanner $rule at ${relativePath}:${startLine}: $($fingerprintOutput -join ' ')"
    }
    $sourceFingerprint = ($fingerprintOutput -join [Environment]::NewLine) | ConvertFrom-Json
    if ($sourceFingerprint.sha256 -notmatch '^[0-9a-f]{64}$') {
        throw "$Scanner source fingerprint is missing or malformed for $rule at ${relativePath}:${startLine}."
    }

    $matches = @($candidates | Where-Object { ($_.Fingerprint -replace '-', '') -ceq $sourceFingerprint.sha256 })
    if ($matches.Count -gt 1) {
        throw "$Scanner reviewed SAST fingerprints are duplicated for $rule at $relativePath."
    }
    $reviewed = $matches.Count -eq 1
    if ($reviewed) {
        $key = "$rule|$relativePath|$($sourceFingerprint.sha256)"
        if (-not $MatchedFindings.Add($key)) {
            throw "$Scanner emitted a duplicate reviewed finding for $rule at $relativePath."
        }
    }

    return [pscustomobject]@{
        Reviewed = $reviewed
        Fingerprint = $sourceFingerprint.sha256
        Source = $sourceFingerprint
        Path = $relativePath
    }
}

function Assert-ReviewedSastCoverage {
    param(
        [array]$Entries,
        [System.Collections.Generic.HashSet[string]]$Matched,
        [string]$Scanner
    )

    $missing = @($Entries | Where-Object {
        -not $Matched.Contains("$($_.Rule)|$($_.Path)|$($_.Fingerprint -replace '-', '')")
    })
    if ($missing.Count -gt 0) {
        foreach ($entry in $missing) {
            Write-Host "[STALE REVIEW] $Scanner $($entry.Rule) $($entry.Path) SHA-256 $($entry.Fingerprint) was not observed."
        }
        throw "$Scanner reviewed SAST manifest contains $($missing.Count) stale or unmatched entry/entries."
    }
}

Assert-ReviewedSastManifest $ReviewedBanditFindings "Bandit"
Assert-ReviewedSastManifest $ReviewedSemgrepFindings "Semgrep"

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
    $script:MatchedSemgrepFindings = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::Ordinal)
    $evaluatedFindings = @($semgrepReport.results | ForEach-Object {
        [pscustomobject]@{
            Finding = $_
            Evaluation = Get-ReviewedSastEvaluation $_ "Semgrep" $script:MatchedSemgrepFindings
        }
    })
    $unreviewed = @($evaluatedFindings | Where-Object { -not $_.Evaluation.Reviewed })
    foreach ($item in @($evaluatedFindings | Where-Object { $_.Evaluation.Reviewed })) {
        $finding = $item.Finding
        $source = $item.Evaluation.Source
        Write-Host "[REVIEWED] Semgrep $($finding.check_id) at $($item.Evaluation.Path):$($finding.start.line) SHA-256 $($item.Evaluation.Fingerprint) (source context $($source.previous -join '-') / $($source.reviewed -join '-') / $($source.following -join '-'))"
    }
    foreach ($item in $unreviewed) {
        $finding = $item.Finding
        $fingerprintDetail = if ($item.Evaluation.Fingerprint) { " SHA-256 $($item.Evaluation.Fingerprint)" } else { "" }
        Write-Host "[FINDING] Semgrep $($finding.check_id) at $($item.Evaluation.Path):$($finding.start.line)$fingerprintDetail"
    }
    if ($unreviewed.Count -gt 0) {
        throw "Semgrep reported $($unreviewed.Count) unreviewed finding(s)."
    }
    Assert-ReviewedSastCoverage $script:ReviewedSemgrepFindings $script:MatchedSemgrepFindings "Semgrep"
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
    $script:MatchedBanditFindings = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::Ordinal)
    $evaluatedFindings = @($banditReport.results | ForEach-Object {
        [pscustomobject]@{
            Finding = $_
            Evaluation = Get-ReviewedSastEvaluation $_ "Bandit" $script:MatchedBanditFindings
        }
    })
    $unreviewed = @($evaluatedFindings | Where-Object { -not $_.Evaluation.Reviewed })
    foreach ($item in @($evaluatedFindings | Where-Object { $_.Evaluation.Reviewed })) {
        $finding = $item.Finding
        $source = $item.Evaluation.Source
        Write-Host "[REVIEWED] Bandit $($finding.test_id) at $($item.Evaluation.Path):$($finding.line_number) SHA-256 $($item.Evaluation.Fingerprint) (source context $($source.previous -join '-') / $($source.reviewed -join '-') / $($source.following -join '-'))"
    }
    foreach ($item in $unreviewed) {
        $finding = $item.Finding
        $fingerprintDetail = if ($item.Evaluation.Fingerprint) { " SHA-256 $($item.Evaluation.Fingerprint)" } else { "" }
        Write-Host "[FINDING] Bandit $($finding.test_id) at $($item.Evaluation.Path):$($finding.line_number)$fingerprintDetail"
    }
    if ($unreviewed.Count -gt 0) {
        throw "Bandit reported $($unreviewed.Count) unreviewed finding(s)."
    }
    Assert-ReviewedSastCoverage $script:ReviewedBanditFindings $script:MatchedBanditFindings "Bandit"
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
