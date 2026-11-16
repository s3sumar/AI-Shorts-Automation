param([string]$Request,[string]$Output)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$plan = Get-Content -LiteralPath $Request -Raw | ConvertFrom-Json
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
$speaker.SelectVoice([string]$plan.voice)
$speaker.SetOutputToWaveFile($Output)
$text = [System.Security.SecurityElement]::Escape([string]$plan.text)
if ($plan.directed) {
    $rate = [string]$plan.rate_percent + '%'
    $ssml = '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US"><prosody rate="' + $rate + '"><emphasis level="moderate">' + $text + '</emphasis></prosody></speak>'
    $speaker.SpeakSsml($ssml)
} else {
    $speaker.Speak([string]$plan.text)
}
$speaker.Dispose()
