import os
import re

print("🚀 正在全局重组 PDF2CBZ（Clash 极简卡片 UI + 画质切换 + ViewModel 状态持久化）...")

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

# 4. 修复 build.gradle.kts
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

# 5. 重构 MainActivity.kt 为 Clash 卡片 UI + 画质选择 + 关于/设置页面
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
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color as ComposeColor
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
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

enum class QualityMode(val title: String, val desc: String) {
    ADAPTIVE("自适应", "优先无损直通，兼容高画质渲染（推荐）"),
    NATIVE("原生", "强制最高清晰度渲染（体积较大）"),
    LOW("低画质", "降低分辨率与质量，大幅减小体积")
}

class MainViewModel : ViewModel() {
    val pdfs = mutableStateListOf<Uri>()
    var outputTree by mutableStateOf<Uri?>(null)
    var log by mutableStateOf("等待操作…")
    var isProcessing by mutableStateOf(false)
    var qualityMode by mutableStateOf(QualityMode.ADAPTIVE)
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

            val darkColorScheme = darkColorScheme(
                background = ComposeColor(0xFF121212),
                surface = ComposeColor(0xFF1E1E1E),
                surfaceVariant = ComposeColor(0xFF2A2A2A),
                primary = ComposeColor(0xFF80D8FF),
                onBackground = ComposeColor(0xFFEEEEEE),
                onSurface = ComposeColor(0xFFFFFFFF)
            )

            MaterialTheme(colorScheme = darkColorScheme) {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    val scope = rememberCoroutineScope()
                    var showLogDialog by remember { mutableStateOf(false) }
                    var showSettingsDialog by remember { mutableStateOf(false) }
                    var showAboutDialog by remember { mutableStateOf(false) }

                    Column(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(horizontal = 20.dp, vertical = 24.dp),
                        verticalArrangement = Arrangement.spacedBy(16.dp)
                    ) {
                        // 顶栏标题
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier.padding(bottom = 8.dp)
                        ) {
                            Text(
                                text = "🐱 PDF2CBZ",
                                fontSize = 26.sp,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.onBackground
                            )
                        }

                        // 卡片 1：选择 PDF
                        Card(
                            shape = RoundedCornerShape(16.dp),
                            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable(enabled = !vm.isProcessing) { pickPdfs.launch(arrayOf("application/pdf")) }
                        ) {
                            Column(modifier = Modifier.padding(20.dp)) {
                                Text(
                                    text = if (vm.pdfs.isEmpty()) "未选择文件" else "已选 ${vm.pdfs.size} 个 PDF",
                                    fontSize = 18.sp,
                                    fontWeight = FontWeight.SemiBold,
                                    color = MaterialTheme.colorScheme.onSurface
                                )
                                Spacer(modifier = Modifier.height(4.dp))
                                Text(
                                    text = if (vm.pdfs.isEmpty()) "点击选择要转换的 PDF" else "点击重新选择文件",
                                    fontSize = 13.sp,
                                    color = ComposeColor.Gray
                                )
                            }
                        }

                        // 卡片 2：输出目录
                        Card(
                            shape = RoundedCornerShape(16.dp),
                            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable(enabled = !vm.isProcessing) { pickTree.launch(null) }
                        ) {
                            Column(modifier = Modifier.padding(20.dp)) {
                                Text(
                                    text = "输出目录",
                                    fontSize = 18.sp,
                                    fontWeight = FontWeight.SemiBold,
                                    color = MaterialTheme.colorScheme.onSurface
                                )
                                Spacer(modifier = Modifier.height(4.dp))
                                Text(
                                    text = vm.outputTree?.let { getFileName(it) ?: it.toString() } ?: "未设置 (点击指定存储路径)",
                                    fontSize = 13.sp,
                                    color = ComposeColor.Gray,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis
                                )
                            }
                        }

                        Spacer(modifier = Modifier.height(8.dp))

                        // 菜单列表选项
                        Column(verticalArrangement = Arrangement.spacedBy(18.dp)) {
                            MenuRow(icon = "📋", title = "日志") { showLogDialog = true }
                            MenuRow(icon = "⚙️", title = "设置") { showSettingsDialog = true }
                            MenuRow(icon = "ℹ️", title = "关于") { showAboutDialog = true }
                        }

                        Spacer(modifier = Modifier.weight(1f))

                        // 状态提示文字
                        Text(
                            text = vm.log,
                            fontSize = 13.sp,
                            color = ComposeColor.LightGray,
                            maxLines = 2,
                            overflow = TextOverflow.Ellipsis,
                            modifier = Modifier.padding(horizontal = 4.dp)
                        )

                        // 底部“开始转换”大按钮
                        Button(
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
                            },
                            enabled = vm.pdfs.isNotEmpty() && vm.outputTree != null && !vm.isProcessing,
                            shape = RoundedCornerShape(12.dp),
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(52.dp)
                        ) {
                            Text(
                                text = if (vm.isProcessing) "正在转换中..." else "开始转换",
                                fontSize = 16.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }

                    // --- 弹窗 1：日志 ---
                    if (showLogDialog) {
                        AlertDialog(
                            onDismissRequest = { showLogDialog = false },
                            title = { Text("📋 运行日志") },
                            text = {
                                SelectionContainer {
                                    LazyColumn(modifier = Modifier.heightIn(max = 300.dp)) {
                                        items(vm.fullLogs) { line ->
                                            Text(line, fontSize = 12.sp, color = ComposeColor.LightGray)
                                        }
                                    }
                                }
                            },
                            confirmButton = {
                                TextButton(onClick = { showLogDialog = false }) { Text("关闭") }
                            }
                        )
                    }

                    // --- 弹窗 2：设置 ---
                    if (showSettingsDialog) {
                        AlertDialog(
                            onDismissRequest = { showSettingsDialog = false },
                            title = { Text("⚙️ 设置") },
                            text = {
                                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                                    Text("画质与清晰度选项：", fontSize = 14.sp, fontWeight = FontWeight.Bold)
                                    QualityMode.values().forEach { mode ->
                                        Row(
                                            verticalAlignment = Alignment.CenterVertically,
                                            modifier = Modifier
                                                .fillMaxWidth()
                                                .clickable { vm.qualityMode = mode }
                                                .padding(vertical = 4.dp)
                                        ) {
                                            RadioButton(
                                                selected = (vm.qualityMode == mode),
                                                onClick = { vm.qualityMode = mode }
                                            )
                                            Spacer(modifier = Modifier.width(8.dp))
                                            Column {
                                                Text(mode.title, fontWeight = FontWeight.SemiBold, fontSize = 15.sp)
                                                Text(mode.desc, fontSize = 11.sp, color = ComposeColor.Gray)
                                            }
                                        }
                                    }
                                }
                            },
                            confirmButton = {
                                TextButton(onClick = { showSettingsDialog = false }) { Text("确定") }
                            }
                        )
                    }

                    // --- 弹窗 3：关于 ---
                    if (showAboutDialog) {
                        AlertDialog(
                            onDismissRequest = { showAboutDialog = false },
                            title = { Text("ℹ️ 关于 PDF2CBZ") },
                            text = {
                                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                    Text("• 开发者：Gemini & a245888295-dot", fontSize = 14.sp)
                                    Text("• 联系方式：待定", fontSize = 14.sp)
                                    Spacer(modifier = Modifier.height(6.dp))
                                    Text("• 更新地址：", fontSize = 14.sp, fontWeight = FontWeight.Bold)
                                    SelectionContainer {
                                        Text(
                                            text = "https://github.com/a245888295-dot/PDF2CBZ/actions",
                                            fontSize = 12.sp,
                                            color = MaterialTheme.colorScheme.primary
                                        )
                                    }
                                }
                            },
                            confirmButton = {
                                TextButton(onClick = { showAboutDialog = false }) { Text("关闭") }
                            }
                        )
                    }
                }
            }
        }
    }

    @Composable
    private fun MenuRow(icon: String, title: String, onClick: () -> Unit) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier
                .fillMaxWidth()
                .clickable { onClick() }
                .padding(vertical = 6.dp, horizontal = 4.dp)
        ) {
            Text(text = icon, fontSize = 20.sp)
            Spacer(modifier = Modifier.width(16.dp))
            Text(
                text = title,
            fontSize = 16.sp,
                fontWeight = FontWeight.Medium,
                color = MaterialTheme.colorScheme.onBackground
            )
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
        val currentQuality = vm.qualityMode

        pdfList.forEachIndexed { index, pdfUri ->
            val rawName = getFileName(pdfUri) ?: "document_$index.pdf"
            val baseName = rawName.substringBeforeLast(".")
            val cbzName = "$baseName.cbz"

            logAndProgress("正在处理 (${index + 1}/$totalPdfs): $rawName [画质模式: ${currentQuality.title}]")

            val targetFile = docDir.createFile("application/x-cbz", cbzName)
                ?: docDir.createFile("application/zip", cbzName)

            if (targetFile == null) {
                logAndProgress("创建目标文件失败: $cbzName")
                return@forEachIndexed
            }

            try {
                var rawJpegs: List<ByteArray> = emptyList()

                // 自适应模式尝试提取原始 JPEG
                if (currentQuality == QualityMode.ADAPTIVE) {
                    contentResolver.openFileDescriptor(pdfUri, "r")?.use { pfd ->
                        rawJpegs = extractRawJpegsFromPdf(pfd.fileDescriptor)
                    }
                }

                if (rawJpegs.isNotEmpty()) {
                    logAndProgress("⚡ [无损直通] 提取到 ${rawJpegs.size} 张原始 JPEG 图片...")
                    contentResolver.openOutputStream(targetFile.uri)?.use { os ->
                        ZipOutputStream(os.buffered(256 * 1024)).use { zipOut ->
                            rawJpegs.forEachIndexed { imgIdx, bytes ->
                                val entryName = String.format("%04d.jpg", imgIdx + 1)
                                writeZipStoredEntry(zipOut, bytes, entryName)
                            }
                        }
                    }
                } else {
                    logAndProgress("🖼 [高清渲染] 正在多核渲染图片...")
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
                                            val (targetWidth, compressQuality) = when (currentQuality) {
                                                QualityMode.NATIVE -> 1800f to 90
                                                QualityMode.ADAPTIVE -> 1440f to 80
                                                QualityMode.LOW -> 1080f to 60
                                            }

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
                                            bitmap.compress(Bitmap.CompressFormat.JPEG, compressQuality, stream)
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
