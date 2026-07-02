# Exposes the modern "OneCore" TTS voices (David/Mark/George/Hazel/Sabina/Raul,
# etc.) to the classic Speech API that the overlay's TTS uses. System.Speech
# only enumerates voices under the "Speech\Voices" key by default, so we copy
# the OneCore voice tokens across.
#
# RUN AS ADMINISTRATOR, after installing the voice packs AND rebooting once.
$ErrorActionPreference = 'SilentlyContinue'
$src = 'HKLM:\SOFTWARE\Microsoft\Speech_OneCore\Voices\Tokens'
$dst = 'HKLM:\SOFTWARE\Microsoft\Speech\Voices\Tokens'
$wow = 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Speech\Voices\Tokens'

if (-not (Test-Path $src)) { Write-Output 'No OneCore voices found. Reboot after installing them.'; exit }

$count = 0
Get-ChildItem $src | ForEach-Object {
    $name = $_.PSChildName
    Copy-Item -Path $_.PSPath -Destination "$dst\$name" -Recurse -Force
    if (Test-Path (Split-Path $wow)) {
        Copy-Item -Path $_.PSPath -Destination "$wow\$name" -Recurse -Force
    }
    $count++
}
Write-Output "Exposed $count voices to System.Speech:"
Add-Type -AssemblyName System.Speech
(New-Object System.Speech.Synthesis.SpeechSynthesizer).GetInstalledVoices() |
    ForEach-Object { '  ' + $_.VoiceInfo.Name + '  [' + $_.VoiceInfo.Culture.Name + ']' }
