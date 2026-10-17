# -*- coding: utf-8 -*-
"""
v3.9.0 DSH — 应用身份补丁（图标 + 名称 + 版本号）

为什么需要这个补丁：
  原始 0.0.zip 的 res/ 目录里只有一个 styles.xml，没有任何 mipmap 图标，
  AndroidManifest.xml 也没写 android:icon —— 所以装出来的 App 用的是
  系统默认的绿色机器人图标，名字叫 "PDF2CBZ Ultimate"。

本补丁在 patch.py 之后运行，做四件事：
  1. 生成白底黑字「PDF」图标（含 Android 8+ 自适应图标）
  2. Manifest 挂上 icon/roundIcon，应用名改为「PDF 转换器」
  3. 同步 UI 文案（首页标题/关于页/日志标题）
  4. 版本号统一到 v3.9.0-dsh (390)

图标由 DejaVuSans-Bold 真实字体渲染，不是手绘近似。
若 CI 环境缺 Pillow 会自动 pip 安装；缺字体则回退到任意可用 ttf。
"""
import os
import re
import subprocess
import sys

VERSION_NAME = "3.9.0-dsh"
VERSION_CODE = 390
APP_LABEL = "PDF 转换器"


def ensure_pillow():
    try:
        from PIL import Image, ImageDraw, ImageFont  # noqa: F401
        return True
    except ImportError:
        pass
    print("[icon] Pillow 未安装，正在安装...")
    # PEP 668: Ubuntu 24.04 / Debian 12 起系统 pip 会拒绝安装，
    # 必须显式加 --break-system-packages，否则 CI 上图标会直接生成失败
    attempts = [
        ['pip3', 'install', '--quiet', '--break-system-packages', 'pillow'],
        [sys.executable, '-m', 'pip', 'install', '--quiet', '--break-system-packages', 'pillow'],
        ['pip3', 'install', '--quiet', 'pillow'],
        [sys.executable, '-m', 'pip', 'install', '--quiet', 'pillow'],
    ]
    for args in attempts:
        try:
            subprocess.check_call(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            from PIL import Image, ImageDraw, ImageFont  # noqa: F401
            print("[icon] Pillow 安装成功")
            return True
        except Exception:
            continue
    print("[icon] Pillow 安装失败")
    return False


FONT_CANDIDATES = [
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
    '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf',
    '/system/fonts/Roboto-Bold.ttf',
]


def find_font():
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            return p
    for root in ('/usr/share/fonts', '/usr/local/share/fonts'):
        for r, _, fs in os.walk(root):
            for f in fs:
                if f.lower().endswith(('.ttf', '.otf')) and 'bold' in f.lower():
                    return os.path.join(r, f)
    for root in ('/usr/share/fonts',):
        for r, _, fs in os.walk(root):
            for f in fs:
                if f.lower().endswith('.ttf'):
                    return os.path.join(r, f)
    return None


def render_icon(size, ratio, transparent, font_path):
    """白底黑字（或透明底黑字）的 PDF 图标"""
    from PIL import Image, ImageDraw, ImageFont
    TEXT = 'PDF'
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0) if transparent else (255, 255, 255, 255))
    d = ImageDraw.Draw(img)

    lo, hi, best = 1, size, 1
    while lo <= hi:
        mid = (lo + hi) // 2
        f = ImageFont.truetype(font_path, mid)
        bb = f.getbbox(TEXT)
        if (bb[2] - bb[0]) <= size * ratio:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1

    f = ImageFont.truetype(font_path, best)
    bb = d.textbbox((0, 0), TEXT, font=f)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    x = (size - tw) / 2 - bb[0]
    y = (size - th) / 2 - bb[1]
    d.text((x, y), TEXT, font=f, fill=(0, 0, 0, 255))
    return img


def find_src_main():
    for r, ds, fs in os.walk('.'):
        if 'AndroidManifest.xml' in fs and 'res' in ds:
            return r
    for r, _, fs in os.walk('.'):
        if 'AndroidManifest.xml' in fs:
            return r
    return None


def write_icons(res_dir):
    if not ensure_pillow():
        print("[icon] Pillow 不可用，跳过图标生成")
        return False
    font_path = find_font()
    if not font_path:
        print("[icon] 找不到字体，跳过图标生成")
        return False
    print("[icon] 使用字体: " + font_path)

    legacy = {'mdpi': 48, 'hdpi': 72, 'xhdpi': 96, 'xxhdpi': 144, 'xxxhdpi': 192}
    fg = {'mdpi': 108, 'hdpi': 162, 'xhdpi': 216, 'xxhdpi': 324, 'xxxhdpi': 432}

    for dens, px in legacy.items():
        out_dir = os.path.join(res_dir, 'mipmap-' + dens)
        os.makedirs(out_dir, exist_ok=True)
        img = render_icon(px, 0.62, False, font_path)
        img.convert('RGB').save(os.path.join(out_dir, 'ic_launcher.png'), 'PNG', optimize=True)

    for dens, px in fg.items():
        out_dir = os.path.join(res_dir, 'mipmap-' + dens)
        os.makedirs(out_dir, exist_ok=True)
        img = render_icon(px, 0.40, True, font_path)
        img.save(os.path.join(out_dir, 'ic_launcher_foreground.png'), 'PNG', optimize=True)

    anydpi = os.path.join(res_dir, 'mipmap-anydpi-v26')
    os.makedirs(anydpi, exist_ok=True)
    adaptive = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
        '    <background android:drawable="@color/ic_launcher_background" />\n'
        '    <foreground android:drawable="@mipmap/ic_launcher_foreground" />\n'
        '</adaptive-icon>\n'
    )
    for fn in ('ic_launcher.xml', 'ic_launcher_round.xml'):
        with open(os.path.join(anydpi, fn), 'w', encoding='utf-8') as f:
            f.write(adaptive)

    vals = os.path.join(res_dir, 'values')
    os.makedirs(vals, exist_ok=True)
    with open(os.path.join(vals, 'ic_launcher_background.xml'), 'w', encoding='utf-8') as f:
        f.write('<resources>\n    <color name="ic_launcher_background">#FFFFFF</color>\n</resources>\n')

    print("[icon] 已生成 5 尺寸启动图标 + 5 尺寸自适应前景 + XML")
    return True


def patch_manifest(src_main, icons_ok=True):
    fp = os.path.join(src_main, 'AndroidManifest.xml')
    with open(fp, 'r', encoding='utf-8') as f:
        c = f.read()
    old = c

    if 'android:label=' in c:
        c = re.sub(r'android:label="[^"]*"', 'android:label="' + APP_LABEL + '"', c)
    else:
        c = c.replace('<application', '<application\n        android:label="' + APP_LABEL + '"', 1)

    # 图标生成失败时不能挂引用，否则资源不存在会导致编译报错
    if icons_ok and 'android:icon=' not in c:
        c = c.replace(
            '<application',
            '<application\n        android:icon="@mipmap/ic_launcher"\n        android:roundIcon="@mipmap/ic_launcher_round"',
            1
        )

    if c != old:
        with open(fp, 'w', encoding='utf-8') as f:
            f.write(c)
        print("[icon] Manifest 已更新：label=" + APP_LABEL)
    else:
        print("[icon] Manifest 无需修改")


def patch_main_activity():
    target = None
    for r, _, fs in os.walk('.'):
        for f in fs:
            if f == 'MainActivity.kt':
                target = os.path.join(r, f)
                break
        if target:
            break
    if not target:
        print("[icon] 未找到 MainActivity.kt")
        return

    with open(target, 'r', encoding='utf-8') as f:
        c = f.read()
    old = c

    reps = [
        ('text = "PDF → CBZ",', 'text = "' + APP_LABEL + '",'),
        ('PageHeader("关于 PDF2CBZ", onBack)',
         'PageHeader("关于 ' + APP_LABEL + '", onBack)'),
        ('ClipData.newPlainText("PDF2CBZ 日志", fullLogText)',
         'ClipData.newPlainText("' + APP_LABEL + ' 日志", fullLogText)'),
        ('StringBuilder("=== PDF2CBZ 运行日志 ($timeStamp) ===\\n")',
         'StringBuilder("=== ' + APP_LABEL + ' 运行日志 ($timeStamp) ===\\n")'),
    ]
    done = 0
    for o, n in reps:
        if o in c:
            c = c.replace(o, n, 1)
            done += 1

    c = re.sub(r'\[启动\] PDF2CBZ v[0-9A-Za-z.\-]+',
               '[启动] ' + APP_LABEL + ' v' + VERSION_NAME, c)
    c = re.sub(r'Text\("v[0-9][0-9A-Za-z.\-]*", fontSize = 16\.sp',
               'Text("v' + VERSION_NAME + '", fontSize = 16.sp', c)

    if c != old:
        with open(target, 'w', encoding='utf-8') as f:
            f.write(c)
        print("[icon] MainActivity.kt 文案已更新（%d 处确定匹配）" % done)
    else:
        print("[icon] MainActivity.kt 未变化")


def patch_version():
    for r, _, fs in os.walk('.'):
        if 'app' not in r:
            continue
        for f in fs:
            if f != 'build.gradle.kts':
                continue
            fp = os.path.join(r, f)
            with open(fp, 'r', encoding='utf-8') as fh:
                c = fh.read()
            c2 = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = %d' % VERSION_CODE, c)
            c2 = re.sub(r'versionName\s*=\s*"[^"]*"', 'versionName = "' + VERSION_NAME + '"', c2)
            if c2 != c:
                with open(fp, 'w', encoding='utf-8') as fh:
                    fh.write(c2)
                print("[icon] 版本号 → " + VERSION_NAME + " (" + str(VERSION_CODE) + ")")


def main():
    print('=== icon_patch v3.9.0 开始 ===')
    src_main = find_src_main()
    if not src_main:
        print('[icon] 未找到 src/main，终止')
        sys.exit(1)
    print('[icon] src/main = ' + src_main)
    ok = write_icons(os.path.join(src_main, 'res'))
    patch_manifest(src_main, ok)
    patch_main_activity()
    patch_version()
    print('=== icon_patch 完成 ===')


if __name__ == '__main__':
    main()
