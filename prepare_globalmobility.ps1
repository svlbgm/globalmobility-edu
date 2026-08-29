$ErrorActionPreference = "Stop"

$documentsDirectory = Join-Path $PSScriptRoot "documents"
$archiveDirectory = Join-Path $documentsDirectory "archive_previous_demo"

$policyFiles = @(
    "academic_integrity_v3_2025.txt",
    "double_major_course_counting_v1_2026.txt",
    "exchange_application_calendar_v1_2026.txt",
    "exchange_course_recognition_v1_2022.txt",
    "exchange_course_recognition_v2_2026.txt",
    "learning_agreement_v1_2023.txt",
    "learning_agreement_v2_2026.txt",
    "legacy_exchange_faq_2022.txt",
    "student_appeals_v2_2025.txt"
)

New-Item `
    -ItemType Directory `
    -Path $archiveDirectory `
    -Force | Out-Null

Get-ChildItem -Path $documentsDirectory -File |
    Where-Object {
        $_.Extension.ToLower() -in @(".txt", ".pdf", ".docx") -and
        $_.Name -notin $policyFiles
    } |
    ForEach-Object {
        $destination = Join-Path $archiveDirectory $_.Name

        if (Test-Path $destination) {
            $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
            $destination = Join-Path `
                $archiveDirectory `
                "$($_.BaseName)-$timestamp$($_.Extension)"
        }

        Move-Item -Path $_.FullName -Destination $destination
        Write-Host "Archived previous demo document: $($_.Name)"
    }

Write-Host "GlobalMobility EDU documents are ready."
Write-Host "Next command: python ingest.py"
