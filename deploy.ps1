[CmdletBinding()]
param(
    [Alias('project-id')]
    [string]$ProjectId = 'recovery-meal',

    [string]$Region = 'us-central1',

    [string]$Service = 'recovery-meal-api',

    [string]$Repo = 'recovery-meal',

    [string]$Bucket = 'recovery-meal-media',

    [switch]$BackendOnly,

    [switch]$FrontendOnly
)

$ErrorActionPreference = 'Stop'

function Invoke-NativeCommand {
    param(
        [Parameter(Mandatory)]
        [string]$Command,

        [Parameter(ValueFromRemainingArguments)]
        [string[]]$Arguments
    )

    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $Command $($Arguments -join ' ')"
    }
}

$RootDir = $PSScriptRoot
$ServiceAccount = "recovery-meal-api@${ProjectId}.iam.gserviceaccount.com"
$Image = "${Region}-docker.pkg.dev/${ProjectId}/${Repo}/${Service}"
$Sha = ((Invoke-NativeCommand git -C $RootDir rev-parse --short HEAD) -join '').Trim()

Write-Host "project=$ProjectId region=$Region service=$Service tag=$Sha"

if (-not $FrontendOnly) {
    Write-Host "`n== Building backend image =="
    Invoke-NativeCommand docker build --platform linux/amd64 -t "${Image}:$Sha" -t "${Image}:latest" (Join-Path $RootDir 'backend')
    Invoke-NativeCommand docker push "${Image}:$Sha"
    Invoke-NativeCommand docker push "${Image}:latest"

    Write-Host "`n== Deploying Cloud Run =="
    Invoke-NativeCommand gcloud run deploy $Service `
        "--project=$ProjectId" `
        "--region=$Region" `
        "--image=${Image}:$Sha" `
        "--service-account=$ServiceAccount" `
        '--allow-unauthenticated' `
        '--min-instances=0' `
        '--max-instances=1' `
        '--memory=1Gi' `
        '--cpu=1' `
        '--timeout=120s' `
        '--set-secrets=DATABASE_URL=DATABASE_URL:latest,OPENAI_API_KEY=OPENAI_API_KEY:latest' `
        '--set-env-vars=APP_ENV=production,AI_MODE=live,IMAGE_MODE=live,UPLOAD_DIR=/app/uploads' `
        "--add-volume=name=media,type=cloud-storage,bucket=$Bucket" `
        '--add-volume-mount=volume=media,mount-path=/app/uploads'

    $DeployedJson = (Invoke-NativeCommand gcloud run services describe $Service "--project=$ProjectId" "--region=$Region" '--format=json') -join "`n"
    $Deployed = $DeployedJson | ConvertFrom-Json
    $Container = $Deployed.spec.template.spec.containers | Select-Object -First 1
    $HasMediaMount = $Container.volumeMounts | Where-Object { $_.mountPath -eq '/app/uploads' } | Select-Object -First 1
    if (-not $HasMediaMount) {
        throw "Bucket $Bucket is not mounted at /app/uploads; media would not persist."
    }

    $UploadDirectory = $Container.env | Where-Object { $_.name -eq 'UPLOAD_DIR' } | Select-Object -First 1
    if (-not $UploadDirectory -or $UploadDirectory.value -ne '/app/uploads') {
        throw 'UPLOAD_DIR is not /app/uploads; media uploads would not persist.'
    }

    $Url = ((Invoke-NativeCommand gcloud run services describe $Service "--project=$ProjectId" "--region=$Region" '--format=value(status.url)') -join '').Trim()
    Write-Host "API: $Url"
    Invoke-NativeCommand curl.exe -fsS "$Url/health"
    Write-Host
}

if (-not $BackendOnly) {
    Write-Host "`n== Building frontend-v2 =="
    $FrontendDir = Join-Path $RootDir 'frontend-v2'
    Push-Location $FrontendDir
    try {
        if (-not (Test-Path -LiteralPath (Join-Path $FrontendDir 'node_modules') -PathType Container)) {
            Invoke-NativeCommand npm ci
        }
        Invoke-NativeCommand npm run build
    }
    finally {
        Pop-Location
    }

    Write-Host "`n== Deploying Firebase Hosting =="
    Invoke-NativeCommand firebase deploy --only hosting --project $ProjectId
    Write-Host "UI: https://$ProjectId.web.app"
}

Write-Host "`nDone."