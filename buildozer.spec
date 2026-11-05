[app]
title = RiseSim
package.name = risesim
package.domain = org.risesim
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,csv,txt,md
source.include_patterns = data/*.csv,save/*.csv
source.exclude_dirs = tests,bin,venv,.git,__pycache__,.buildozer
source.exclude_patterns = test_*.py,*.pyc
version = 0.1.0

requirements = hostpython3==3.11.10,python3==3.11.10,kivy==2.3.0,pyjnius,android,plyer

orientation = portrait
fullscreen = 0
android.api = 33
android.minapi = 24
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.allow_backup = True
android.add_assets = data

# 安定版 p4a（Python 3.14 デフォルトを避ける）
p4a.branch = v2024.01.21

presplash.color = #1a1a2e
android.presplash_color = #1a1a2e

[buildozer]
log_level = 2
warn_on_root = 0
