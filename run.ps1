Write-Host "Sinav Takvimi Sistemi Baslatiliyor..."

Set-Location -Path $PSScriptRoot

if (-not (Test-Path -Path "venv")) {
    Write-Host "Sanal ortam bulunamadi, olusturuluyor..."
    python -m venv venv
    if (-not $?) {
        Write-Host "Sanal ortam olusturulamadi. Lutfen Python'un kurulu ve PATH'e ekli oldugundan emin olun."
        exit 1
    }
    Write-Host "Sanal ortam olusturuldu."
}

. .\venv\Scripts\Activate.ps1

Write-Host "Gerekli paketler kontrol ediliyor/yukleniyor..."
pip install -r requirements.txt
if (-not $?) {
    Write-Host "Paketler yuklenirken bir hata olustu."
    exit 1
}

$env:PYTHONPATH = $PSScriptRoot

Write-Host "Uygulama baslatiliyor..."
python src/app.py
