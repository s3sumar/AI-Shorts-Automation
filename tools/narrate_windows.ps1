param([string]$Config, [string]$Output)
$ErrorActionPreference = 'Stop'
$episode = Get-Content -LiteralPath $Config -Raw | ConvertFrom-Json
New-Item -ItemType Directory -Path $Output -Force | Out-Null
$speaker = New-Object -ComObject SAPI.SpVoice
$speaker.Rate = 0
$speaker.Volume = 100
$index = 0
foreach ($line in $episode.narration) {
    $path = Join-Path $Output ('voice_{0:D2}.wav' -f $index)
    $stream = New-Object -ComObject SAPI.SpFileStream
    $stream.Format.Type = 22
    $stream.Open($path, 3, $false)
    $speaker.AudioOutputStream = $stream
    [void]$speaker.Speak([string]$line.text)
    $stream.Close()
    $index++
}
Write-Output ('Synthesized {0} radio lines with {1}' -f $index, $speaker.Voice.GetDescription())
