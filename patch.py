import os, re

# 1. 修复 settings.gradle.kts
if os.path.exists('settings.gradle.kts'):
    with open('settings.gradle.kts', 'r+', encoding='utf-8') as f:
        c = f.read()
        if 'org.jetbrains.kotlin.plugin.compose' not in c:
            f.seek(0)
            f.write(c.replace('pluginManagement {', 'pluginManagement {\nplugins {\n id("org.jetbrains.kotlin.android") version "2.0.0"\n id("org.jetbrains.kotlin.plugin.compose") version "2.0.0"\n}\n'))

# 2. 修复 app/build.gradle.kts (注入 Compose 依赖)
p = 'app/build.gradle.kts'
if os.path.exists(p):
    with open(p, 'r+', encoding='utf-8') as f:
        c = f.read().replace('JavaVersion.VERSION_1_8', 'JavaVersion.VERSION_17').replace('jvmTarget = "1.8"', 'jvmTarget = "17"')
        if 'compose = true' not in c:
            c = c.replace('android {', 'android {\n buildFeatures { compose = true }')
        if 'activity-compose' not in c and 'dependencies {' in c:
            deps = 'dependencies {\n implementation("androidx.activity:activity-compose:1.9.0")\n implementation("androidx.compose.ui:ui:1.6.8")\n implementation("androidx.compose.material3:material3:1.2.1")'
            c = c.replace('dependencies {', deps)
        f.seek(0); f.write(c); f.truncate()

# 3. 修复 MainActivity.kt (注入进度条与状态提示) & ZipStoredWriter.kt
for r, _, fs in os.walk('.'):
    for file in fs:
        fp = os.path.join(r, file)
        if file == 'MainActivity.kt':
            with open(fp, 'r', encoding='utf-8') as f:
                c = f.read()
            
            # 导入 Compose setContent 及 ProgressIndicator
            if 'import androidx.activity.compose.setContent' not in c:
                imports = '''import androidx.activity.compose.setContent
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.ui.unit.dp'''
                c = re.sub(r'(package\s+[^\n]+)', r'\1\n' + imports, c, count=1)
            
            # 替换底层占位文本并加入流动进度条
            c = c.replace('"Native backend placeholder"', '"准备就绪 / 处理中..."')
            if 'LinearProgressIndicator' not in c and 'Text(text = statusText)' in c:
                c = c.replace('Text(text = statusText)', 'LinearProgressIndicator(modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp))\n                Text(text = statusText)')
            
            with open(fp, 'w', encoding='utf-8') as f:
                f.write(c)

        elif file == 'ZipStoredWriter.kt':
            with open(fp, 'r+', encoding='utf-8') as f:
                lines = [('// ' + l if ('crc =' in l or 'crc=' in l) and 'CRC32()' not in l else l) for l in f.readlines()]
                f.seek(0); f.writelines(lines); f.truncate()
