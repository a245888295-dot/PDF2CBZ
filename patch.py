import os
import re
import base64

# ============================================================
# v3.7.1 DSH: 固定签名
# 根因: CI 跑 assembleDebug, debug 包用 runner 上临时生成的
# ~/.android/debug.keystore —— runner 一换就换证书, 于是
# 「同包名不同签名」, 覆盖安装必然失败, 只能卸载重装(数据全清)。
# 这里把一张固定证书内嵌进补丁, 所有构建共用, 从此可覆盖升级。
# 证书 sha256: 09:47:74:0F:35:D1:CF:C7:EB:56:BA:FD:28:12:5A:42:
#              1C:ED:43:6E:9F:01:B4:BB:BC:3A:86:41:47:BE:11:49
# 有效期至 2056-10-09
# ============================================================
SIGNING_P12_B64 = (
    "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"
)
SIGNING_STORE_PASS = "pdf2cbz-dsh"
SIGNING_KEY_ALIAS = "pdf2cbz"
SIGNING_KEY_PASS = "pdf2cbz-dsh"


def ensure_signing_keystore():
    os.makedirs('signing', exist_ok=True)
    path = os.path.join('signing', 'pdf2cbz.p12')
    data = base64.b64decode(SIGNING_P12_B64)
    with open(path, 'wb') as f:
        f.write(data)
    print("固定签名 keystore 已就位: %s (%d 字节)" % (path, len(data)))
    return path


def patch_signing_config():
    gradle_path = None
    for root, dirs, files in os.walk('.'):
        if 'build.gradle.kts' in files and 'app' in root:
            gradle_path = os.path.join(root, 'build.gradle.kts')
            break
    if not gradle_path:
        print("未找到 app/build.gradle.kts, 跳过签名配置")
        return
    with open(gradle_path, 'r', encoding='utf-8') as f:
        content = f.read()
    if 'fixedDebug' in content:
        print("固定签名配置已存在, 跳过")
        return
    block = """

// v3.7.1 DSH: 固定签名 —— 所有构建共用一张证书, 覆盖安装不再冲突
android {
    signingConfigs {
        create("fixedDebug") {
            storeFile = rootProject.file("signing/pdf2cbz.p12")
            storePassword = "pdf2cbz-dsh"
            keyAlias = "pdf2cbz"
            keyPassword = "pdf2cbz-dsh"
        }
    }
    buildTypes {
        getByName("debug") {
            signingConfig = signingConfigs.getByName("fixedDebug")
        }
    }
}
"""
    content += block
    with open(gradle_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("已注入固定签名配置: %s" % gradle_path)


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
        'implementation("androidx.compose.material:material-icons-extended:1.6.8")',
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
ensure_signing_keystore()
patch_signing_config()

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
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContract
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.ui.graphics.vector.ImageVector
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
import androidx.compose.ui.text.style.TextAlign
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
import com.tom_roush.pdfbox.contentstream.operator.Operator
import com.tom_roush.pdfbox.cos.COSName
import com.tom_roush.pdfbox.pdfparser.PDFStreamParser
import com.tom_roush.pdfbox.pdmodel.PDDocument
import com.tom_roush.pdfbox.pdmodel.PDPage
import com.tom_roush.pdfbox.pdmodel.graphics.image.PDImageXObject

enum class QualityMode(val title: String, val desc: String) {
    ADAPTIVE("自适应", "优先无损直通，兼容高画质渲染（推荐）"),
    NATIVE("原生", "强制最高清晰度渲染（体积较大）"),
    LOW("低画质", "降低分辨率与质量，大幅减小体积")
}

/** v3.7 DSH: 页面栈 —— 设置/日志/关于改成独立页面,不再用弹窗堆在首页 */
enum class AppScreen { HOME, SETTINGS, QUALITY, LOG, ABOUT }

class MainViewModel : ViewModel() {
    val pdfs = mutableStateListOf<Uri>()
    var outputTree by mutableStateOf<Uri?>(null)
    var log by mutableStateOf("等待操作…")
    /** v3.8 DSH: 命令行式滚动区 —— 进度逐行追加, 旧行留在上面 */
    val console = mutableStateListOf<String>()
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
            if (input != null && input.scheme == "content") {
                // 传上次选中的 PDF 文件 URI,选择器会定位到它所在目录并选中它
                // v3.5 DSH: 只接受 content:// 文档 URI, 非 content(或误传的 tree URI)一律不传,
                // 避免部分 ROM 的 DocumentsUI 解析失败后又退回全局上次位置。
                if (!input.toString().contains("/tree/")) {
                    putExtra("android.provider.extra.INITIAL_URI", input)
                }
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

/**
 * v3.5 DSH: 自定义「选择输出目录」契约。
 *
 * 标准 ActivityResultContracts.OpenDocumentTree 的 createIntent 实现是
 * `Intent(Intent.ACTION_OPEN_DOCUMENT_TREE)`, 把传进来的 input 直接丢掉,
 * 于是 pickTree.launch(lastOutputDir) 等于什么都没传 —— 输出目录选择器
 * 永远跟随系统 DocumentsUI 的「全局上次位置」, 而那个位置通常就是刚选完
 * PDF 停留的目录。这就是「选 PDF」和「选输出目录」绑在一起、互相干扰的根因。
 *
 * 这里自己实现, 显式把上次的输出目录(没有历史时退回下载目录)作为 INITIAL_URI 传入。
 */
private class PickTreeContract : ActivityResultContract<Uri?, Uri?>() {

    override fun createIntent(context: Context, input: Uri?): Intent {
        return Intent(Intent.ACTION_OPEN_DOCUMENT_TREE).apply {
            addFlags(
                Intent.FLAG_GRANT_READ_URI_PERMISSION or
                    Intent.FLAG_GRANT_WRITE_URI_PERMISSION or
                    Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION or
                    Intent.FLAG_GRANT_PREFIX_URI_PERMISSION
            )
            val anchor = if (input != null &&
                input.scheme == "content" &&
                input.toString().contains("/tree/")
            ) {
                input
            } else {
                defaultDownloadsTree()
            }
            if (anchor != null) {
                putExtra("android.provider.extra.INITIAL_URI", anchor)
            }
        }
    }

    override fun parseResult(resultCode: Int, intent: Intent?): Uri? {
        if (resultCode != android.app.Activity.RESULT_OK) return null
        return intent?.data
    }

    /** 首次使用时没有历史输出目录: 退回「下载」目录, 避免又跟随 DocumentsUI 的上次位置。 */
    private fun defaultDownloadsTree(): Uri? {
        return try {
            android.provider.DocumentsContract.buildTreeDocumentUri(
                "com.android.externalstorage.documents",
                "primary:Download"
            )
        } catch (_: Exception) {
            null
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
        // v3.5 DSH: 用户在选择器里按返回/取消时 uris 为空。原实现无条件 clear(),
        // 于是「取消一次」就会把已选的 PDF 全部清空, 表现为两个入口互相干扰。
        // 这里空结果直接忽略, 不动已选列表。
        appendPersistentLog("[选择] PDF 选择器返回 ${uris.size} 个: ${uris.map { getFileName(it) ?: it.toString() }}")
        if (uris.isNotEmpty()) mainViewModel?.let { vm ->
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

    // v3.5 DSH: 改用自定义契约。原写法 ActivityResultContracts.OpenDocumentTree()
    // 会丢弃 launch() 传进来的初始位置, 这才是「两个选择器互相带跑」的真正原因。
    private val pickTree = registerForActivityResult(
        PickTreeContract()
    ) { uri ->
        appendPersistentLog("[选择] 输出目录选择器返回: ${uri ?: "取消(未改动)"}")
        if (uri != null) applyOutputDir(uri)
    }

    /**
     * v3.6 DSH: 输出目录的唯一应用入口。
     * 「一键沿用上次目录」「最近用过的目录」和应用内选择都走这里,不再必须经过系统选择器。
     */
    private fun applyOutputDir(uri: Uri) {
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
        appendPersistentLog("[输出目录] 已应用: $uri")
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
        appendPersistentLog("[启动] PDF2CBZ v3.6.0-dsh  ${SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault()).format(Date())}")
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
                background = ComposeColor(0xFF0E1116),
                surface = ComposeColor(0xFF141821),
                surfaceVariant = ComposeColor(0xFF232833),
                primary = ComposeColor(0xFF7DD3FC),
                onBackground = ComposeColor(0xFFECF1F8),
                onSurface = ComposeColor(0xFFF5F8FC),
                onSurfaceVariant = ComposeColor(0xFF9BA6B8),
                outline = ComposeColor(0xFF3A4150)
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
                    var showDirDialog by remember { mutableStateOf(false) }
                    var screen by remember { mutableStateOf(AppScreen.HOME) }

                    // v3.7 DSH: 子页面里按返回键回首页,不直接退出 App
                    BackHandler(enabled = screen != AppScreen.HOME) {
                        screen = if (screen == AppScreen.QUALITY) AppScreen.SETTINGS else AppScreen.HOME
                    }

                    if (screen == AppScreen.HOME) Column(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(horizontal = 18.dp)
                    ) {
                        // ── 顶部品牌栏（Material 3，去 emoji）────────────────
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(top = 18.dp, bottom = 16.dp)
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    text = "PDF → CBZ",
                                    fontSize = 24.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = MaterialTheme.colorScheme.onBackground
                                )
                                Text(
                                    text = "原生无损直通 · 逐页判定",
                                    fontSize = 12.sp,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                            // v3.7 DSH: 首页只留一个入口,日志/关于都收进设置页
                            IconButton(onClick = { screen = AppScreen.SETTINGS }) {
                                Icon(Icons.Outlined.Tune, contentDescription = "设置")
                            }
                        }

                        // ── 步骤 1：选择 PDF ─────────────────────────────
                        SourceCard(
                            icon = Icons.Outlined.PictureAsPdf,
                            title = if (vm.pdfs.isEmpty()) "选择 PDF 文件" else "已选 ${vm.pdfs.size} 个 PDF",
                            subtitle = if (vm.pdfs.isEmpty()) "可多选" else "点击重新选择",
                            enabled = !vm.isProcessing
                        ) {
                            // v3.4 DSH: 记下我们传给选择器的初始位置 —— 某些 ROM 的
                            // DocumentsUI 会忽略 EXTRA_INITIAL_URI，日志里能直接看出来。
                            vm.fullLogs.add(
                                "[选择] PDF 选择器,初始位置: " +
                                    (lastPdfUriOrDir?.let { getFileName(it) ?: it.toString() } ?: "无")
                            )
                            pickPdfs.launch(lastPdfUriOrDir)
                        }

                        Spacer(modifier = Modifier.height(14.dp))

                        // ── 步骤 2：输出目录 ─────────────────────────────
                        SourceCard(
                            icon = Icons.Outlined.FolderOpen,
                            title = "输出目录",
                            subtitle = vm.outputTree?.let { getFileName(it) ?: it.toString() }
                                ?: "未设置 · 点击选择存储位置",
                            enabled = !vm.isProcessing
                        ) {
                            // v3.6 DSH: 不再直接弹系统选择器。
                            // 实测(10-17 17:29 的 logcat + DocumentsUI 的 lastAccess.db):
                            // 本机 OPEN_DOCUMENT_TREE 会忽略 EXTRA_INITIAL_URI, 永远恢复
                            // 「上一次访问过的目录」= 刚选过 PDF 的那个文件夹, 于是输出目录
                            // 选择器被 PDF 目录带跑。改成就地给「一键沿用 / 最近目录」。
                            showDirDialog = true
                        }

                        Spacer(modifier = Modifier.height(14.dp))


                        Spacer(modifier = Modifier.height(14.dp))

                        // ── 状态 / 进度：命令行式滚动区(v3.8) ─────────────
                        val consoleScroll = rememberScrollState()
                        LaunchedEffect(vm.console.size, vm.pdfs.size, vm.isProcessing) {
                            consoleScroll.animateScrollTo(consoleScroll.maxValue)
                        }
                        Column(
                            modifier = Modifier
                                .fillMaxWidth()
                                .weight(1f)
                                .verticalScroll(consoleScroll)
                        ) {
                            if (vm.pdfs.isNotEmpty()) {
                                Text(
                                    text = "已选 ${vm.pdfs.size} 个 PDF",
                                    fontSize = 12.sp,
                                    fontWeight = FontWeight.SemiBold,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                                vm.pdfs.forEach { u ->
                                    Text(
                                        text = "  " + (getFileName(u) ?: u.toString()),
                                        fontSize = 12.sp,
                                        color = MaterialTheme.colorScheme.onSurface,
                                        maxLines = 1,
                                        overflow = TextOverflow.Ellipsis
                                    )
                                }
                                Spacer(modifier = Modifier.height(8.dp))
                            }
                            vm.console.forEach { line ->
                                Text(
                                    text = line,
                                    fontSize = 12.sp,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                            if (vm.console.isEmpty() && vm.pdfs.isEmpty()) {
                                Text(
                                    text = "等待操作…",
                                    fontSize = 12.sp,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }
                        Spacer(modifier = Modifier.height(10.dp))

                        // ── 主按钮 ─────────────────────────────────────
                        Button(
                            onClick = {
                                vm.console.clear()
                                vm.isProcessing = true
                                scope.launch(Dispatchers.IO) {
                                    convertPdfsToCbz(
                                        vm = vm,
                                        onLog = { entry ->
                                            scope.launch(Dispatchers.Main) { vm.fullLogs.add(entry) }
                                        },
                                        onProgress = { status ->
                                            scope.launch(Dispatchers.Main) { vm.console.add(status) }
                                        }
                                    )
                                    vm.isProcessing = false
                                }
                            },
                            enabled = vm.pdfs.isNotEmpty() && vm.outputTree != null && !vm.isProcessing,
                            shape = RoundedCornerShape(16.dp),
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(54.dp)
                        ) {
                            Icon(
                                imageVector = if (vm.isProcessing) {
                                    Icons.Outlined.HourglassEmpty
                                } else {
                                    Icons.Outlined.PlayArrow
                                },
                                contentDescription = null
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = if (vm.isProcessing) "正在转换…" else "开始转换",
                                fontSize = 16.sp,
                                fontWeight = FontWeight.SemiBold
                            )
                        }
                        Spacer(modifier = Modifier.height(18.dp))
                    }

                    // --- 页面：画质与清晰度(v3.8 与其它设置条目一致) ---
                    if (screen == AppScreen.QUALITY) {
                        QualityPage(
                            qualityMode = vm.qualityMode,
                            onQualityChange = { vm.qualityMode = it },
                            onBack = { screen = AppScreen.SETTINGS }
                        )
                    }

                    // --- 页面：运行日志(v3.7 弹窗 -> 独立页) ---
                    if (screen == AppScreen.LOG) {
                        val diskLog by produceState(initialValue = "", screen) {
                            value = try {
                                crashLogFile().takeIf { it.exists() }?.readText()?.takeLast(12000) ?: ""
                            } catch (_: Throwable) {
                                ""
                            }
                        }
                        val fullLogText = buildString {
                            appendLine("=== 本次运行日志 ===")
                            if (vm.fullLogs.isEmpty()) appendLine("(暂无)") else vm.fullLogs.forEach { appendLine(it) }
                            if (diskLog.isNotBlank()) {
                                appendLine()
                                appendLine("=== 历史记录(含崩溃堆栈) ===")
                                append(diskLog)
                            }
                        }
                        LogPage(
                            fullLogText = fullLogText,
                            onCopy = {
                                try {
                                    val cm = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                                    cm.setPrimaryClip(ClipData.newPlainText("PDF2CBZ 日志", fullLogText))
                                    vm.log = "日志已复制到剪贴板"
                                } catch (e: Exception) {
                                    vm.log = "复制失败: ${e.localizedMessage}"
                                }
                            },
                            onExport = {
                                try {
                                    val dir = getExternalFilesDir(null)
                                    val f = java.io.File(dir, "pdf2cbz_log_export.txt")
                                    f.writeText(fullLogText)
                                    vm.log = "已导出: ${f.absolutePath}"
                                    appendPersistentLog("[导出] 日志已导出到 ${f.absolutePath}")
                                } catch (e: Exception) {
                                    vm.log = "导出失败: ${e.localizedMessage}"
                                }
                            },
                            onBack = { screen = AppScreen.SETTINGS }
                        )
                    }

                    // --- 弹窗：输出目录(v3.6：绕开 DocumentsUI 的位置记忆) ---
                    if (showDirDialog) {
                        val recentDirs: List<Uri> = try {
                            contentResolver.persistedUriPermissions
                                .filter { it.isWritePermission && it.uri.toString().contains("/tree/") }
                                .map { it.uri }
                                .distinct()
                        } catch (_: Exception) {
                            emptyList()
                        }
                        AlertDialog(
                            onDismissRequest = { showDirDialog = false },
                            title = { Text("输出目录", fontWeight = FontWeight.SemiBold) },
                            text = {
                                Column(
                                    modifier = Modifier
                                        .heightIn(max = 320.dp)
                                        .verticalScroll(rememberScrollState()),
                                    verticalArrangement = Arrangement.spacedBy(4.dp)
                                ) {
                                    Text(
                                        "当前：" + (vm.outputTree?.let { getFileName(it) ?: it.toString() } ?: "未设置"),
                                        fontSize = 13.sp
                                    )
                                    if (lastOutputDir != null) {
                                        TextButton(onClick = {
                                            applyOutputDir(lastOutputDir!!)
                                            showDirDialog = false
                                        }) { Text("一键沿用上次目录（不进选择器）", fontSize = 13.sp) }
                                    }
                                    if (recentDirs.isNotEmpty()) {
                                        Text(
                                            "最近用过的目录：",
                                            fontSize = 12.sp,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                                            modifier = Modifier.padding(top = 6.dp)
                                        )
                                        recentDirs.take(5).forEach { u ->
                                            TextButton(onClick = {
                                                applyOutputDir(u)
                                                showDirDialog = false
                                            }) { Text(getFileName(u) ?: u.toString(), fontSize = 13.sp) }
                                        }
                                    }
                                }
                            },
                            confirmButton = {
                                TextButton(onClick = {
                                    showDirDialog = false
                                    appendPersistentLog(
                                        "[选择] 打开系统目录选择器,anchor=" + (lastOutputDir?.toString() ?: "null")
                                    )
                                    pickTree.launch(lastOutputDir)
                                }) { Text("选择其它目录…") }
                            },
                            dismissButton = {
                                TextButton(onClick = { showDirDialog = false }) { Text("取消") }
                            }
                        )
                    }

                    // --- 页面：设置(v3.7 独立页,选项集中在这里) ---
                    if (screen == AppScreen.SETTINGS) {
                        SettingsPage(
                            qualityMode = vm.qualityMode,
                            onOpenQuality = { screen = AppScreen.QUALITY },
                            onOpenLog = { screen = AppScreen.LOG },
                            onOpenAbout = { screen = AppScreen.ABOUT },
                            onBack = { screen = AppScreen.HOME }
                        )
                    }

                    // --- 页面：关于(v3.7 独立页,版本说明不再挤在版本号后面) ---
                    if (screen == AppScreen.ABOUT) {
                        AboutPage(onBack = { screen = AppScreen.SETTINGS })
                    }
                }
            }
        }
    }

    /** v3.7 DSH: 子页面通用头部(返回 + 标题) */
    @Composable
    private fun PageHeader(title: String, onBack: () -> Unit) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 14.dp, bottom = 10.dp)
        ) {
            IconButton(onClick = onBack) {
                Icon(Icons.Outlined.ChevronLeft, contentDescription = "返回")
            }
            Text(
                text = title,
                fontSize = 22.sp,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onBackground,
                modifier = Modifier.padding(start = 2.dp)
            )
        }
    }

    /** v3.7 DSH: 设置页里的可点条目 */
    @Composable
    private fun SettingsEntry(
        icon: ImageVector,
        title: String,
        subtitle: String,
        onClick: () -> Unit
    ) {
        Card(
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.surfaceVariant
            ),
            modifier = Modifier
                .fillMaxWidth()
                .padding(vertical = 4.dp)
                .clickable(onClick = onClick)
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 14.dp)
            ) {
                Icon(icon, contentDescription = null)
                Spacer(modifier = Modifier.width(12.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Text(title, fontSize = 15.sp, fontWeight = FontWeight.SemiBold)
                    Text(
                        subtitle,
                        fontSize = 11.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                Icon(Icons.Outlined.ChevronRight, contentDescription = null)
            }
        }
    }

    /** v3.7 DSH: 设置页 —— 画质选项 + 日志 / 关于入口 */
    @Composable
    private fun SettingsPage(
        qualityMode: QualityMode,
        onOpenQuality: () -> Unit,
        onOpenLog: () -> Unit,
        onOpenAbout: () -> Unit,
        onBack: () -> Unit
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 18.dp)
        ) {
            PageHeader("设置", onBack)
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f)
                    .verticalScroll(rememberScrollState())
            ) {
                SettingsEntry(
                    icon = Icons.Outlined.Image,
                    title = "画质与清晰度",
                    subtitle = qualityMode.title,
                    onClick = onOpenQuality
                )
                Spacer(modifier = Modifier.height(10.dp))
                SettingsEntry(
                    icon = Icons.Outlined.Description,
                    title = "运行日志",
                    subtitle = "本次与历史记录(含崩溃堆栈)",
                    onClick = onOpenLog
                )
                SettingsEntry(
                    icon = Icons.Outlined.Info,
                    title = "关于",
                    subtitle = "版本信息与更新地址",
                    onClick = onOpenAbout
                )
                Spacer(modifier = Modifier.height(18.dp))
            }
        }
    }

    /** v3.8 DSH: 画质选择页(从设置条目进入) */
    @Composable
    private fun QualityPage(
        qualityMode: QualityMode,
        onQualityChange: (QualityMode) -> Unit,
        onBack: () -> Unit
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 18.dp)
        ) {
            PageHeader("画质与清晰度", onBack)
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f)
                    .verticalScroll(rememberScrollState())
            ) {
                QualityMode.values().forEach { mode ->
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { onQualityChange(mode) }
                            .padding(vertical = 8.dp, horizontal = 4.dp)
                    ) {
                        RadioButton(
                            selected = (qualityMode == mode),
                            onClick = { onQualityChange(mode) }
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Column {
                            Text(mode.title, fontWeight = FontWeight.SemiBold, fontSize = 15.sp)
                            Text(
                                mode.desc,
                                fontSize = 11.sp,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                }
            }
        }
    }

    /** v3.7 DSH: 日志页 */
    @Composable
    private fun LogPage(
        fullLogText: String,
        onCopy: () -> Unit,
        onExport: () -> Unit,
        onBack: () -> Unit
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 18.dp)
        ) {
            PageHeader("运行日志", onBack)
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f)
                    .verticalScroll(rememberScrollState())
            ) {
                Text(
                    text = fullLogText,
                    fontSize = 11.sp,
                    color = ComposeColor.LightGray
                )
            }
            Row(
                horizontalArrangement = Arrangement.spacedBy(10.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 12.dp)
            ) {
                OutlinedButton(onClick = onCopy, modifier = Modifier.weight(1f)) {
                    Text("复制全部")
                }
                OutlinedButton(onClick = onExport, modifier = Modifier.weight(1f)) {
                    Text("导出文件")
                }
            }
        }
    }

    /** v3.7 DSH: 关于页 */
    @Composable
    private fun AboutPage(onBack: () -> Unit) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 18.dp)
        ) {
            PageHeader("关于 PDF2CBZ", onBack)
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f)
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Text("版本", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Text("v3.8.0-dsh", fontSize = 16.sp, fontWeight = FontWeight.SemiBold)
                Text(
                    "首页只保留 选择文件 / 输出目录 / 滚动状态区 / 开始;设置与画质都改成独立页面。",
                    fontSize = 12.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(modifier = Modifier.height(6.dp))
                Text("开发者", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Text("Gemini & a245888295-dot & DSH", fontSize = 14.sp)
                Text("联系方式", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Text("待定", fontSize = 14.sp)
                Spacer(modifier = Modifier.height(6.dp))
                Text("更新地址", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                SelectionContainer {
                    Text(
                        text = "https://github.com/a245888295-dot/PDF2CBZ/actions",
                        fontSize = 12.sp,
                        color = MaterialTheme.colorScheme.primary
                    )
                }
            }
        }
    }

    /** v3.4 DSH: 步骤卡片 —— 图标 + 步骤号 + 标题 + 说明，替换原来的 emoji 卡片。 */
    @Composable
    private fun SourceCard(
        icon: ImageVector,
        title: String,
        subtitle: String,
        enabled: Boolean,
        onClick: () -> Unit
    ) {
        Card(
            shape = RoundedCornerShape(20.dp),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.surfaceVariant
            ),
            modifier = Modifier
                .fillMaxWidth()
                .clickable(enabled = enabled) { onClick() }
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.padding(16.dp)
            ) {
                Box(
                    contentAlignment = Alignment.Center,
                    modifier = Modifier
                        .size(44.dp)
                        .background(
                            color = MaterialTheme.colorScheme.primary.copy(alpha = 0.14f),
                            shape = RoundedCornerShape(14.dp)
                        )
                ) {
                    Icon(
                        imageVector = icon,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary
                    )
                }
                Spacer(modifier = Modifier.width(14.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = title,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.onSurface,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                    Spacer(modifier = Modifier.height(3.dp))
                    Text(
                        text = subtitle,
                        fontSize = 12.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }
            }
        }
    }

    /** v3.4 DSH: 已选文件的一行。 */
    @Composable
    private fun SelectedFileRow(name: String) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier
                .fillMaxWidth()
                .padding(start = 4.dp)
        ) {
            Icon(
                imageVector = Icons.Outlined.Description,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.size(16.dp)
            )
            Spacer(modifier = Modifier.width(10.dp))
            Text(
                text = name,
                fontSize = 12.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
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
     * v3.4 DSH: **逐页**判定能不能无损直通。返回 list 第 i 项 = 第 i 页产出(扩展名 to 字节);
     * null = 这一页不能直通,必须交 PdfRenderer 渲染。
     *
     * 为什么不"要么全直通、要么全渲染": 一个 PDF 里常混着「整页单图」和「带文字/多图」的页。
     * 前者直通是字节级无损(原始 JPEG 原样进 CBZ),后者直通会丢内容 —— 按页分别处理,
     * 才能既保住无损、又不丢东西。整份返回 null 只表示「这份 PDF 解析不了」。
     */
    private fun extractNativePages(
        pfd: FileDescriptor,
        onLog: (String) -> Unit
    ): List<Pair<String, ByteArray>?>? {
        val pages = mutableListOf<Pair<String, ByteArray>?>()
        return try {
            FileInputStream(pfd).use { fis ->
                PDDocument.load(fis).use { doc ->
                    var passthrough = 0
                    var needRender = 0
                    for (i in 0 until doc.numberOfPages) {
                        val out = extractSinglePage(doc.getPage(i), i + 1, onLog)
                        if (out == null) needRender++ else passthrough++
                        pages.add(out)
                    }
                    onLog(
                        "已解析 ${doc.numberOfPages} 页: 无损直通 $passthrough 页" +
                            (if (needRender > 0) ", 需渲染 $needRender 页(含文字/矢量/多图)" else "")
                    )
                }
            }
            pages
        } catch (e: Exception) {
            onLog("原生提取异常,回退整体渲染: ${e.localizedMessage}")
            null
        }
    }

    /** 内容流里是否真的在画文字(BT/Tj/TJ) —— 解析失败就保守当有文字。 */
    private fun pageShowsText(page: PDPage): Boolean = try {
        // 注意: 这版 PdfBox 的 parse() 返回 void, token 要用 getTokens() 取。
        val parser = PDFStreamParser(page)
        parser.parse()
        var found = false
        for (t in parser.tokens) {
            if (t is Operator) {
                val name = t.name
                if (name == "BT" || name == "Tj" || name == "TJ" ||
                    name == "'" || name == "\""
                ) {
                    found = true
                    break
                }
            }
        }
        found
    } catch (e: Exception) {
        true
    }

    /**
     * 单页无损直通判定: 只有「这一页就是一张整幅图」时才返回字节,其余一律 null 交渲染 ——
     *  - 页面用了字体(有文字)          → 直通会把字丢掉
     *  - 页面有非图像 XObject(表单/组) → 可能有叠加内容
     *  - 页面图像不止一张              → 是拼版页
     *  - 图像带 /SMask(软蒙版)         → 直通会丢透明信息
     *  - 滤镜解完不是合法 JPEG/PNG 头  → 宁可不直通,也不写坏图
     */
    private fun extractSinglePage(
        page: PDPage,
        pageNo: Int,
        onLog: (String) -> Unit
    ): Pair<String, ByteArray>? {
        val res = page.resources ?: return null
        // 注意: 不能只看「页面资源里有字体」—— 有些 PDF 里字体对象是没人引用的残留
        // (实测某漫画 PDF 有 30 个字体对象, 但 /Resources 里根本没有 /Font)。
        // 只有内容流**真的在画文字**(BT/Tj/TJ)才交渲染, 否则白丢字节级无损。
        if (res.fontNames.any() && pageShowsText(page)) {
            onLog("第 $pageNo 页: 内容流在画文字, 交渲染")
            return null
        }
        var best: PDImageXObject? = null
        var bestArea = 0
        var imageCount = 0
        for (name in res.xObjectNames) {
            val xo = try {
                res.getXObject(name)
            } catch (e: Exception) {
                null
            }
            if (xo is PDImageXObject) {
                if (!xo.isStencil) {
                    imageCount++
                    val area = xo.width * xo.height
                    if (area > bestArea) {
                        bestArea = area
                        best = xo
                    }
                }
            } else {
                onLog("第 $pageNo 页: 含矢量/表单对象, 交渲染")
                return null
            }
        }
        if (imageCount != 1) {
            if (imageCount > 1) onLog("第 $pageNo 页: 多图拼版, 交渲染")
            return null
        }
        val img = best ?: return null
        if (img.cosObject.getDictionaryObject(COSName.SMASK) != null) {
            onLog("第 $pageNo 页: 图像带透明蒙版, 交渲染")
            return null
        }
        return when (img.suffix) {
            "jpg" -> {
                // v3.4 DSH 修复(坏图 bug): 以前用 cosObject.createRawInputStream() —— 它给的是
                // **未解滤镜**的存储字节。夸克/微信导出的漫画 PDF 常见
                // `/Filter [ /ASCII85Decode /DCTDecode ]`,于是把 ASCII85 文本当 JPEG 写进 CBZ
                // (实测 29/29 页全坏, 文件头是 `s4IA0!` 而不是 `FFD8`)。
                // PDStream.createInputStream(stopFilters) 会解掉非图像滤镜、到 DCTDecode 停下;
                // 若第一个滤镜就是 DCTDecode,直接返回原始字节 —— 两种 PDF 都覆盖。
                val raw = img.createInputStream(listOf("DCTDecode")).use { it.readBytes() }
                if (raw.size < 4 || raw[0] != 0xFF.toByte() || raw[1] != 0xD8.toByte()) {
                    onLog("第 $pageNo 页: 直通字节不是 JPEG 头, 交渲染")
                    return null
                }
                "jpg" to raw
            }
            "png" -> {
                // Flate/LZW/RLE 位图: 解码后写无损 PNG(像素级无损)
                val bmp = img.image
                val bos = ByteArrayOutputStream()
                bmp.compress(Bitmap.CompressFormat.PNG, 100, bos)
                // 不要 recycle(): PdfBox 会缓存这份位图(cachedImage),回收后再被别的页取用会崩
                "png" to bos.toByteArray()
            }
            else -> {
                onLog("第 $pageNo 页: 图像编码 ${img.suffix} 不支持直通, 交渲染")
                null
            }
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

    /**
     * v3.4 DSH: 渲染单页写进 CBZ。
     * ADAPTIVE/NATIVE 用 PNG —— 渲染本身已经是一次栅格化,不给它再叠一层 JPEG 损失;
     * LOW 档用 JPEG 60(体积优先)。渲染模式用 FOR_PRINT,文字/线条更清楚。
     */
    private fun writeRenderedPage(
        renderer: PdfRenderer,
        index: Int,
        quality: QualityMode,
        zipOut: ZipOutputStream
    ) {
        renderer.openPage(index).use { page ->
            val targetWidth = when (quality) {
                QualityMode.NATIVE -> 1800f
                QualityMode.ADAPTIVE -> 1440f
                QualityMode.LOW -> 1080f
            }
            val scale = if (page.width > 0) (targetWidth / page.width).coerceIn(1.0f, 2.0f) else 1.5f
            val bitmap = Bitmap.createBitmap(
                (page.width * scale).toInt(),
                (page.height * scale).toInt(),
                Bitmap.Config.ARGB_8888
            )
            bitmap.eraseColor(Color.WHITE)
            page.render(bitmap, null, null, PdfRenderer.Page.RENDER_MODE_FOR_PRINT)

            val stream = ByteArrayOutputStream()
            val lossless = quality != QualityMode.LOW
            if (lossless) {
                bitmap.compress(Bitmap.CompressFormat.PNG, 100, stream)
            } else {
                bitmap.compress(Bitmap.CompressFormat.JPEG, 60, stream)
            }
            bitmap.recycle()
            val ext = if (lossless) "png" else "jpg"
            writeZipStoredEntry(zipOut, stream.toByteArray(), String.format("%04d.%s", index + 1, ext))
        }
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
                var nativePages: List<Pair<String, ByteArray>?>? = null

                // v3.0 DSH: 自适应模式优先走「按 PDF 结构逐页原生无损提取」
                if (currentQuality == QualityMode.ADAPTIVE) {
                    contentResolver.openFileDescriptor(pdfUri, "r")?.use { pfd ->
                        nativePages = extractNativePages(pfd.fileDescriptor, logAndProgress)
                    }
                }

                val extracted = nativePages
                if (extracted != null && extracted.isNotEmpty() && extracted.any { it != null }) {
                    // v3.4 DSH: 混合输出 —— 能直通的页原样写入(字节级无损),
                    // 不能直通的页现场渲染(不丢内容)。
                    logAndProgress(
                        "⚡ [原生无损] 共 ${extracted.size} 页: 原始图像直通 ${extracted.count { it != null }} 页"
                    )
                    contentResolver.openFileDescriptor(pdfUri, "r")?.use { pfd ->
                        PdfRenderer(pfd).use { renderer ->
                            contentResolver.openOutputStream(targetFile.uri)?.use { os ->
                                ZipOutputStream(os.buffered(256 * 1024)).use { zipOut ->
                                    extracted.forEachIndexed { imgIdx, pair ->
                                        if (pair != null) {
                                            writeZipStoredEntry(
                                                zipOut,
                                                pair.second,
                                                String.format("%04d.%s", imgIdx + 1, pair.first)
                                            )
                                        } else {
                                            writeRenderedPage(renderer, imgIdx, currentQuality, zipOut)
                                        }
                                    }
                                }
                            }
                        }
                    }
                } else {
                    logAndProgress("[高清渲染] 正在逐页渲染...")
                    contentResolver.openFileDescriptor(pdfUri, "r")?.use { pfd ->
                        PdfRenderer(pfd).use { renderer ->
                            contentResolver.openOutputStream(targetFile.uri)?.use { os ->
                                ZipOutputStream(os.buffered(256 * 1024)).use { zipOut ->
                                    val pageCount = renderer.pageCount
                                    for (i in 0 until pageCount) {
                                        if (i % 3 == 0 || i == pageCount - 1) {
                                            logAndProgress("正在转换 (${index + 1}/$totalPdfs): $rawName [页码 ${i + 1}/$pageCount]")
                                        }
                                        writeRenderedPage(renderer, i, currentQuality, zipOut)
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
DSH_VERSION_NAME = "3.8.0-dsh"
DSH_VERSION_CODE = 380

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