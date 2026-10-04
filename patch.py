import os
import zipfile
import shutil

# ==================== 配置区 ====================
SOURCE_ZIP_NAME = "source.zip"  # 改成你的源 zip 文件名
BACKUP_SUFFIX = ".old"          # 旧 zip 的备份后缀
# ================================================

# 1. 全量覆盖所有文件（所有历史更新合并版）
print(">>> 步骤1: 全量覆盖项目文件...")

# --- 1.1 修复 AndroidManifest.xml ---
for r, _, fs in os.walk('.'):
    for file in fs:
        if file == 'AndroidManifest.xml':
            p = os.path.join(r, file)
            with open(p, 'r+', encoding='utf-8') as f:
                c = f.read()
                if 'android:configChanges' not in c:
                    c = c.replace(
                        '<activity',
                        '<activity\n            android:configChanges="orientation|screenSize|keyboardHidden|screenLayout|smallestScreenSize"'
                    )
                    f.seek(0); f.write(c); f.truncate()
            print(f"[Patch] AndroidManifest.xml 已更新")

# --- 1.2 修复 settings.gradle.kts ---
for r, _, fs in os.walk('.'):
    for file in fs:
        if file == 'settings.gradle.kts':
            p = os.path.join(r, file)
            with open(p, 'r+', encoding='utf-8') as f:
                c = f.read()
                if 'org.jetbrains.kotlin.plugin.compose' not in c and 'pluginManagement {' in c:
                    c = c.replace(
                        'pluginManagement {',
                        'pluginManagement {\nplugins {\n id("org.jetbrains.kotlin.android") version "2.0.0"\n id("org.jetbrains.kotlin.plugin.compose") version "2.0.0"\n}\n'
                    )
                    f.seek(0); f.write(c); f.truncate()
            print(f"[Patch] settings.gradle.kts 已更新")

# --- 1.3 修复 app/build.gradle.kts ---
for r, _, fs in os.walk('.'):
    for file in fs:
        if file in ['build.gradle.kts', 'build.gradle'] and 'app' in r:
            p = os.path.join(r, file)
            with open(p, 'r+', encoding='utf-8') as f:
                c = f.read().replace('JavaVersion.VERSION_1_8', 'JavaVersion.VERSION_17').replace('jvmTarget = "1.8"', 'jvmTarget = "17"')
                if 'compose = true' not in c and 'android {' in c:
                    c = c.replace('android {', 'android {\n    buildFeatures { compose = true }')
                if 'dependencies {' in c:
                    deps = '''dependencies {
    implementation("androidx.documentfile:documentfile:1.0.1")
    implementation("androidx.activity:activity-compose:1.9.0")
    implementation("androidx.compose.ui:ui:1.6.8")
    implementation("androidx.compose.material3:material3:1.2.1")'''
                    if 'documentfile' not in c and 'activity-compose' not in c:
                        c = c.replace('dependencies {', deps)
                    elif 'documentfile' not in c:
                        c = c.replace('dependencies {', 'dependencies {\n    implementation("androidx.documentfile:documentfile:1.0.1")')
                f.seek(0); f.write(c); f.truncate()
            print(f"[Patch] build.gradle.kts 已更新")

# --- 1.4 写入 ZipStoredWriter.kt ---
zip_writer_code = r'''package com.example.pdf2cbz

import java.util.zip.CRC32
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

object ZipStoredWriter {
    fun addStoredBytes(zip: ZipOutputStream, bytes: ByteArray, name: String) {
        val crc = CRC32().apply { update(bytes, 0, bytes.size) }
        val entry = ZipEntry(name).apply {
            method = ZipEntry.STORED
            size = bytes.size.toLong()
            compressedSize = bytes.size.toLong()
            this.crc = crc.value
        }
        zip.putNextEntry(entry)
        zip.write(bytes)
        zip.closeEntry()
    }
}
'''

# --- 1.5 写入 MainActivity.kt（完整版，含原生提取 + 兜底渲染） ---
main_activity_code = r'''package com.example.pdf2cbz

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.pdf.PdfRenderer
import android.net.Uri
import android.os.Bundle
import android.provider.DocumentsContract
import android.provider.OpenableColumns
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color as ComposeColor
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import java.io.ByteArrayOutputStream
import java.io.InputStream
import java.util.zip.Inflater
import java.util.zip.ZipOutputStream

class MainActivity : ComponentActivity() {
    private val pdfs = mutableStateListOf<Uri>()
    private var outputTree by mutableStateOf<Uri?>(null)
    private val logs = mutableStateListOf<String>()

    private val pickPdfs = registerForActivityResult(
        ActivityResultContracts.OpenMultipleDocuments()
    ) { uris ->
        pdfs.clear()
        pdfs.addAll(uris.filter { it.toString().isNotBlank() })
        appendLog("已选择 ${pdfs.size} 个 PDF 文件")
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
            saveOutputTreeUri(uri)
            appendLog("输出目录已更改为: ${getFriendlyPath(uri)}")
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        restoreOutputTreeUri()
        appendLog("App 启动完成，就绪中…")

        setContent {
            MaterialTheme {
                val context = LocalContext.current
                val scope = rememberCoroutineScope()
                var isProcessing by remember { mutableStateOf(false) }
                val logListState = rememberLazyListState()

                LaunchedEffect(logs.size) {
                    if (logs.isNotEmpty()) logListState.animateScrollToItem(logs.size - 1)
                }

                Column(
                    modifier = Modifier.fillMaxSize().padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Text("PDF2CBZ Direct", style = MaterialTheme.typography.headlineSmall)

                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(
                            enabled = !isProcessing,
                            onClick = { pickPdfs.launch(arrayOf("application/pdf")) }
                        ) { Text("选择 PDF") }

                        OutlinedButton(
                            enabled = !isProcessing,
                            onClick = {
                                val initialUri = outputTree?.let { uri ->
                                    try {
                                        val docId = DocumentsContract.getTreeDocumentId(uri)
                                        DocumentsContract.buildDocumentUriUsingTree(uri, docId)
                                    } catch (e: Exception) { uri }
                                }
                                pickTree.launch(initialUri)
                            }
                        ) { Text("更改输出目录") }
                    }

                    Card(
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.padding(10.dp)) {
                            Text("已选 PDF：${pdfs.size} 个", style = MaterialTheme.typography.bodyMedium)
                            Text(
                                "输出目录：${outputTree?.let { getFriendlyPath(it) } ?: "未指定"}",
                                style = MaterialTheme.typography.bodySmall
                            )
                        }
                    }

                    if (isProcessing) {
                        LinearProgressIndicator(modifier = Modifier.fillMaxWidth().padding(vertical = 2.dp))
                    }

                    Button(
                        modifier = Modifier.fillMaxWidth(),
                        enabled = pdfs.isNotEmpty() && outputTree != null && !isProcessing,
                        onClick = {
                            isProcessing = true
                            scope.launch(Dispatchers.IO) {
                                convertPdfsToCbz()
                                isProcessing = false
                            }
                        }
                    ) {
                        Text(if (isProcessing) "正在深度无损解包中..." else "开始提取")
                    }

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("运行日志监控", style = MaterialTheme.typography.titleMedium)
                        TextButton(
                            onClick = {
                                val allLogs = logs.joinToString("\n")
                                val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                                clipboard.setPrimaryClip(ClipData.newPlainText("PDF2CBZ Logs", allLogs))
                                Toast.makeText(context, "日志已复制到剪贴板", Toast.LENGTH_SHORT).show()
                            }
                        ) { Text("一键复制日志") }
                    }

                    Card(
                        modifier = Modifier.weight(1f).fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = ComposeColor(0xFF1E1E1E))
                    ) {
                        LazyColumn(
                            state = logListState,
                            modifier = Modifier.padding(8.dp).fillMaxSize()
                        ) {
                            items(logs) { log ->
                                Text(
                                    text = log,
                                    color = ComposeColor(0xFF00FF66),
                                    fontSize = 12.sp,
                                    fontFamily = FontFamily.Monospace,
                                    modifier = Modifier.padding(vertical = 2.dp)
                                )
                            }
                        }
                    }
                }
            }
        }
    }

    private fun appendLog(msg: String) {
        runOnUiThread {
            logs.add("[${System.currentTimeMillis() % 100000 / 1000}s] $msg")
        }
    }

    private fun getFriendlyPath(uri: Uri): String {
        val decoded = Uri.decode(uri.toString())
        return when {
            decoded.contains("/tree/primary:") -> "内部存储/" + decoded.substringAfter("/tree/primary:")
            decoded.contains("/tree/") -> {
                val path = decoded.substringAfter("/tree/")
                if (path.contains(":")) "SD卡/" + path.substringAfter(":") else path
            }
            else -> decoded
        }
    }

    private fun saveOutputTreeUri(uri: Uri) {
        val sp = getSharedPreferences("pdf2cbz_prefs", Context.MODE_PRIVATE)
        sp.edit().putString("saved_output_tree", uri.toString()).apply()
    }

    private fun restoreOutputTreeUri() {
        val sp = getSharedPreferences("pdf2cbz_prefs", Context.MODE_PRIVATE)
        val uriStr = sp.getString("saved_output_tree", null) ?: return
        val uri = Uri.parse(uriStr)
        val hasPermission = contentResolver.persistedUriPermissions.any {
            it.uri == uri && it.isWritePermission
        }
        if (hasPermission) outputTree = uri
    }

    private fun getFileName(uri: Uri): String? {
        var name: String? = null
        contentResolver.query(uri, null, null, null, null)?.use { cursor ->
            val nameIndex = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if (nameIndex != -1 && cursor.moveToFirst()) name = cursor.getString(nameIndex)
        }
        return name
    }

    private fun indexOfBytes(source: ByteArray, target: ByteArray, start: Int): Int {
        if (target.isEmpty() || start >= source.size) return -1
        for (i in start..source.size - target.size) {
            var match = true
            for (j in target.indices) {
                if (source[i + j] != target[j]) { match = false; break }
            }
            if (match) return i
        }
        return -1
    }

    private fun findJpegsInBytes(bytes: ByteArray): List<ByteArray> {
        val list = mutableListOf<ByteArray>()
        var i = 0
        val len = bytes.size
        while (i < len - 3) {
            if ((bytes[i].toInt() and 0xFF) == 0xFF &&
                (bytes[i + 1].toInt() and 0xFF) == 0xD8 &&
                (bytes[i + 2].toInt() and 0xFF) == 0xFF
            ) {
                val start = i
                var j = start + 2
                while (j < len - 1) {
                    if ((bytes[j].toInt() and 0xFF) == 0xFF &&
                        (bytes[j + 1].toInt() and 0xFF) == 0xD9
                    ) {
                        val end = j + 2
                        if ((end - start) / 1024 > 30) {
                            list.add(bytes.copyOfRange(start, end))
                            i = end
                            break
                        }
                    }
                    j++
                }
                if (j >= len - 1) i++
            } else i++
        }
        return list
    }

    private fun tryDecompressFlate(data: ByteArray): ByteArray? {
        return try {
            val inflater = Inflater()
            inflater.setInput(data)
            val outputStream = ByteArrayOutputStream(data.size * 2)
            val buffer = ByteArray(4096)
            while (!inflater.finished() && !inflater.needsInput()) {
                val count = inflater.inflate(buffer)
                if (count > 0) outputStream.write(buffer, 0, count) else break
            }
            inflater.end()
            val result = outputStream.toByteArray()
            if (result.isNotEmpty()) result else null
        } catch (e: Exception) {
            try {
                val inflater = Inflater(true)
                inflater.setInput(data)
                val outputStream = ByteArrayOutputStream(data.size * 2)
                val buffer = ByteArray(4096)
                while (!inflater.finished() && !inflater.needsInput()) {
                    val count = inflater.inflate(buffer)
                    if (count > 0) outputStream.write(buffer, 0, count) else break
                }
                inflater.end()
                val result = outputStream.toByteArray()
                if (result.isNotEmpty()) result else null
            } catch (e2: Exception) { null }
        }
    }

    private fun extractLosslessNativeImages(inputStream: InputStream, logAction: (String) -> Unit): List<ByteArray> {
        val bytes = inputStream.readBytes()
        val len = bytes.size
        logAction("读取 PDF 文件大小: ${len / 1024} KB")

        val directImages = findJpegsInBytes(bytes)
        if (directImages.isNotEmpty()) {
            logAction("直出匹配成功：找到 ${directImages.size} 张裸流 JPEG 原图")
            return directImages
        }

        logAction("开启 PDF 深度数据流解包 (Flate/Zlib 解压)...")
        val streamMarker = "stream".toByteArray(Charsets.US_ASCII)
        val endStreamMarker = "endstream".toByteArray(Charsets.US_ASCII)
        val images = mutableListOf<ByteArray>()

        var pos = 0
        var streamCount = 0
        var decompressedCount = 0

        while (pos < len) {
            val streamIdx = indexOfBytes(bytes, streamMarker, pos)
            if (streamIdx == -1) break

            var start = streamIdx + streamMarker.size
            if (start < len && bytes[start] == '\r'.code.toByte()) start++
            if (start < len && bytes[start] == '\n'.code.toByte()) start++

            val endIdx = indexOfBytes(bytes, endStreamMarker, start)
            if (endIdx == -1) break

            var end = endIdx
            if (end > start && bytes[end - 1] == '\n'.code.toByte()) end--
            if (end > start && bytes[end - 1] == '\r'.code.toByte()) end--

            if (end > start) {
                streamCount++
                val streamData = bytes.copyOfRange(start, end)
                val decompressed = tryDecompressFlate(streamData)
                val targetData = decompressed ?: streamData
                if (decompressed != null) decompressedCount++
                images.addAll(findJpegsInBytes(targetData))
            }
            pos = endIdx + endStreamMarker.size
        }

        logAction("已定位 $streamCount 个数据流，解压 $decompressedCount 个 Flate 块，提取原图 ${images.size} 张")
        return images
    }

    private fun renderPdfFallback(pdfUri: Uri, outputStream: java.io.OutputStream, logAction: (String) -> Unit) {
        try {
            contentResolver.openFileDescriptor(pdfUri, "r")?.use { pfd ->
                val renderer = PdfRenderer(pfd)
                val pageCount = renderer.pageCount
                logAction("开始逐页渲染，共 $pageCount 页...")

                ZipOutputStream(outputStream.buffered()).use { zipOut ->
                    for (i in 0 until pageCount) {
                        val page = renderer.openPage(i)
                        val width = (page.width * 1.5f).toInt()
                        val height = (page.height * 1.5f).toInt()

                        val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
                        bitmap.eraseColor(Color.WHITE)
                        page.render(bitmap, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)

                        val baos = ByteArrayOutputStream()
                        bitmap.compress(Bitmap.CompressFormat.JPEG, 95, baos)

                        val entryName = String.format("%04d.jpg", i + 1)
                        ZipStoredWriter.addStoredBytes(zipOut, baos.toByteArray(), entryName)

                        bitmap.recycle()
                        page.close()

                        if (i % 5 == 0 || i == pageCount - 1) {
                            logAction("已渲染 ${i + 1}/$pageCount 页")
                        }
                    }
                }
                renderer.close()
            }
        } catch (e: Exception) {
            logAction("❌ 渲染过程异常: ${e.localizedMessage}")
            throw e
        }
    }

    private suspend fun convertPdfsToCbz() {
        val targetTreeUri = outputTree ?: return
        val parentDocUri = try {
            DocumentsContract.buildDocumentUriUsingTree(
                targetTreeUri,
                DocumentsContract.getTreeDocumentId(targetTreeUri)
            )
        } catch (e: Exception) {
            appendLog("❌ 无法解析输出目录: ${e.localizedMessage}")
            return
        }

        val totalPdfs = pdfs.size
        pdfs.forEachIndexed { index, pdfUri ->
            val rawName = getFileName(pdfUri) ?: "document_$index.pdf"
            val baseName = rawName.substringBeforeLast(".")
            val cbzName = "$baseName.cbz"

            appendLog("----------------------------------------")
            appendLog("开始处理 (${index + 1}/$totalPdfs): $rawName")

            var rawImages: List<ByteArray> = emptyList()
            try {
                contentResolver.openInputStream(pdfUri)?.use { input ->
                    rawImages = extractLosslessNativeImages(input) { log -> appendLog(log) }
                }
            } catch (e: Exception) {
                appendLog("❌ 读取 PDF 异常: ${e.localizedMessage}")
            }

            if (rawImages.isEmpty()) {
                appendLog("⚠️ 原生流提取失败，自动切换至兜底渲染模式...")
                val targetUri = try {
                    DocumentsContract.createDocument(contentResolver, parentDocUri, "application/x-cbz", cbzName)
                } catch (e: Exception) { null }

                if (targetUri != null) {
                    try {
                        contentResolver.openOutputStream(targetUri)?.use { os ->
                            renderPdfFallback(pdfUri, os) { log -> appendLog(log) }
                        }
                        appendLog("✅ 成功生成 $cbzName (兜底渲染完成)")
                    } catch (e: Exception) {
                        appendLog("❌ 兜底渲染失败: ${e.localizedMessage}")
                    }
                }
                return@forEachIndexed
            }

            val targetUri = try {
                DocumentsContract.createDocument(
                    contentResolver, parentDocUri, "application/x-cbz", cbzName
                )
            } catch (e: Exception) {
                appendLog("❌ 创建文件失败: $cbzName (${e.localizedMessage})")
                null
            } ?: return@forEachIndexed

            try {
                contentResolver.openOutputStream(targetUri)?.use { os ->
                    ZipOutputStream(os.buffered()).use { zipOut ->
                        rawImages.forEachIndexed { imgIdx, imgBytes ->
                            ZipStoredWriter.addStoredBytes(zipOut, imgBytes, String.format("%04d.jpg", imgIdx + 1))
                        }
                    }
                }
                appendLog("✅ 成功生成 $cbzName (共 ${rawImages.size} 页，100% 字节无损存储！)")
            } catch (e: Exception) {
                appendLog("❌ 打包写入失败: ${e.localizedMessage}")
            }
        }
        appendLog("----------------------------------------")
        appendLog("🎉 全部任务处理完成！")
    }
}
'''

# 写入文件
for r, _, fs in os.walk('.'):
    for file in fs:
        fp = os.path.join(r, file)
        if file == 'MainActivity.kt':
            with open(fp, 'w', encoding='utf-8') as f:
                f.write(main_activity_code)
            print(f"[Patch] MainActivity.kt 已写入")
        elif file == 'ZipStoredWriter.kt':
            with open(fp, 'w', encoding='utf-8') as f:
                f.write(zip_writer_code)
            print(f"[Patch] ZipStoredWriter.kt 已写入")

# ==================== 步骤2: 把更新后的项目重新打包成 zip ====================
print("\n>>> 步骤2: 正在把更新后的项目重新打包成源 zip...")

if os.path.exists(SOURCE_ZIP_NAME):
    # 备份旧 zip
    backup_name = SOURCE_ZIP_NAME + BACKUP_SUFFIX
    if os.path.exists(backup_name):
        os.remove(backup_name)
    shutil.move(SOURCE_ZIP_NAME, backup_name)
    print(f"[Zip] 旧源 zip 已备份为: {backup_name}")

# 重新打包当前项目（排除临时构建产物和旧 zip）
exclude_dirs = {'.gradle', 'build', '.idea', 'app/build', '.git'}
exclude_files = {SOURCE_ZIP_NAME, SOURCE_ZIP_NAME + BACKUP_SUFFIX}

with zipfile.ZipFile(SOURCE_ZIP_NAME, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk('.'):
        # 过滤目录
        dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith('.')]
        for file in files:
            if file in exclude_files:
                continue
            file_path = os.path.join(root, file)
            arcname = os.path.relpath(file_path, '.')
            zf.write(file_path, arcname)

print(f"[Zip] 新的源 zip 已生成: {SOURCE_ZIP_NAME}")
print("\n✅ 全部完成！下次编译时，源 zip 已经是最新版，")
print("   以后你可以只用几十行的增量补丁来更新了。")
