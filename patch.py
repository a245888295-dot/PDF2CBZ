import os
import zipfile
import glob

# 1. 自动定位仓库根目录
current_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = current_dir
while not os.path.exists(os.path.join(repo_root, "0.0.zip")):
    parent = os.path.dirname(repo_root)
    if parent == repo_root: break
    repo_root = parent
os.chdir(repo_root)

# 2. 寻找历史版本底板
versions_dir = "版本"
os.makedirs(versions_dir, exist_ok=True)
existing_zips = glob.glob(os.path.join(versions_dir, "*.zip"))
if existing_zips:
    existing_zips.sort()
    base_zip = existing_zips[-1]
else:
    base_zip = "0.0.zip"

# 3. 解压底板
with zipfile.ZipFile(base_zip, 'r') as zf:
    zf.extractall('.')

# 4. 应用以前所有的历史更新
# ==================== 粘贴上方强制覆盖的 Python 代码 ====================
# （包含 AndroidManifest, settings.gradle.kts, app/build.gradle.kts 的写入）
# =====================================================================

# 5. 应用以前写好的 MainActivity.kt 和 ZipStoredWriter.kt 写入逻辑
# ==================== 粘贴你原有的写入 Kotlin 代码 ====================

# 6. 应用本次的最新更新（关闭1.5倍放大 + 无损WebP）
# ==================== 粘贴无损 WebP 修复代码 ====================

# 7. 打包成新版本 zip
# ==================== 保留原有的打包逻辑 ====================
