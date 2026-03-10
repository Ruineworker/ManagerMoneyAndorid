[app]
title = FinWise
package.name = finwise
package.domain = org.finwise
source.dir = .
source.include_exts = py,kv,png,jpg,atlas,json
version = 1.1.0

# Keep runtime small and deterministic on Android.
requirements = python3,kivy==2.3.1,kivymd==2.0.1.dev0,pillow
orientation = portrait
fullscreen = 0
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
android.private_storage = True
android.allow_backup = True
android.statusbar_color = #14B8A6
android.background_color = #F0FDFA
log_level = 1

# Exclude development leftovers from package.
exclude_dirs = .git,.github,__pycache__,bin,.buildozer
exclude_patterns = *.pyc,*.pyo,*.db-shm,*.db-wal

[buildozer]
log_level = 1
warn_on_root = 1
build_dir = ./.buildozer
bin_dir = ./bin
