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
        'implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.0")',
        'implementation("com.tom-roush:pdfbox-android:2.0.27.0")'
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
import androidx.activity.result.contract.ActivityResultContract
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.foundation.verticalScroll
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
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
import com.tom_roush.pdfbox.pdmodel.PDDocument
import com.tom_roush.pdfbox.pdmodel.graphics.image.PDImageXObject

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

/**
 * v3.3 DSH: 自定义「选择 PDF」契约。
 * 标准 OpenMultipleDocuments 的 createIntent 是 final override,无法注入初始目录,
 * 于是它永远跟随系统 DocumentsUI 的「上次位置」—— 表现为「选 PDF」和「选输出目录」
 * 两个选择器互相带跑(用户反馈的"绑定在一起")。这里自己实现以支持指定打开位置。
 */
private class PickPdfsContract : ActivityResultContract<Uri?, List<Uri>>() {
    override fun createIntent(context: Context, input: Uri?): Intent {
        return Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = "application/pdf"
            putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true)
            putExtra(Intent.EXTRA_MIME_TYPES, arrayOf("application/pdf"))
            if (input != null) {
                // 传上次选中的 PDF 文件 URI,选择器会定位到它所在目录并选中它
                putExtra("android.provider.extra.INITIAL_URI", input)
            }
        }
    }

    override fun parseResult(resultCode: Int, intent: Intent?): List<Uri> {
        if (resultCode != android.app.Activity.RESULT_OK || intent == null) return emptyList()
        val clip = intent.clipData
        return if (clip != null) {
            (0 until clip.itemCount).mapNotNull { clip.getItemAt(it)?.uri }
        } else {
            listOfNotNull(intent.data)
        }
    }
}

class MainActivity : ComponentActivity() {
    private var mainViewModel: MainViewModel? = null

    /** v3.3 DSH: 两个选择器各自记住自己的位置,互不干扰。 */
    private var lastPdfUriOrDir: Uri? = null
    private var lastOutputDir: Uri? = null

    private fun prefs() = getSharedPreferences("pdf2cbz_dsh", Context.MODE_PRIVATE)

    private val pickPdfs = registerForActivityResult(PickPdfsContract()) { uris ->
        mainViewModel?.let { vm ->
            vm.pdfs.clear()
            vm.pdfs.addAll(uris.filter { it.toString().isNotBlank() })
            // 记住本次选中的 PDF 文件(下次选择器定点到它所在目录,不跟随输出目录)
            uris.firstOrNull()?.let { u ->
                lastPdfUriOrDir = u
                try {
                    prefs().edit().putString("last_pdf_uri", u.toString()).apply()
                } catch (_: Exception) {
                }
            }
        }
    }

    private val pickTree = registerForActivityResult(
        ActivityResultContracts.OpenDocumentTree()
    ) { uri ->
        if (uri != null) {
            // v3.1 DSH 修复闪退: 部分 ROM(联想 ZUI 等)会拒绝持久化目录权限并抛
            // SecurityException。原实现未捕获 -> 选完目录点确定直接崩溃。
            // 这里降级处理:持久化失败也不影响本次运行内读写该目录。
            try {
                contentResolver.takePersistableUriPermission(
                    uri,
                    Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION
                )
            } catch (e: SecurityException) {
                mainViewModel?.fullLogs?.add("[警告] 目录权限无法持久化(ROM 限制),本次运行内仍可使用: ${e.localizedMessage}")
            } catch (e: Exception) {
                mainViewModel?.fullLogs?.add("[警告] 保存输出目录时出错(已忽略): ${e.localizedMessage}")
            }
            mainViewModel?.outputTree = uri
            lastOutputDir = uri
            try {
                prefs().edit().putString("last_out_dir", uri.toString()).apply()
            } catch (_: Exception) {
            }
        }
    }

    /** v3.1 DSH: 崩溃与关键事件落盘,重开 App 后仍能在日志里看到原因。 */
    private fun crashLogFile() = java.io.File(filesDir, "pdf2cbz_log.txt")

    private fun appendPersistentLog(text: String) {
        try {
            crashLogFile().appendText(text + "\n")
        } catch (_: Throwable) {
        }
    }

    /** v3.1 DSH: 全局崩溃捕获 —— 闪退不再"无迹可寻"。 */
    private fun installCrashHandler() {
        val prev = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { t, e ->
            try {
                val sw = java.io.StringWriter()
                e.printStackTrace(java.io.PrintWriter(sw))
                appendPersistentLog(
                    "[崩溃] ${SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault()).format(Date())}\n$sw"
                )
            } catch (_: Throwable) {
            }
            prev?.uncaughtException(t, e)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        installCrashHandler()
        appendPersistentLog("[启动] PDF2CBZ v3.3.0-dsh  ${SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault()).format(Date())}")
        // v3.3 DSH: 恢复上次的两个位置(各自独立)
        try {
            lastPdfUriOrDir = prefs().getString("last_pdf_uri", null)?.let { Uri.parse(it) }
            lastOutputDir = prefs().getString("last_out_dir", null)?.let { Uri.parse(it) }
        } catch (_: Exception) {
        }
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
                    // v3.3 DSH: 启动时尝试恢复上次的输出目录(ROM 不支持持久权限时提示重选)
                    LaunchedEffect(Unit) {
                        val saved = try {
                            prefs().getString("last_out_dir", null)
                        } catch (_: Exception) {
                            null
                        }
                        if (saved != null && vm.outputTree == null) {
                            val u = Uri.parse(saved)
                            val granted = try {
                                contentResolver.persistedUriPermissions.any { it.uri == u && it.isWritePermission }
                            } catch (_: Exception) {
                                false
                            }
                            if (granted) {
                                vm.outputTree = u
                                vm.fullLogs.add("[恢复] 已恢复上次的输出目录")
                            } else {
                                vm.fullLogs.add("[提示] 上次的输出目录权限已失效,请重新选择")
                            }
                        }
                    }
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
                                .clickable(enabled = !vm.isProcessing) { pickPdfs.launch(lastPdfUriOrDir) }
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
                                .clickable(enabled = !vm.isProcessing) { pickTree.launch(lastOutputDir) }
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
                        // v3.1 DSH: 打开日志即自动带出落盘记录(含上次闪退的堆栈),不用再猜原因
                        val diskLog by produceState(initialValue = "", showLogDialog) {
                            value = try {
                                crashLogFile().takeIf { it.exists() }?.readText()?.takeLast(12000) ?: ""
                            } catch (_: Throwable) {
                                ""
                            }
                        }
                        // v3.2 DSH 修复闪退②: 原实现用 SelectionContainer 包 LazyColumn,
                        // 长按拖选文本时 Compose 选区管理器算方向越界 -> 崩溃(用户"复制日志就崩")。
                        // 现在改成单个可滚动文本块 + 一键复制/导出,不再需要手动拖选。
                        val fullLogText = buildString {
                            appendLine("=== 本次运行日志 ===")
                            if (vm.fullLogs.isEmpty()) appendLine("(暂无)") else vm.fullLogs.forEach { appendLine(it) }
                            if (diskLog.isNotBlank()) {
                                appendLine()
                                appendLine("=== 历史记录(含崩溃堆栈) ===")
                                append(diskLog)
                            }
                        }
                        AlertDialog(
                            onDismissRequest = { showLogDialog = false },
                            title = { Text("📋 运行日志") },
                            text = {
                                Column(
                                    modifier = Modifier
                                        .heightIn(max = 320.dp)
                                        .verticalScroll(rememberScrollState())
                                ) {
                                    Text(
                                        text = fullLogText,
                                        fontSize = 11.sp,
                                        color = ComposeColor.LightGray
                                    )
                                }
                            },
                            confirmButton = {
                                TextButton(onClick = {
                                    // 一键复制全部日志
                                    try {
                                        val cm = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                                        cm.setPrimaryClip(ClipData.newPlainText("PDF2CBZ 日志", fullLogText))
                                        vm.log = "✅ 日志已复制到剪贴板"
                                    } catch (e: Exception) {
                                        vm.log = "复制失败: ${e.localizedMessage}"
                                    }
                                    showLogDialog = false
                                }) { Text("复制全部") }
                            },
                            dismissButton = {
                                Row {
                                    TextButton(onClick = {
                                        // 一键导出为文件(应用外部私有目录,文件管理器可访问)
                                        try {
                                            val dir = getExternalFilesDir(null)
                                            val f = java.io.File(dir, "pdf2cbz_log_export.txt")
                                            f.writeText(fullLogText)
                                            vm.log = "✅ 已导出: ${f.absolutePath}"
                                            appendPersistentLog("[导出] 日志已导出到 ${f.absolutePath}")
                                        } catch (e: Exception) {
                                            vm.log = "导出失败: ${e.localizedMessage}"
                                        }
                                        showLogDialog = false
                                    }) { Text("导出文件") }
                                    TextButton(onClick = { showLogDialog = false }) { Text("关闭") }
                                }
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
                                    Text("• 版本：v3.3.0-dsh (DSH Edition · 输入/输出位置各自独立记忆)", fontSize = 14.sp)
                                    Text("• 开发者：Gemini & a245888295-dot & DSH", fontSize = 14.sp)
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

    /**
     * v3.2 DSH 修复闪退①: 原实现对 tree: URI 调 ContentResolver.query,
     * 系统抛 UnsupportedOperationException,而它在 Compose 渲染期被调用 -> 界面直接崩。
     * 现在 tree URI 走 DocumentFile,且全程兜底,任何解析失败都退回显示 URI 本身。
     */
    private fun getFileName(uri: Uri): String? {
        return try {
            var name: String? = null
            try {
                contentResolver.query(uri, null, null, null, null)?.use { cursor ->
                    val nameIndex = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                    if (nameIndex != -1 && cursor.moveToFirst()) {
                        name = cursor.getString(nameIndex)
                    }
                }
            } catch (_: Exception) {
                // tree: URI 不支持 query,交给下面的 DocumentFile 分支
            }
            if (name.isNullOrBlank()) {
                name = try {
                    DocumentFile.fromTreeUri(this, uri)?.name
                } catch (_: Exception) {
                    null
                }
            }
            if (name.isNullOrBlank()) {
                name = uri.lastPathSegment
                    ?.substringAfterLast('/')
                    ?.substringAfterLast(':')
            }
            name?.takeIf { it.isNotBlank() } ?: uri.toString()
        } catch (_: Exception) {
            uri.toString()
        }
    }

    /**
     * DSH v3.0 原生无损提取:按 PDF 结构逐页遍历图像对象(PdfBox),
     * 每页取面积最大的非 mask 图像作为页面主图。
     *
     * - DCTDecode(JPEG):createRawInputStream 零解码直通,得到原始 JPEG 字节;
     * - Flate/LZW/RLE 位图:解码为 Bitmap 后写无损 PNG;
     * - JPX/JBIG2/CCITT、缺图页、异常:返回 null,由 PdfRenderer 渲染兜底。
     *
     * 返回 null 表示「不适合直通」,调用方必须走渲染路径 —— 宁可重编码也不漏页。
     */
    private fun extractNativePages(
        pfd: FileDescriptor,
        onLog: (String) -> Unit
    ): List<Pair<String, ByteArray>>? {
        val pages = mutableListOf<Pair<String, ByteArray>>()
        return try {
            FileInputStream(pfd).use { fis ->
                PDDocument.load(fis).use { doc ->
                    val pageCount = doc.numberOfPages
                    for (i in 0 until pageCount) {
                        val page = doc.getPage(i)
                        val res = page.resources ?: return null

                        var best: PDImageXObject? = null
                        var bestArea = 0
                        for (name in res.xObjectNames) {
                            val xo = try {
                                res.getXObject(name)
                            } catch (e: Exception) {
                                null
                            }
                            if (xo is PDImageXObject && !xo.isStencil) {
                                val area = xo.width * xo.height
                                if (area > bestArea) {
                                    bestArea = area
                                    best = xo
                                }
                            }
                        }

                        val img = best ?: return null
                        when (img.suffix) {
                            "jpg" -> {
                                // 零解码直通:原始 JPEG 字节直接进 CBZ
                                val raw = img.cosObject.createRawInputStream().use { it.readBytes() }
                                pages.add("jpg" to raw)
                            }
                            "png" -> {
                                // Flate/LZW/RLE 位图:解码后写无损 PNG
                                val bmp = img.image
                                val bos = ByteArrayOutputStream()
                                bmp.compress(Bitmap.CompressFormat.PNG, 100, bos)
                                bmp.recycle()
                                pages.add("png" to bos.toByteArray())
                            }
                            else -> return null
                        }
                    }
                    onLog("已解析 $pageCount 页,全部命中可无损直通的图像编码")
                }
            }
            pages
        } catch (e: Exception) {
            onLog("原生提取异常,回退渲染: ${e.localizedMessage}")
            null
        }
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
                var nativePages: List<Pair<String, ByteArray>>? = null

                // v3.0 DSH: 自适应模式优先走「按 PDF 结构逐页原生无损提取」
                if (currentQuality == QualityMode.ADAPTIVE) {
                    contentResolver.openFileDescriptor(pdfUri, "r")?.use { pfd ->
                        nativePages = extractNativePages(pfd.fileDescriptor, logAndProgress)
                    }
                }

                if (nativePages != null && nativePages!!.isNotEmpty()) {
                    val extracted = nativePages!!
                    logAndProgress("⚡ [原生无损] 逐页提取成功,共 ${extracted.size} 页原始图像")
                    contentResolver.openOutputStream(targetFile.uri)?.use { os ->
                        ZipOutputStream(os.buffered(256 * 1024)).use { zipOut ->
                            extracted.forEachIndexed { imgIdx, pair ->
                                val entryName = String.format("%04d.%s", imgIdx + 1, pair.first)
                                writeZipStoredEntry(zipOut, pair.second, entryName)
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

# 7. DSH: 统一版本号（zip 里写死 2.0.0，README 说 2.1.0，这里以补丁为准）
DSH_VERSION_NAME = "3.3.0-dsh"
DSH_VERSION_CODE = 330

def patch_version():
    for r, _, fs in os.walk('.'):
        if 'app' not in r:
            continue
        for file in fs:
            if file == 'build.gradle.kts':
                fp = os.path.join(r, file)
                try:
                    with open(fp, 'r', encoding='utf-8') as f:
                        c = f.read()
                    c2 = re.sub(r'versionCode\s*=\s*\d+', f'versionCode = {DSH_VERSION_CODE}', c)
                    c2 = re.sub(r'versionName\s*=\s*"[^"]*"', f'versionName = "{DSH_VERSION_NAME}"', c2)
                    if c2 != c:
                        with open(fp, 'w', encoding='utf-8') as f:
                            f.write(c2)
                        print(f"✅ 版本号已设为 {DSH_VERSION_NAME} ({DSH_VERSION_CODE}): {fp}")
                except Exception as e:
                    print(f"⚠ 设置版本号失败: {e}")

patch_version()
