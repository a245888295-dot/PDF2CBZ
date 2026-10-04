import os
import re

print("🚀 正在自动补全 Gradle 缺失依赖并修复编译问题...")

# ==============================================================================
# 📦 [V1.0] 自动提取 Kotlin 版本并补全 Compose 与 DocumentFile 库依赖
# ==============================================================================
def get_kotlin_version():
    kotlin_ver = None
    for r, _, fs in os.walk('.'):
        for f in fs:
            if f == 'libs.versions.toml':
                try:
                    with open(os.path.join(r, f), 'r', encoding='utf-8') as file:
                        m = re.search(r'kotlin\s*=\s*["\']([^"\']+)["\']', file.read())
                        if m:
                            kotlin_ver = m.group(1)
                except Exception:
                    pass

    if not kotlin_ver:
        for r, _, fs in os.walk('.'):
            for f in fs:
                if 'build.gradle' in f:
                    try:
                        with open(os.path.join(r, f), 'r', encoding='utf-8') as file:
                            m = re.search(r'org\.jetbrains\.kotlin\.android["\']?\s*\)?\s*version\s*["\']([^"\']+)["\']', file.read())
                            if m:
                                kotlin_ver = m.group(1)
                                break
                    except Exception:
                        pass

    if not kotlin_ver:
        kotlin_ver = "2.0.0"
        
    print(f"🔍 [Kotlin 检测] 当前确定版本为: {kotlin_ver}")
    return kotlin_ver

def fix_gradle_config():
    kotlin_ver = get_kotlin_version()
    compose_plugin_str = f'id("org.jetbrains.kotlin.plugin.compose") version "{kotlin_ver}"'
    
    for r, _, fs in os.walk('.'):
        for file in fs:
            if file == 'build.gradle.kts' and 'app' in r:
                fp = os.path.join(r, file)
                with open(fp, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 1. 确保 Compose 插件版本
                if 'org.jetbrains.kotlin.plugin.compose' in content:
                    content = re.sub(
                        r'id\s*\(\s*["\']org\.jetbrains\.kotlin\.plugin\.compose["\']\s*\)(\s*version\s*["\'][^"\']+["\'])?',
                        compose_plugin_str,
                        content
                    )
                else:
                    if 'plugins {' in content:
                        content = content.replace('plugins {', f'plugins {{\n    {compose_plugin_str}')
                    else:
                        content = compose_plugin_str + '\n' + content

                # 2. 确保开启 compose 支持
                if 'buildFeatures' not in content:
                    if 'android {' in content:
                        content = content.replace('android {', 'android {\n    buildFeatures {\n        compose = true\n    }')
                elif 'compose' not in content:
                    content = content.replace('buildFeatures {', 'buildFeatures {\n        compose = true')

                # 3. 自动注入报错缺失的关键依赖项
                deps_to_add = [
                    'implementation("androidx.activity:activity-compose:1.9.0")',
                    'implementation("androidx.documentfile:documentfile:1.0.1")',
                    'implementation("androidx.compose.material3:material3:1.2.1")',
                    'implementation("androidx.compose.ui:ui:1.6.8")'
                ]
                
                needed_deps = []
                for dep in deps_to_add:
                    pkg_key = dep.split('"')[1].split(':')[1]
                    if pkg_key not in content:
                        needed_deps.append(dep)
                
                if needed_deps:
                    deps_block = "\n    ".join(needed_deps)
                    if 'dependencies {' in content:
                        content = content.replace('dependencies {', f'dependencies {{\n    {deps_block}')
                    else:
                        content += f'\ndependencies {{\n    {deps_block}\n}}'

                with open(fp, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✅ [V1.0] 已成功修复依赖并补全库支持: {fp}")
                return

# 执行 Gradle 依赖补全
fix_gradle_config()


# ==============================================================================
# 📦 [V2.0] 重置并写入轻量化渲染 MainActivity.kt
# ==============================================================================
def update_main_activity():
    target_file = None
    for r, _, fs in os.walk('.'):
        for file in fs:
            if file == 'MainActivity.kt':
                target_file = os.path.join(r, file)
                break

    if not target_file:
        print("❌ [V2.0] 未找到 MainActivity.kt")
        return

    new_main_activity = r'''package com.example.pdf2cbz

import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.pdf.PdfRenderer
import android.net.Uri
import android.os.Bundle
import android.provider.OpenableColumns
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.documentfile.provider.DocumentFile
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import java.io.ByteArrayOutputStream
import java.util.zip.ZipOutputStream

class MainActivity : ComponentActivity() {
    private val pdfs = mutableStateListOf<Uri>()
    private var outputTree by mutableStateOf<Uri?>(null)

    private val pickPdfs = registerForActivityResult(
        ActivityResultContracts.OpenMultipleDocuments()
    ) { uris ->
        pdfs.clear()
        pdfs.addAll(uris.filter { it.toString().isNotBlank() })
    }

    private val pickTree = registerForActivityResult(
        ActivityResultContracts.OpenDocumentTree()
    ) { uri ->
        if (uri != null) {
            contentResolver.takePersistableUriPermission(
                uri,
                Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION
            )
            outputTree = uri
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                val scope = rememberCoroutineScope()
                var log by remember { mutableStateOf("等待选择 PDF…") }
                var isProcessing by remember { mutableStateOf(false) }

                Column(
                    modifier = Modifier.fillMaxSize().padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Text("PDF2CBZ Ultimate", style = MaterialTheme.typography.headlineSmall)
                    Text("轻量渲染 · 体积优化 · 零 NDK 依赖")

                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(
                            enabled = !isProcessing,
                            onClick = { pickPdfs.launch(arrayOf("application/pdf")) }
                        ) { Text("选择 PDF") }

                        OutlinedButton(
                            enabled = !isProcessing,
                            onClick = { pickTree.launch(null) }
                        ) { Text("输出目录") }
                    }

                    Text("已选 PDF：${pdfs.size} 个")
                    Text("输出路径：${outputTree ?: "未选择"}")

                    if (pdfs.isNotEmpty()) {
                        LazyColumn(
                            modifier = Modifier.weight(1f),
                            verticalArrangement = Arrangement.spacedBy(6.dp)
                        ) {
                            items(pdfs) { uri ->
                                Text(
                                    getFileName(uri) ?: uri.toString(),
                                    style = MaterialTheme.typography.bodyMedium
                                )
                            }
                        }
                    } else {
                        Spacer(Modifier.weight(1f))
                    }

                    Button(
                        modifier = Modifier.fillMaxWidth(),
                        enabled = pdfs.isNotEmpty() && outputTree != null && !isProcessing,
                        onClick = {
                            isProcessing = true
                            scope.launch(Dispatchers.IO) {
                                convertPdfsToCbz { status ->
                                    scope.launch(Dispatchers.Main) { log = status }
                                }
                                isProcessing = false
                            }
                        }
                    ) {
                        Text(if (isProcessing) "正在转换中..." else "开始转换")
                    }

                    Text(log)
                }
            }
        }
    }

    private fun getFileName(uri: Uri): String? {
        var name: String? = null
        contentResolver.query(uri, null, null, null, null)?.use { cursor ->
            val nameIndex = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if (nameIndex != -1 && cursor.moveToFirst()) {
                name = cursor.getString(nameIndex)
            }
        }
        return name
    }

    private suspend fun convertPdfsToCbz(onProgress: (String) -> Unit) {
        val targetTreeUri = outputTree ?: return
        val docDir = DocumentFile.fromTreeUri(this, targetTreeUri) ?: run {
            onProgress("无法访问输出目录")
            return
        }

        val totalPdfs = pdfs.size
        pdfs.forEachIndexed { index, pdfUri ->
            val rawName = getFileName(pdfUri) ?: "document_$index.pdf"
            val baseName = rawName.substringBeforeLast(".")
            val cbzName = "$baseName.cbz"

            onProgress("正在处理 (${index + 1}/$totalPdfs): $rawName")

            val targetFile = docDir.createFile("application/x-cbz", cbzName)
                ?: docDir.createFile("application/zip", cbzName)

            if (targetFile == null) {
                onProgress("创建目标文件失败: $cbzName")
                return@forEachIndexed
            }

            try {
                contentResolver.openFileDescriptor(pdfUri, "r")?.use { pfd ->
                    PdfRenderer(pfd).use { renderer ->
                        contentResolver.openOutputStream(targetFile.uri)?.use { os ->
                            ZipOutputStream(os.buffered()).use { zipOut ->
                                val pageCount = renderer.pageCount
                                for (i in 0 until pageCount) {
                                    onProgress("正在转换 (${index + 1}/$totalPdfs): $rawName [页码 ${i + 1}/$pageCount]")

                                    renderer.openPage(i).use { page ->
                                        val scale = 2
                                        val bitmap = Bitmap.createBitmap(
                                            page.width * scale,
                                            page.height * scale,
                                            Bitmap.Config.ARGB_8888
                                        )
                                        bitmap.eraseColor(Color.WHITE)
                                        page.render(
                                            bitmap,
                                            null,
                                            null,
                                            PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY
                                        )

                                        val stream = ByteArrayOutputStream()
                                        bitmap.compress(Bitmap.CompressFormat.JPEG, 90, stream)
                                        val imageBytes = stream.toByteArray()
                                        bitmap.recycle()

                                        val entryName = String.format("%04d.jpg", i + 1)
                                        ZipStoredWriter.addStoredBytes(zipOut, imageBytes, entryName)
                                    }
                                }
                            }
                        }
                    }
                }
            } catch (e: Exception) {
                onProgress("转换失败 [$rawName]: ${e.localizedMessage}")
                return
            }
        }
        onProgress("转换完成！共成功处理 $totalPdfs 个文件。")
    }
}
'''
    with open(target_file, 'w', encoding='utf-8') as f:
        f.write(new_main_activity)
    print(f"✅ [V2.0] 已成功更新逻辑文件: {target_file}")

# 执行 V2.0 逻辑
update_main_activity()


# ==============================================================================
# 🔻🔻🔻 [V3.0 下次更新区域 - 变量隔离，可在此直接追加新代码] 🔻🔻🔻
# ==============================================================================
def patch_v3_future():
    pass

patch_v3_future()
