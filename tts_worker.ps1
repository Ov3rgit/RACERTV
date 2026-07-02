# Persistent team-radio TTS worker.
# Protocol (one request per stdin line):  <wavpath><TAB><voice><TAB><ssml>
# Selects <voice> (per-driver accent) if non-empty, renders to <wavpath>, then
# prints "OK" so Python can post-process (radio FX) and play it.
$ErrorActionPreference = 'SilentlyContinue'
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.Volume = 100
[Console]::Out.WriteLine('READY')
[Console]::Out.Flush()
while ($true) {
    $line = [Console]::In.ReadLine()
    if ($null -eq $line) { break }
    if ($line -eq '__QUIT__') { break }
    $parts = $line.Split([char]9, 3)
    if ($parts.Count -lt 3) { [Console]::Out.WriteLine('ERR'); [Console]::Out.Flush(); continue }
    $path = $parts[0]; $voice = $parts[1]; $ssml = $parts[2]
    if ($voice -ne '') { try { $synth.SelectVoice($voice) } catch { } }
    try {
        $synth.SetOutputToWaveFile($path)
        $synth.SpeakSsml($ssml)
    } catch {
        try { $synth.Speak($ssml) } catch { }
    }
    try { $synth.SetOutputToNull() } catch { }
    [Console]::Out.WriteLine('OK')
    [Console]::Out.Flush()
}
