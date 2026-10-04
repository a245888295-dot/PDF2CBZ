import os

# 1. 修复 AndroidManifest.xml（防屏幕旋转重置 App 状态）
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
            print(f"[Patch] Fixed AndroidManifest.xml configChanges")

# 2. 修复 settings.gradle.kts
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

# 3. 修复 app/build.gradle.kts
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

# 4. ZipStoredWriter.kt
zip_writer_code = '''package com.example.pdf2cbz

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

# 5. MainActivity.kt（全功能日志监控 + 0字节防创 + SAF路径精准解耦）
main_activity_code = '''package com.example.pdf2cbz

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.provider.DocumentsContract
import android.provider.OpenableColumns
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import java.io.InputStream
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

                // 自动滚动日志到底部
                LaunchedEffect(logs.size) {
                    if (logs.isNotEmpty()) {
                        logListState.animateScrollToItem(logs.size - 1)
                    }
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
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.surfaceVariant
                        ),
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
                        Text(if (isProcessing) "正在无损提取中..." else "开始提取")
                    }

                    // 日志控制台 header
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
                        ) {
                            Text("一键复制日志")
                        }
                    }

                    // 实时日志卡片
                    Card(
                        modifier = Modifier.weight(1f).fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = Color(0xFF1E1E1E))
                    ) {
                        LazyColumn(
                            state = logListState,
                            modifier = Modifier.padding(8.dp).fillMaxSize()
                        ) {
                            items(logs) { log ->
                                Text(
                                    text = log,
                                    color = Color(0xFF00FF66),
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
        if (hasPermission) {
            outputTree = uri
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

    private fun extractRawImages(inputStream: InputStream, logAction: (String) -> Unit): List<ByteArray> {
        val bytes = inputStream.readBytes()
        val images = mutableListOf<ByteArray>()
        var i = 0
        val len = bytes.size

        logAction("读取 PDF 文件大小: ${len / 1024} KB")

        var foundHeaderCount = 0
        var filteredSmallCount = 0

        while (i < len - 3) {
            // 匹配 JPEG 帧头 FF D8 FF
            if ((bytes[i].toInt() and 0xFF) == 0xFF &&
                (bytes[i + 1].toInt() and 0xFF) == 0xD8 &&
                (bytes[i + 2].toInt() and 0xFF) == 0xFF
            ) {
                foundHeaderCount++
                val start = i
                var j = start + 2
                while (j < len - 1) {
                    // 匹配 JPEG 帧尾 FF D9
                    if ((bytes[j].toInt() and 0xFF) == 0xFF &&
                        (bytes[j + 1].toInt() and 0xFF) == 0xD9
                    ) {
                        val end = j + 2
                        val sizeKB = (end - start) / 1024
                        if (sizeKB > 30) {
                            images.add(bytes.copyOfRange(start, end))
                            i = end
                            break
                        } else {
                            filteredSmallCount++
                        }
                    }
                    j++
                }
                if (j >= len - 1) i++
            } else {
                i++
            }
        }

        logAction("扫描结果: 发现 $foundHeaderCount 个JPEG头，过滤微图 $filteredSmallCount 个，匹配有效原图 ${images.size} 张")
        return images
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

            // 1. 先提取图片字节（零解码）
            var rawImages: List<ByteArray> = emptyList()
            try {
                contentResolver.openInputStream(pdfUri)?.use { input ->
                    rawImages = extractRawImages(input) { log -> appendLog(log) }
                }
            } catch (e: Exception) {
                appendLog("❌ 读取 PDF 异常: ${e.localizedMessage}")
            }

            // 2. 检查：如果提取到的原图为空，绝对不创建目标文件（防生成 0 字节空壳）
            if (rawImages.isEmpty()) {
                appendLog("⚠️ 提取失败: 未找到有效内嵌 JPEG（可能是 Flate/JP2 压缩或 PDF 1.5+ 对象流）")
                return@forEachIndexed
            }

            // 3. 确认拿到原图后再创建目标 CBZ 文件
            val targetUri = try {
                DocumentsContract.createDocument(
                    contentResolver,
                    parentDocUri,
                    "application/x-cbz",
                    cbzName
                )
            } catch (e: Exception) {
                appendLog("❌ 创建文件失败: $cbzName (${e.localizedMessage})")
                null
            } ?: return@forEachIndexed

            // 4. 打包写入
            try {
                contentResolver.openOutputStream(targetUri)?.use { os ->
                    ZipOutputStream(os.buffered()).use { zipOut ->
                        rawImages.forEachIndexed { imgIdx, imgBytes ->
                            val entryName = String.format("%04d.jpg", imgIdx + 1)
                            ZipStoredWriter.addStoredBytes(zipOut, imgBytes, entryName)
                        }
                    }
                }
                appendLog("✅ 成功生成 $cbzName (共 ${rawImages.size} 页)")
            } catch (e: Exception) {
                appendLog("❌ 打包写入失败: ${e.localizedMessage}")
            }
        }
        appendLog("----------------------------------------")
        appendLog("🎉 全部任务处理完成！")
    }
}
'''

for r, _, fs in os.walk('.'):
    for file in fs:
        fp = os.path.join(r, file)
        if file == 'MainActivity.kt':
            with open(fp, 'w', encoding='utf-8') as f:
                f.write(main_activity_code)
            print(f"[Patch] Overwritten {fp}")
        elif file == 'ZipStoredWriter.kt':
            with open(fp, 'w', encoding='utf-8') as f:
                f.write(zip_writer_code)
            print(f"[Patch] Overwritten {fp}")
