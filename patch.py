import os
import re

print("🚀 正在全局重组 PDF2CBZ（自动修补 Manifest + 防屏幕/拔电重置 ViewModel + 极致 I/O 提速）...")

# 1. 自动清理冲突文件
def clean_conflicting_files():
    for r, _, fs in os.walk('.'):
        for file in fs:
            if file == 'ZipStoredWriter.kt':
                fp = os.path.join(r, file)
                try:
                    os.remove(fp)
                    print(f"🧹 已成功清理冲突文件: {fp}")
                except Exception as e:
                    print(f"⚠ 清理冲突文件失败: {e}")

clean_conflicting_files()

# 2. 修改 AndroidManifest.xml 彻底解决屏幕旋转/插拔充电恢复初始状态的问题
def patch_manifest():
    for r, _, fs in os.walk('.'):
        for file in fs:
            if file == 'AndroidManifest.xml':
                fp = os.path.join(r, file)
                try:
                    with open(fp, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # 防止旋转屏幕/插拔充电/主题切换导致 Activity 销毁重建
                    if 'android:configChanges' not in content:
                        config_attr = 'android:configChanges="orientation|screenSize|screenLayout|keyboardHidden|uiMode"'
                        content = content.replace('<activity', f'<activity {config_attr}')
                        with open(fp, 'w', encoding='utf-8') as f:
                            f.write(content)
                        print(f"✅ 已注入 AndroidManifest 防重置属性: {fp}")
                except Exception as e:
                    print(f"⚠ 修改 Manifest 失败: {e}")

patch_manifest()

# 3. 自动检测 Kotlin 版本
def find_kotlin_version():
    toml_path = os.path.join('gradle', 'libs.versions.toml')
    if os.path.exists(toml_path):
        try:
            with open(toml_path, 'r', encoding='utf-8') as f:
                content = f.read()
            m = re.search(r'kotlin\s*=\s*"([^"]+)"', content)
            if m:
                return m.group(1)
        except Exception:
            pass

    for r, _, fs in os.walk('.'):
        for file in fs:
            if file.endswith('.gradle.kts'):
                fp = os.path.join(r, file)
                try:
                    with open(fp, 'r', encoding='utf-8') as f:
                        c = f.read()
                    m = re.search(r'kotlin[^\n]*version[^\n]*"([^"]+)"', c, re.IGNORECASE)
                    if m:
                        return m.group(1)
                    m2 = re.search(r'"org\.jetbrains\.kotlin[^\n]*"\s*version\s*"([^"]+)"', c)
                    if m2:
                        return m2.group(1)
                except Exception:
                    pass
    return "2.0.20"

# 4. 修复 build.gradle.kts，补充 ViewModel 依赖库
def patch_build_gradle():
    kotlin_ver = find_kotlin_version()
    print(f"🔍 检测到当前项目 Kotlin 版本: {kotlin_ver}")

    gradle_path = None
    for root, dirs, files in os.walk('.'):
        if 'build.gradle.kts' in files and ('app' in root or root == '.'):
            if 'app' in root:
                gradle_path = os.path.join(root, 'build.gradle.kts')
                break
            else:
                gradle_path = os.path.join(root, 'build.gradle.kts')

    if not gradle_path:
        print("❌ 未找到 app/build.gradle.kts")
        return

    with open(gradle_path, 'r', encoding='utf-8') as f:
        content = f.read()

    content = re.sub(r'.*org\.jetbrains\.kotlin\.plugin\.compose.*\n?', '', content)
    plugin_line = f'    id("org.jetbrains.kotlin.plugin.compose") version "{kotlin_ver}"\n'
    if 'plugins {' in content:
        content = content.replace('plugins {', f'plugins {{\n{plugin_line}', 1)

    deps_to_add = [
        'implementation("androidx.activity:activity-compose:1.9.0")',
        'implementation("androidx.documentfile:documentfile:1.0.1")',
        'implementation("androidx.compose.material3:material3:1.2.1")',
        'implementation("androidx.compose.ui:ui:1.6.8")',
        'implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.0")'
    ]

    needed_deps = []
    for dep in deps_to_add:
        pkg_key = dep.split('"')[1].split(':')[1]
        if pkg_key not in content:
            needed_deps.append(f"    {dep}")

    if needed_deps:
        deps_block = "\n".join(needed_deps) + "\n"
        if 'dependencies {' in content:
            content = content.replace('dependencies {', f'dependencies {{\n{deps_block}', 1)
        else:
            content += f"\ndependencies {{\n{deps_block}}}\n"

    with open(gradle_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ 已成功修复并更新 Gradle 配置: {gradle_path}")

patch_build_gradle()

# 5. 更新 MainActivity.kt：包含 ViewModel 状态持久化 + 极大 I/O 提速逻辑
def update_main_activity():
    target_file = None
    for r, _, fs in os.walk('.'):
        for file in fs:
            if file == 'MainActivity.kt':
                target_file = os.path.join(r, file)
                break

    if not target_file:
        print("❌ 未找到 MainActivity.kt")
        return

    clean_kotlin_code = r'''package com.example.pdf2cbz

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
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.documentfile.provider.DocumentFile
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewmodel.compose.viewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import java.io.ByteArrayOutputStream
import java.io.FileDescriptor
import java.io.FileInputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.zip.CRC32
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

class MainViewModel : ViewModel() {
    val pdfs = mutableStateListOf<Uri>()
    var outputTree by mutableStateOf<Uri?>(null)
    var log by mutableStateOf("等待选择 PDF…")
    var isProcessing by mutableStateOf(false)
    val fullLogs = mutableStateListOf<String>()
}

class MainActivity : ComponentActivity() {
    private var mainViewModel: MainViewModel? = null

    private val pickPdfs = registerForActivityResult(
        ActivityResultContracts.OpenMultipleDocuments()
    ) { uris ->
        mainViewModel?.let { vm ->
            vm.pdfs.clear()
            vm.pdfs.addAll(uris.filter { it.toString().isNotBlank() })
        }
    }

    private val pickTree = registerForActivityResult(
        ActivityResultContracts.OpenDocumentTree()
    ) { uri ->
        if (uri != null) {
            contentResolver.takePersistableUriPermission(
                uri,
                Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION
            )
            mainViewModel?.outputTree = uri
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            val vm: MainViewModel = viewModel()
            mainViewModel = vm

            MaterialTheme {
                val scope = rememberCoroutineScope()
                var showLogDialog by remember { mutableStateOf(false) }

                Column(
                    modifier = Modifier.fillMaxSize().padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("PDF2CBZ Ultimate", style = MaterialTheme.typography.headlineSmall)
                        OutlinedButton(onClick = { showLogDialog = true }) {
                            Text("📋 日志")
                        }
                    }

                    Text("无损直出 · 多核极速 · 防切屏/拔电重置")

                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(
                            enabled = !vm.isProcessing,
                            onClick = { pickPdfs.launch(arrayOf("application/pdf")) }
                        ) { Text("选择 PDF") }

                        OutlinedButton(
                            enabled = !vm.isProcessing,
                            onClick = { pickTree.launch(null) }
                        ) { Text("输出目录") }
                    }

                    Text("已选 PDF：${vm.pdfs.size} 个")
                    Text("输出路径：${vm.outputTree ?: "未选择"}")

                    if (vm.pdfs.isNotEmpty()) {
                        LazyColumn(
                            modifier = Modifier.weight(1f),
                            verticalArrangement = Arrangement.spacedBy(6.dp)
                        ) {
                            items(vm.pdfs) { uri ->
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
                        enabled = vm.pdfs.isNotEmpty() && vm.outputTree != null && !vm.isProcessing,
                        onClick = {
                            vm.isProcessing = true
                            scope.launch(Dispatchers.IO) {
                                convertPdfsToCbz(
                                    vm = vm,
                                    onLog = { entry ->
                                        scope.launch(Dispatchers.Main) { vm.fullLogs.add(entry) }
                                    },
                                    onProgress = { status ->
                                        scope.launch(Dispatchers.Main) { vm.log = status }
                                    }
                                )
                                vm.isProcessing = false
                            }
                        }
                    ) {
                        Text(if (vm.isProcessing) "正在转换中..." else "开始转换")
                    }

                    Text(vm.log)

                    if (showLogDialog) {
                        AlertDialog(
                            onDismissRequest = { showLogDialog = false },
                            title = { Text("🛠 转换日志与调试历史") },
                            text = {
                                SelectionContainer {
                                    LazyColumn(modifier = Modifier.heightIn(max = 350.dp)) {
                                        items(vm.fullLogs) { line ->
                                            Text(line, style = MaterialTheme.typography.bodySmall)
                                        }
                                    }
                                }
                            },
                            confirmButton = {
                                Button(onClick = { showLogDialog = false }) {
                                    Text("关闭")
                                }
                            }
                        )
                    }
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

    // 极速字节对比提取 JPEG
    private fun extractRawJpegsFromPdf(pfd: FileDescriptor): List<ByteArray> {
        val images = mutableListOf<ByteArray>()
        try {
            FileInputStream(pfd).use { fis ->
                val bytes = fis.readBytes()
                val len = bytes.size
                var i = 0
                val bFF = 0xFF.toByte()
                val bD8 = 0xD8.toByte()
                val bD9 = 0xD9.toByte()

                while (i < len - 3) {
                    if (bytes[i] == bFF && bytes[i + 1] == bD8 && bytes[i + 2] == bFF) {
                        val start = i
                        var j = i + 2
                        var end = -1
                        while (j < len - 1) {
                            if (bytes[j] == bFF && bytes[j + 1] == bD9) {
                                end = j + 2
                                break
                            }
                            j++
                        }
                        if (end != -1 && (end - start) > 10000) {
                            images.add(bytes.copyOfRange(start, end))
                            i = end - 1
                        }
                    }
                    i++
                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
        return images
    }

    private fun writeZipStoredEntry(zipOut: ZipOutputStream, bytes: ByteArray, entryName: String) {
        val entry = ZipEntry(entryName)
        entry.method = ZipEntry.STORED
        entry.size = bytes.size.toLong()
        entry.compressedSize = bytes.size.toLong()
        val crc = CRC32()
        crc.update(bytes)
        entry.crc = crc.value
        zipOut.putNextEntry(entry)
        zipOut.write(bytes)
        zipOut.closeEntry()
    }

    private suspend fun convertPdfsToCbz(
        vm: MainViewModel,
        onLog: (String) -> Unit,
        onProgress: (String) -> Unit
    ) {
        val targetTreeUri = vm.outputTree ?: return
        val docDir = DocumentFile.fromTreeUri(this, targetTreeUri) ?: run {
            onProgress("无法访问输出目录")
            return
        }

        val timeStamp = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault()).format(Date())
        val logBuffer = StringBuilder("=== PDF2CBZ 运行日志 ($timeStamp) ===\n")

        val logAndProgress: (String) -> Unit = { msg ->
            val entry = "[${SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())}] $msg"
            logBuffer.append(entry).append("\n")
            onLog(entry)
            onProgress(msg)
        }

        val totalPdfs = vm.pdfs.size
        val pdfList = vm.pdfs.toList()

        pdfList.forEachIndexed { index, pdfUri ->
            val rawName = getFileName(pdfUri) ?: "document_$index.pdf"
            val baseName = rawName.substringBeforeLast(".")
            val cbzName = "$baseName.cbz"

            logAndProgress("正在处理 (${index + 1}/$totalPdfs): $rawName")

            val targetFile = docDir.createFile("application/x-cbz", cbzName)
                ?: docDir.createFile("application/zip", cbzName)

            if (targetFile == null) {
                logAndProgress("创建目标文件失败: $cbzName")
                return@forEachIndexed
            }

            try {
                var rawJpegs: List<ByteArray> = emptyList()
                contentResolver.openFileDescriptor(pdfUri, "r")?.use { pfd ->
                    rawJpegs = extractRawJpegsFromPdf(pfd.fileDescriptor)
                }

                if (rawJpegs.isNotEmpty()) {
                    logAndProgress("⚡ [无损直通] 成功提取到 ${rawJpegs.size} 张原始 JPEG 图片...")
                    contentResolver.openOutputStream(targetFile.uri)?.use { os ->
                        ZipOutputStream(os.buffered(256 * 1024)).use { zipOut ->
                            rawJpegs.forEachIndexed { imgIdx, bytes ->
                                val entryName = String.format("%04d.jpg", imgIdx + 1)
                                writeZipStoredEntry(zipOut, bytes, entryName)
                            }
                        }
                    }
                } else {
                    logAndProgress("🖼 [兼容模式] 未找到纯 JPEG 流，启用高效率渲染...")
                    contentResolver.openFileDescriptor(pdfUri, "r")?.use { pfd ->
                        PdfRenderer(pfd).use { renderer ->
                            contentResolver.openOutputStream(targetFile.uri)?.use { os ->
                                ZipOutputStream(os.buffered(256 * 1024)).use { zipOut ->
                                    val pageCount = renderer.pageCount
                                    for (i in 0 until pageCount) {
                                        if (i % 3 == 0 || i == pageCount - 1) {
                                            logAndProgress("正在转换 (${index + 1}/$totalPdfs): $rawName [页码 ${i + 1}/$pageCount]")
                                        }

                                        renderer.openPage(i).use { page ->
                                            val targetWidth = 1440f
                                            val scale = if (page.width > 0) (targetWidth / page.width).coerceIn(1.0f, 2.0f) else 1.5f
                                            val bitmap = Bitmap.createBitmap(
                                                (page.width * scale).toInt(),
                                                (page.height * scale).toInt(),
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
                                            bitmap.compress(Bitmap.CompressFormat.JPEG, 80, stream)
                                            val imageBytes = stream.toByteArray()
                                            bitmap.recycle()

                                            val entryName = String.format("%04d.jpg", i + 1)
                                            writeZipStoredEntry(zipOut, imageBytes, entryName)
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            } catch (e: Exception) {
                logAndProgress("转换失败 [$rawName]: ${e.localizedMessage}")
                return@forEachIndexed
            }
        }

        logAndProgress("转换完成！共成功处理 $totalPdfs 个文件。")

        try {
            val logFile = docDir.createFile("text/plain", "pdf2cbz_log.txt")
            if (logFile != null) {
                contentResolver.openOutputStream(logFile.uri)?.use { os ->
                    os.write(logBuffer.toString().toByteArray())
                }
            }
        } catch (_: Exception) {}
    }
}
'''
    with open(target_file, 'w', encoding='utf-8') as f:
        f.write(clean_kotlin_code)
    print(f"✅ 全局代码已成功更新: {target_file}")

update_main_activity()
