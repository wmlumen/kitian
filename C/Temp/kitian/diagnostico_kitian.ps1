$ErrorActionPreference='SilentlyContinue'
$kitian='C:\Temp\kitian'
$report=Join-Path $kitian 'diagnostico_kitian.txt'
"$(['datetime]::Now) - KITIAN DIAG" | Out-File $report
"---" | Out-File $report -Append

"PYTHON:" | Out-File $report -Append
python --version 2>&1 | Out-File $report -Append
where.exe python 2>&1 | Out-File $report -Append

"ARCHIVOS:" | Out-File $report -Append
@('activar_kitian.bat','kitian_hud.py','kitian_http_standalone_real.py','nebula_web.html','reddot.ico') | ForEach-Object {
  $p=Join-Path $kitian $_
  if (Test-Path $p){ "$_ OK" } else { "$_ MISSING" }
} | Out-File $report -Append

"PROCESOS:" | Out-File $report -Append
Get-Process -Name python* 2>$null | Select-Object Name, Id, Path | Out-String | Out-File $report -Append

"PUERTOS:" | Out-File $report -Append
@(8080,8081,8082) | ForEach-Object {
  $open=Get-NetTCPConnection -LocalPort $_ 2>$null
  if ($open){ "$_ OPEN" } else { "$_ CLOSED" }
} | Out-File $report -Append

"AUDIO:" | Out-File $report -Append
$py=(Get-Command python -ErrorAction SilentlyContinue).Source
$pkgs=@('sounddevice','faster-whisper','torch','onnxruntime','pyttsx3','pyaudio','numpy')
if ($py){
  foreach ($p in $pkgs){
    $r=python -c "import importlib.util as u; print('OK' if u.find_spec('$p') else 'FAIL')" 2>&1
    "$p : $r"
  } | Out-File $report -Append
}

"ATAJO:" | Out-File $report -Append
$lnk=Join-Path $HOME 'Desktop\Kitian.lnk'
if (Test-Path $lnk){ 'Kitian.lnk presente' } else { 'Kitian.lnk ausente' } | Out-File $report -Append

"LOG Kitian:" | Out-File $report -Append
if (Test-Path (Join-Path $kitian 'kitian.log')){ 'kitian.log presente' } else { 'kitian.log ausente' } | Out-File $report -Append

Write-Output "Reporte guardado en $report"
