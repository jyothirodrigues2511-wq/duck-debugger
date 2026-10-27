$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
Set-Location -Path $PSScriptRoot
python -m streamlit run app.py
