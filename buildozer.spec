[app]

title = FinWise
package.name = finwise
package.domain = org.finwise

source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,ttf,atlas,json,db

version = 1.0

requirements = python3,kivy==2.3.1,kivymd2==2.0.1,pillow,sqlite3,filetype,materialyoucolor,exceptiongroup,asyncgui,asynckivy

orientation = portrait
fullscreen = 0

android.api = 33
android.minapi = 24
android.ndk = 25b
android.accept_sdk_license = True

# Optional but useful
android.archs = arm64-v8a, armeabi-v7a

log_level = 2

# Include common project dirs if they exist
source.exclude_dirs = .git,__pycache__,venv,.venv,build,dist,.idea,.github

[buildozer]
log_level = 2
warn_on_root = 1
