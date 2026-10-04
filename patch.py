import os

print("🚀 正在全局重组 PDF2CBZ（自动清洗 Gradle 报错插件 + 更新 MainActivity.kt）...")

# 1. 自动清洗 build.gradle.kts 中引发报错的 compose 插件
def clean_gradle_plugins():
    for r, _, fs in os.walk('.'):
        for file in fs:
            if file.endswith('.gradle.kts'):
                fp = os.path.join(r, file)
                try:
                    with open(fp, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    # 过滤掉引发 Plugin not found 错误的这一行
                    cleaned_lines = [
                        line for line in lines 
                        if 'org.jetbrains.kotlin.plugin.compose' not in line
                    ]

                    if len(cleaned_lines) != len(lines):
                        with open(fp, 'w', encoding='utf-8') as f:
                            f.writelines(cleaned_lines)
                        print(f"✅ 已成功清除报错插件行: {fp}")
                except Exception as e:
                    print(f"⚠ 清洗 Gradle 遇到问题: {e}")

clean_gradle_plugins()

# 2. 写入包含无损直出与日志功能的完整 MainActivity.kt
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
                var showLogDialog by remember { mutableStateOf(false) }
                val fullLogs = remember { mutableStateListOf<String>() }

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

                    Text("无损直出 · 体积优化 · 零 NDK 依赖")

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
                                convertPdfsToCbz(
                                    onLog = { entry ->
                                        scope.launch(Dispatchers.Main) { fullLogs.add(entry) }
                                    },
                                    onProgress = { status ->
                                        scope.launch(Dispatchers.Main) { log = status }
                                    }
                                )
                                isProcessing = false
                            }
                        }
                    ) {
                        Text(if (isProcessing) "正在转换中..." else "开始转换")
                    }

                    Text(log)

                    if (showLogDialog) {
                        AlertDialog(
                            onDismissRequest = { showLogDialog = false },
                            title = { Text("🛠 转换日志与调试历史") },
                            text = {
                                SelectionContainer {
                                    LazyColumn(modifier = Modifier.heightIn(max = 350.dp)) {
                                        items(fullLogs) { line ->
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

    private fun extractRawJpegsFromPdf(pfd: FileDescriptor): List<ByteArray> {
        val images = mutableListOf<ByteArray>()
        try {
            FileInputStream(pfd).use { fis ->
                val bytes = fis.readBytes()
                var i = 0
                val len = bytes.size
                while (i < len - 3) {
                    if ((bytes[i].toInt() and 0xFF) == 0xFF &&
                        (bytes[i + 1].toInt() and 0xFF) == 0xD8 &&
                        (bytes[i + 2].toInt() and 0xFF) == 0xFF) {
                        val start = i
                        var j = i + 2
                        var end = -1
                        while (j < len - 1) {
                            if ((bytes[j].toInt() and 0xFF) == 0xFF &&
                                (bytes[j + 1].toInt() and 0xFF) == 0xD9) {
                                end = j + 2
                                break
                            }
                            j++
                        }
                        if (end != -1 && (end - start) > 15000) {
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

    private suspend fun convertPdfsToCbz(
        onLog: (String) -> Unit,
        onProgress: (String) -> Unit
    ) {
        val targetTreeUri = outputTree ?: return
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

        val totalPdfs = pdfs.size
        pdfs.forEachIndexed { index, pdfUri ->
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
                        ZipOutputStream(os.buffered()).use { zipOut ->
                            rawJpegs.forEachIndexed { imgIdx, bytes ->
                                val entryName = String.format("%04d.jpg", imgIdx + 1)
                                ZipStoredWriter.addStoredBytes(zipOut, bytes, entryName)
                            }
                        }
                    }
                } else {
                    logAndProgress("🖼 [兼容模式] 未找到纯 JPEG 流，启用标准渲染...")
                    contentResolver.openFileDescriptor(pdfUri, "r")?.use { pfd ->
                        PdfRenderer(pfd).use { renderer ->
                            contentResolver.openOutputStream(targetFile.uri)?.use { os ->
                                ZipOutputStream(os.buffered()).use { zipOut ->
                                    val pageCount = renderer.pageCount
                                    for (i in 0 until pageCount) {
                                        logAndProgress("正在转换 (${index + 1}/$totalPdfs): $rawName [页码 ${i + 1}/$pageCount]")

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
                                            ZipStoredWriter.addStoredBytes(zipOut, imageBytes, entryName)
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
            logFile?.uri?.let { uri ->
                contentResolver.openOutputStream(uri)?.use { os ->
                    os.write(logBuffer.toString().toByteArray())
                }
            }
        } catch (_: Exception) {}
    }
}

object ZipStoredWriter {
    fun addStoredBytes(zipOut: ZipOutputStream, bytes: ByteArray, entryName: String) {
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
}
'''
    with open(target_file, 'w', encoding='utf-8') as f:
        f.write(clean_kotlin_code)
    print(f"✅ 全局代码已成功更新: {target_file}")

update_main_activity()
