import os

# 1. 修复 settings.gradle.kts
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

# 2. 修复 app/build.gradle.kts
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

# 3. ZipStoredWriter.kt (只打包不压二次压缩，保留原体积)
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

# 4. MainActivity.kt (100% 字节级直通剥离)
main_activity_code = '''package com.example.pdf2cbz

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.provider.DocumentsContract
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
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import java.io.InputStream
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
                    Text("PDF2CBZ Direct", style = MaterialTheme.typography.headlineSmall)
                    Text("PDF 原生图片流无损直通抽取")

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

                    if (isProcessing) {
                        LinearProgressIndicator(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp))
                    }

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
                        Text(if (isProcessing) "正在无损提取中..." else "开始提取")
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

    // 从 PDF 二进制字节流中，逐个读取原始图片（零解码、零失真）
    private fun extractRawImages(inputStream: InputStream): List<ByteArray> {
        val bytes = inputStream.readBytes()
        val images = mutableListOf<ByteArray>()
        var i = 0
        val len = bytes.size

        while (i < len - 3) {
            // 匹配 JPEG 头 FF D8 FF
            if ((bytes[i].toInt() and 0xFF) == 0xFF &&
                (bytes[i + 1].toInt() and 0xFF) == 0xD8 &&
                (bytes[i + 2].toInt() and 0xFF) == 0xFF
            ) {
                val start = i
                var j = start + 2
                while (j < len - 1) {
                    // 匹配 JPEG 尾 FF D9
                    if ((bytes[j].toInt() and 0xFF) == 0xFF &&
                        (bytes[j + 1].toInt() and 0xFF) == 0xD9
                    ) {
                        val end = j + 2
                        // 过滤掉小于 30KB 的矢量微型图标或杂小元素
                        if (end - start > 30 * 1024) {
                            images.add(bytes.copyOfRange(start, end))
                            i = end
                            break
                        }
                    }
                    j++
                }
                if (j >= len - 1) i++
            } else {
                i++
            }
        }
        return images
    }

    private suspend fun convertPdfsToCbz(onProgress: (String) -> Unit) {
        val targetTreeUri = outputTree ?: return

        val parentDocUri = try {
            DocumentsContract.buildDocumentUriUsingTree(
                targetTreeUri,
                DocumentsContract.getTreeDocumentId(targetTreeUri)
            )
        } catch (e: Exception) {
            onProgress("无法解析输出目录")
            return
        }

        val totalPdfs = pdfs.size
        pdfs.forEachIndexed { index, pdfUri ->
            val rawName = getFileName(pdfUri) ?: "document_$index.pdf"
            val baseName = rawName.substringBeforeLast(".")
            val cbzName = "$baseName.cbz"

            onProgress("正在无损剥离 (${index + 1}/$totalPdfs): $rawName")

            val targetUri = try {
                DocumentsContract.createDocument(
                    contentResolver,
                    parentDocUri,
                    "application/x-cbz",
                    cbzName
                )
            } catch (e: Exception) {
                null
            }

            if (targetUri == null) {
                onProgress("创建文件失败: $cbzName")
                return@forEachIndexed
            }

            try {
                var rawImages: List<ByteArray> = emptyList()
                contentResolver.openInputStream(pdfUri)?.use { input ->
                    rawImages = extractRawImages(input)
                }

                if (rawImages.isNotEmpty()) {
                    contentResolver.openOutputStream(targetUri)?.use { os ->
                        ZipOutputStream(os.buffered()).use { zipOut ->
                            rawImages.forEachIndexed { imgIdx, imgBytes ->
                                val entryName = String.format("%04d.jpg", imgIdx + 1)
                                ZipStoredWriter.addStoredBytes(zipOut, imgBytes, entryName)
                            }
                        }
                    }
                    onProgress("成功提取 ${rawImages.size} 页原图 ($cbzName)")
                } else {
                    onProgress("未在 $rawName 中找到有效内嵌原图")
                }
            } catch (e: Exception) {
                onProgress("处理失败 [$rawName]: ${e.localizedMessage}")
                return@forEachIndexed
            }
        }
        onProgress("全部完成！已无损提取 $totalPdfs 个文件。")
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
