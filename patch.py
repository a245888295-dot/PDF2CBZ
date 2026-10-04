import os
import zipfile
import glob

# 1. 确定基础底板
versions_dir = "版本"
os.makedirs(versions_dir, exist_ok=True)

# 找版本文件夹里已有的 zip，没有就找根目录的 0.0.zip
existing_zips = glob.glob(os.path.join(versions_dir, "*.zip"))
if not existing_zips:
    if os.path.exists("0.0.zip"):
        base_zip = "0.0.zip"
        print(">>> 基础底板: 0.0.zip")
    else:
        print("❌ 找不到 0.0.zip，请确保它在仓库根目录")
        exit(1)
else:
    existing_zips.sort()
    base_zip = existing_zips[-1]
    print(f">>> 基础底板: {base_zip}")

# 2. 解压基础底板
print(">>> 正在解压...")
with zipfile.ZipFile(base_zip, 'r') as zf:
    zf.extractall('.')

# 3. 应用以前所有的历史更新
# =====================================================================
# ⚠️⚠️⚠️ 把以前你 py 脚本里的更新逻辑（AndroidManifest、Gradle、MainActivity 写入代码）
# 全部粘贴在这个位置！不能漏，漏了源码就不完整了！
# =====================================================================


# 4. 应用本次的最新更新（关闭1.5倍放大 + 无损WebP）
print(">>> 应用最新更新: 修复画质...")
for r, _, fs in os.walk('.'):
    for file in fs:
        if file == 'MainActivity.kt':
            p = os.path.join(r, file)
            with open(p, 'r+', encoding='utf-8') as f:
                c = f.read()
                # 关闭无意义的 1.5 倍放大
                c = c.replace('val width = (page.width * 1.5f).toInt()', 'val width = page.width')
                c = c.replace('val height = (page.height * 1.5f).toInt()', 'val height = page.height')
                # 95% JPEG 替换为无损 WebP
                c = c.replace(
                    'bitmap.compress(Bitmap.CompressFormat.JPEG, 95, baos)',
                    'if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.R) {\n'
                    '                            bitmap.compress(Bitmap.CompressFormat.WEBP_LOSSLESS, 100, baos)\n'
                    '                        } else {\n'
                    '                            bitmap.compress(Bitmap.CompressFormat.JPEG, 100, baos)\n'
                    '                        }'
                )
                f.seek(0); f.write(c); f.truncate()

# 5. 打包成新版本 zip
if not existing_zips:
    new_version = "v0.1"
else:
    # 自动递增版本号
    new_version = f"v{len(existing_zips) + 1}.0"

new_zip_path = os.path.join(versions_dir, f"{new_version}.zip")
print(f">>> 正在打包新底板: {new_zip_path}")

exclude_dirs = {'.gradle', 'build', '.idea', 'app/build', '.git', '版本'}
with zipfile.ZipFile(new_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith('.')]
        for file in files:
            if file.endswith('.zip'):
                continue
            file_path = os.path.join(root, file)
            arcname = os.path.relpath(file_path, '.')
            zf.write(file_path, arcname)

print(f"✅ 成功生成新底板: {new_zip_path}")
