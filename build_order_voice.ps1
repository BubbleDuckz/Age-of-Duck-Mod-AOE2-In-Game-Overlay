param([string]$Manifest, [string]$Output)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $entries = Get-Content -LiteralPath $Manifest -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($entry in $entries) {
        $destination = Join-Path $Output ($entry.index.ToString() + '.wav')
        if (-not (Test-Path -LiteralPath $destination)) {
            $temporary = $destination + ".partial"
            $speaker.SetOutputToWaveFile($temporary)
            $speaker.Speak([string]$entry.text)
            $speaker.SetOutputToNull()
            Move-Item -LiteralPath $temporary -Destination $destination -Force
        }
    }
} finally { $speaker.Dispose() }
