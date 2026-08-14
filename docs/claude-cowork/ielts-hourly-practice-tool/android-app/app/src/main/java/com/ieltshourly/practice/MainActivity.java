package com.ieltshourly.practice;

import android.Manifest;
import android.app.Activity;
import android.app.DownloadManager;
import android.content.ClipData;
import android.content.ContentValues;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.provider.MediaStore;
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;
import android.view.Gravity;
import android.view.View;
import android.view.WindowInsets;
import android.window.OnBackInvokedCallback;
import android.window.OnBackInvokedDispatcher;
import android.webkit.CookieManager;
import android.webkit.DownloadListener;
import android.webkit.JavascriptInterface;
import android.webkit.MimeTypeMap;
import android.webkit.RenderProcessGoneDetail;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import java.io.BufferedInputStream;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class MainActivity extends Activity {
    private static final String BASE_URL =
            "https://mtm0101.github.io/public-sites/claude-cowork/ielts-hourly-practice-tool/";
    private static final String INDEX_URL = BASE_URL + "index.html";
    private static final String CACHE_FILE = "ielts-hourly-index.html";
    private static final String RUNTIME_PREFS = "app-runtime";
    private static final String CACHED_APP_VERSION = "cached-app-version";
    private static final int FILE_CHOOSER_REQUEST = 40;
    private static final String NAV_PREFS = "navigation-state";
    private static final String NAV_HASH = "hash";
    private static final String NAV_X = "scroll-x";
    private static final String NAV_Y = "scroll-y";
    private static final String NAV_READER = "reader-state";

    private final ExecutorService ioExecutor = Executors.newSingleThreadExecutor();
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private WebView webView;
    private FrameLayout rootView;
    private FrameLayout loadingLayer;
    private ValueCallback<Uri[]> fileChooserCallback;
    private TextToSpeech textToSpeech;
    private volatile boolean textToSpeechReady;
    private volatile boolean reloadInProgress;
    private boolean restoreOnNextPage = true;
    private boolean reloadDataAfterPageLoad;
    private OnBackInvokedCallback backCallback;
    private volatile boolean destroyed;
    private boolean mediaPermissionRequested;
    private volatile String servedHtml;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        buildUi();
        configureWebView();
        configureNativeNavigationAndSpeech();

        // Never restore WebView state from the Activity Bundle. A WebView loaded
        // from an HTML string can make that Bundle exceed Binder's transaction
        // limit when Android backgrounds the Activity. Compact UI state is
        // restored separately from SharedPreferences after the cached page loads.
        loadCachedToolOnly();
    }

    private void configureNativeNavigationAndSpeech() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            backCallback = this::handleBackNavigation;
            getOnBackInvokedDispatcher().registerOnBackInvokedCallback(
                    OnBackInvokedDispatcher.PRIORITY_DEFAULT, backCallback);
        }

        MediaPlaybackService.setListener(new MediaPlaybackService.Listener() {
            @Override public void onSpeechFinished(String utteranceId, int status) {
                finishNativeSpeech(utteranceId, status);
            }
            @Override public void onMediaControl(String action) {
                dispatchMediaControl(action);
            }
        });
        MediaPlaybackService.initialize(getApplicationContext());
    }

    private void finishTtsInitialization(int status) {
        TextToSpeech engine = textToSpeech;
        if (destroyed || engine == null) {
            textToSpeechReady = false;
            return;
        }
        textToSpeechReady = status == TextToSpeech.SUCCESS;
        if (!textToSpeechReady) return;
        try {
            engine.setSpeechRate(0.95f);
            engine.setOnUtteranceProgressListener(new UtteranceProgressListener() {
                @Override public void onStart(String utteranceId) { }
                @Override public void onStop(String utteranceId, boolean interrupted) {
                    finishNativeSpeech(utteranceId, -1);
                }
                @Override public void onDone(String utteranceId) {
                    finishNativeSpeech(utteranceId, true);
                }
                @Override public void onError(String utteranceId) {
                    finishNativeSpeech(utteranceId, false);
                }
                @Override public void onError(String utteranceId, int errorCode) {
                    finishNativeSpeech(utteranceId, false);
                }
            });
        } catch (RuntimeException error) {
            textToSpeechReady = false;
        }
    }

    private void buildUi() {
        FrameLayout root = rootView = new FrameLayout(this);
        webView = new WebView(this);
        webView.setSaveEnabled(false);
        webView.setSaveFromParentEnabled(false);
        root.addView(webView, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT));

        loadingLayer = new FrameLayout(this);
        loadingLayer.setBackgroundColor(Color.rgb(248, 250, 252));
        ProgressBar spinner = new ProgressBar(this);
        FrameLayout.LayoutParams spinnerParams = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.WRAP_CONTENT,
                FrameLayout.LayoutParams.WRAP_CONTENT,
                Gravity.CENTER);
        spinnerParams.bottomMargin = dp(28);
        loadingLayer.addView(spinner, spinnerParams);

        TextView label = new TextView(this);
        label.setText(R.string.loading_tool);
        label.setTextColor(Color.rgb(71, 85, 105));
        label.setTextSize(15);
        label.setGravity(Gravity.CENTER);
        FrameLayout.LayoutParams labelParams = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.WRAP_CONTENT,
                FrameLayout.LayoutParams.WRAP_CONTENT,
                Gravity.CENTER);
        labelParams.topMargin = dp(58);
        loadingLayer.addView(label, labelParams);
        root.addView(loadingLayer, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT));
        applySafeAreaInsets(root);
        setContentView(root);
        root.requestApplyInsets();
    }

    private void applySafeAreaInsets(View root) {
        root.setOnApplyWindowInsetsListener((view, windowInsets) -> {
            int left;
            int top;
            int right;
            int bottom;

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                android.graphics.Insets safe = windowInsets.getInsets(
                        WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout());
                left = safe.left;
                top = safe.top;
                right = safe.right;
                bottom = safe.bottom;
            } else {
                left = windowInsets.getSystemWindowInsetLeft();
                top = windowInsets.getSystemWindowInsetTop();
                right = windowInsets.getSystemWindowInsetRight();
                bottom = windowInsets.getSystemWindowInsetBottom();

                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P
                        && windowInsets.getDisplayCutout() != null) {
                    android.view.DisplayCutout cutout = windowInsets.getDisplayCutout();
                    left = Math.max(left, cutout.getSafeInsetLeft());
                    top = Math.max(top, cutout.getSafeInsetTop());
                    right = Math.max(right, cutout.getSafeInsetRight());
                    bottom = Math.max(bottom, cutout.getSafeInsetBottom());
                }
            }

            view.setPadding(left, top, right, bottom);
            return windowInsets;
        });
    }

    @SuppressWarnings("SetJavaScriptEnabled")
    private void configureWebView() {
        webView.setSaveEnabled(false);
        webView.setSaveFromParentEnabled(false);
        // Keep the renderer at the app's bound priority while this Activity is
        // backgrounded. Samsung may otherwise reclaim an invisible renderer,
        // forcing a cold reconstruction when the user switches back.
        webView.setRendererPriorityPolicy(WebView.RENDERER_PRIORITY_BOUND, false);
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(true);
        settings.setSupportZoom(true);
        settings.setBuiltInZoomControls(true);
        settings.setDisplayZoomControls(false);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setJavaScriptCanOpenWindowsAutomatically(true);
        settings.setSupportMultipleWindows(true);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);

        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(webView, true);
        WebView.setWebContentsDebuggingEnabled((getApplicationInfo().flags
                & android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE) != 0);

        webView.addJavascriptInterface(new DownloadBridge(), "AndroidDownloads");
        webView.addJavascriptInterface(new AndroidHostBridge(), "AndroidHost");
        webView.setWebViewClient(new ToolWebViewClient());
        webView.setWebChromeClient(new ToolWebChromeClient());
        webView.setDownloadListener(new ToolDownloadListener());
    }

    private void loadCachedToolOnly() {
        ioExecutor.execute(() -> {
            SharedPreferences runtime = getSharedPreferences(RUNTIME_PREFS, MODE_PRIVATE);
            int cachedVersion = runtime.getInt(CACHED_APP_VERSION, -1);
            int appVersion = getAppVersionCode();
            String html = cachedVersion == appVersion ? readCache() : null;
            if (html == null) {
                html = readAssetFallback();
                try {
                    writeCache(html);
                    runtime.edit().putInt(CACHED_APP_VERSION, appVersion).commit();
                } catch (Exception ignored) { }
            }
            final String page = html;
            mainHandler.post(() -> {
                if (!destroyed && webView != null) loadToolHtml(page);
            });
        });
    }

    private int getAppVersionCode() {
        try {
            return (int) getPackageManager().getPackageInfo(getPackageName(), 0).getLongVersionCode();
        } catch (Exception ignored) {
            return 0;
        }
    }
    private void loadToolHtml(String html) {
        restoreOnNextPage = true;
        servedHtml = prepareHtmlForAndroid(html);
        // Loading the normal URL keeps only a small URL in WebView history. The
        // client below supplies the private cached HTML without a network fetch.
        webView.loadUrl(INDEX_URL);
    }

    private String prepareHtmlForAndroid(String html) {
        String automaticReload = "if(!S.speaking.length) await reloadData(true);";
        String manualOnly = "if(!S.speaking.length) "
                + "console.info('[Android] Waiting for Reload data.');";
        String sectionLoop = "scopeEl.classList.add('section-read-active');\n"
                + "  let i=0;\n  while(i<units.length){";
        String directSectionLoop = "scopeEl.classList.add('section-read-active');\n"
                + "  let i=(Number.isFinite(window.__androidStartIndex)"
                + "&&window.__androidStartIndex>=0)"
                + "?Math.min(window.__androidStartIndex,units.length-1):0;"
                + "window.__androidStartIndex=-1;\n  while(i<units.length){";
        return html
                .replace(sectionLoop, directSectionLoop)
                .replace(sectionLoop.replace("\n", "\r\n"), directSectionLoop)
                .replace(automaticReload, manualOnly)
                .replace("await probeAppEditedAt();",
                        "console.info('[Android] HTML probe waits for Reload data.');")
                .replace("loadDolManifestStats().then(()=>renderHero()).catch(()=>{});",
                        "console.info('[Android] DOL stats wait for Reload data.');");
    }

    private String fetchCurrentIndex() throws Exception {
        URL url = new URL(INDEX_URL + "?android=" + System.currentTimeMillis());
        HttpURLConnection connection = (HttpURLConnection) url.openConnection();
        connection.setConnectTimeout(7000);
        connection.setReadTimeout(12000);
        connection.setUseCaches(false);
        connection.setRequestProperty("Cache-Control", "no-cache, no-store");
        connection.setRequestProperty("Accept", "text/html");
        connection.setRequestProperty("User-Agent", "IELTSHourlyAndroid/1.0");
        try {
            int status = connection.getResponseCode();
            if (status < 200 || status >= 300) {
                throw new IllegalStateException("HTTP " + status);
            }
            String html = readUtf8(connection.getInputStream());
            if (!html.toLowerCase(Locale.US).contains("id=\"reloadbtn\"")
                    || !html.contains("ielts-practice-tool")) {
                throw new IllegalStateException("Unexpected page content");
            }
            return html;
        } finally {
            connection.disconnect();
        }
    }

    private String readCache() {
        File file = new File(getFilesDir(), CACHE_FILE);
        if (!file.isFile()) return null;
        try (InputStream input = new FileInputStream(file)) {
            return readUtf8(input);
        } catch (Exception ignored) {
            return null;
        }
    }

    private String readAssetFallback() {
        try (InputStream input = getAssets().open("fallback-index.html")) {
            return readUtf8(input);
        } catch (Exception error) {
            throw new IllegalStateException("Bundled IELTS page is missing", error);
        }
    }

    private void writeCache(String html) throws Exception {
        File target = new File(getFilesDir(), CACHE_FILE);
        File temporary = new File(getFilesDir(), CACHE_FILE + ".tmp");
        try (FileOutputStream output = new FileOutputStream(temporary)) {
            output.write(html.getBytes(StandardCharsets.UTF_8));
            output.getFD().sync();
        }
        if (target.exists() && !target.delete()) {
            throw new IllegalStateException("Could not replace cached page");
        }
        if (!temporary.renameTo(target)) {
            throw new IllegalStateException("Could not activate cached page");
        }
    }

    private static String readUtf8(InputStream source) throws Exception {
        try (BufferedInputStream input = new BufferedInputStream(source);
             ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[16 * 1024];
            int count;
            while ((count = input.read(buffer)) != -1) {
                output.write(buffer, 0, count);
            }
            return output.toString(StandardCharsets.UTF_8.name());
        }
    }

    private boolean isToolUrl(Uri uri) {
        return "https".equalsIgnoreCase(uri.getScheme())
                && "mtm0101.github.io".equalsIgnoreCase(uri.getHost())
                && uri.getPath() != null
                && uri.getPath().startsWith(
                "/public-sites/claude-cowork/ielts-hourly-practice-tool/");
    }

    private void openExternal(Uri uri) {
        try {
            startActivity(new Intent(Intent.ACTION_VIEW, uri));
        } catch (Exception error) {
            Toast.makeText(this, "No app can open this link.", Toast.LENGTH_SHORT).show();
        }
    }

    private final class AndroidHostBridge {
        @JavascriptInterface
        public void savePosition(String hash, int x, int y) {
            saveNavigationPosition(hash, x, y);
        }

        @JavascriptInterface
        public void saveUiState(String hash, int x, int y, String readerState) {
            saveNavigationPosition(hash, x, y, readerState);
        }

        @JavascriptInterface
        public void reloadFromUser(String hash, int x, int y) {
            saveNavigationPosition(hash, x, y);
            clearReaderState();
            startUserRequestedReload();
        }

        @JavascriptInterface
        public boolean ttsReady() {
            return MediaPlaybackService.isTtsReadyOrInitializing();
        }

        @JavascriptInterface
        public void speak(String utteranceId, String text, String languageTag) {
            ensureMediaNotificationPermission();
            MediaPlaybackService.speak(getApplicationContext(), utteranceId, text, languageTag);
        }

        @JavascriptInterface
        public void stopSpeech() {
            MediaPlaybackService.stopSpeech(getApplicationContext());
        }

        @JavascriptInterface
        public void updateMediaState(String mode, String title, String subtitle,
                                     boolean playing, long position, long duration) {
            ensureMediaNotificationPermission();
            MediaPlaybackService.update(getApplicationContext(), mode, title, subtitle,
                    playing, position, duration);
        }

        @JavascriptInterface
        public void endMediaSession() {
            MediaPlaybackService.end(getApplicationContext());
        }
    }

    private void ensureMediaNotificationPermission() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU || mediaPermissionRequested
                || checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
                == PackageManager.PERMISSION_GRANTED) return;
        mainHandler.post(() -> {
            if (!destroyed && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
                    != PackageManager.PERMISSION_GRANTED) {
                mediaPermissionRequested = true;
                requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 81);
            }
        });
    }

    private void dispatchMediaControl(String action) {
        if (action == null) return;
        mainHandler.post(() -> {
            if (destroyed || webView == null) return;
            try {
                webView.evaluateJavascript(
                        "if(window.__androidMediaControl)window.__androidMediaControl("
                                + quoteJs(action) + ")", null);
            } catch (RuntimeException ignored) { }
        });
    }

    private void saveNavigationPosition(String hash, int x, int y) {
        saveNavigationPosition(hash, x, y, null);
    }

    private void saveNavigationPosition(String hash, int x, int y, String readerState) {
        String safeHash = hash != null && hash.startsWith("#/") ? hash : "#/";
        SharedPreferences.Editor editor = getSharedPreferences(NAV_PREFS, MODE_PRIVATE).edit()
                .putString(NAV_HASH, safeHash)
                .putInt(NAV_X, Math.max(0, x))
                .putInt(NAV_Y, Math.max(0, y));
        if (readerState != null) editor.putString(NAV_READER, readerState);
        editor.commit();
    }

    private void clearReaderState() {
        getSharedPreferences(NAV_PREFS, MODE_PRIVATE).edit().remove(NAV_READER).apply();
    }

    private void captureCurrentPosition() {
        if (destroyed || webView == null) return;
        try {
            webView.evaluateJavascript(
                    "if(window.__androidSaveUi)window.__androidSaveUi();else AndroidHost.savePosition(location.hash,Math.round(scrollX),Math.round(scrollY))",
                    null);
        } catch (RuntimeException ignored) { }
    }

    private void startUserRequestedReload() {
        if (reloadInProgress) return;
        reloadInProgress = true;
        mainHandler.post(() -> {
            if (!destroyed && loadingLayer != null) loadingLayer.setVisibility(View.VISIBLE);
        });
        ioExecutor.execute(() -> {
            try {
                String html = fetchCurrentIndex();
                writeCache(html);
                mainHandler.post(() -> {
                    if (destroyed || webView == null) return;
                    reloadDataAfterPageLoad = true;
                    loadToolHtml(html);
                });
            } catch (Exception error) {
                mainHandler.post(() -> {
                    reloadInProgress = false;
                    if (destroyed || webView == null) return;
                    loadingLayer.setVisibility(View.GONE);
                    try {
                        webView.evaluateJavascript(
                                "if(typeof reloadData==='function')reloadData(false)", null);
                    } catch (RuntimeException ignored) { }
                    Toast.makeText(MainActivity.this,
                            "HTML update unavailable; reloading lesson data only.",
                            Toast.LENGTH_LONG).show();
                });
            }
        });
    }

    private void speakWithNativeTts(String utteranceId, String text, String languageTag) {
        mainHandler.post(() -> {
            if (destroyed || !textToSpeechReady || textToSpeech == null || text == null || text.trim().isEmpty()) {
                finishNativeSpeech(utteranceId, 0);
                return;
            }
            try {
                Locale locale = Locale.forLanguageTag(
                        languageTag == null || languageTag.isEmpty() ? "en-US" : languageTag);
                int languageResult = textToSpeech.setLanguage(locale);
                if (languageResult == TextToSpeech.LANG_MISSING_DATA
                        || languageResult == TextToSpeech.LANG_NOT_SUPPORTED) {
                    finishNativeSpeech(utteranceId, 0);
                    return;
                }
                int result = textToSpeech.speak(text.trim(), TextToSpeech.QUEUE_ADD,
                        new Bundle(), utteranceId);
                if (result == TextToSpeech.ERROR) finishNativeSpeech(utteranceId, 0);
            } catch (RuntimeException error) {
                textToSpeechReady = false;
                finishNativeSpeech(utteranceId, 0);
            }
        });
    }

    private void finishNativeSpeech(String utteranceId, boolean success) {
        finishNativeSpeech(utteranceId, success ? 1 : 0);
    }

    private void finishNativeSpeech(String utteranceId, int status) {
        if (destroyed || utteranceId == null) return;
        mainHandler.post(() -> {
            if (destroyed || webView == null) return;
            try {
                webView.evaluateJavascript(
                        "if(window.__androidTtsDone)window.__androidTtsDone("
                                + quoteJs(utteranceId) + "," + status + ")", null);
            } catch (RuntimeException ignored) { }
        });
    }

    private void handleBackNavigation() {
        captureCurrentPosition();
        if (webView != null && webView.canGoBack()) {
            restoreOnNextPage = false;
            webView.goBack();
        } else {
            moveTaskToBack(true);
        }
    }

    private void installAndroidRuntime() {
        String script = "(()=>{if(window.__ieltsAndroidRuntime)return;"
                + "window.__ieltsAndroidRuntime=true;"
                + "const oldWord=window.playWordAsync,oldSentence=window.playSentenceAsync,oldStop=window.stopAudio,"
                + "oldDirectWord=window.playWord,oldDirectSentence=window.playSentence;"
                + "const pending=new Map();let sequence=0;"
                + "window.__androidTtsDone=(id,status)=>{const done=pending.get(id);"
                + "if(done){pending.delete(id);done(status);}};"
                + "const nativeSpeak=(text,lang)=>new Promise(resolve=>{"
                + "const id='android-'+Date.now()+'-'+(++sequence);pending.set(id,resolve);"
                + "AndroidHost.speak(id,String(text||''),lang);});"
                + "const directNative=(fallback,text,accent)=>{"
                + "if(!AndroidHost.ttsReady())return fallback(text,accent);AndroidHost.stopSpeech();"
                + "const lang=String(accent||'').toLowerCase()==='uk'?'en-GB':'en-US';"
                + "return nativeSpeak(text,lang).then(status=>status===0?fallback(text,accent):undefined);};"
                + "window.playWord=(text,accent)=>directNative(oldDirectWord,text,accent);"
                + "window.playSentence=(text,accent)=>directNative(oldDirectSentence,text,accent);"
                + "const norm=text=>String(text||'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();"
                + "const skipForResume=text=>{const wantedIndex=Number(window.__androidResumeIndex);"
                + "if(Number.isFinite(wantedIndex)&&wantedIndex>=0&&typeof READER_DOCK!=='undefined'){"
                + "if(READER_DOCK.index<wantedIndex)return true;window.__androidResumeIndex=-1;window.__androidResumeText='';return false;}"
                + "const wanted=window.__androidResumeText||'';if(!wanted)return false;"
                + "if(norm(text)===norm(wanted)){window.__androidResumeText='';return false;}return true;};"
                + "window.playWordAsync=(text,accent)=>{"
                + "if(skipForResume(text))return Promise.resolve();"
                + "if(!AndroidHost.ttsReady())return oldWord(text,accent);"
                + "const lang=String(accent||'').toLowerCase()==='uk'?'en-GB':'en-US';"
                + "return nativeSpeak(text,lang).then(status=>status===0?oldWord(text,accent):undefined);};"
                + "window.playSentenceAsync=(text,accent)=>{"
                + "if(skipForResume(text))return Promise.resolve();"
                + "if(!AndroidHost.ttsReady())return oldSentence(text,accent);"
                + "const lang=String(accent||'').toLowerCase()==='uk'?'en-GB':'en-US';"
                + "return nativeSpeak(text,lang).then(status=>status===0?oldSentence(text,accent):undefined);};"
                + "window.stopAudio=function(){AndroidHost.stopSpeech();"
                + "if(typeof oldStop==='function')return oldStop.apply(this,arguments);};"
                + "const pathFor=element=>{const root=document.getElementById('view'),parts=[];"
                + "while(element&&element!==root){const parent=element.parentElement;if(!parent)return '';"
                + "parts.unshift(Array.prototype.indexOf.call(parent.children,element));element=parent;}"
                + "return element===root?parts.join('.'):'';};"
                + "const readerSnapshot=()=>{let kind='',scope=null,accent='';"
                + "if(typeof SECTION_READ!=='undefined'&&SECTION_READ.active){kind='section';scope=SECTION_READ.scopeEl;accent=SECTION_READ.accent;}"
                + "else if(typeof DOL_READ!=='undefined'&&DOL_READ.active){kind='dol';scope=DOL_READ.scopeEl;accent=DOL_READ.accent;}"
                + "if(!kind||!scope||typeof READER_DOCK==='undefined')return '';"
                + "const current=READER_DOCK.units&&READER_DOCK.units[READER_DOCK.index];"
                + "return JSON.stringify({kind:kind,path:pathFor(scope),accent:accent||'us',"
                + "text:current&&current.text||'',index:READER_DOCK.index||0,paused:!!READER_DOCK.paused,"
                + "oneOnly:!!READER_DOCK.oneOnly,withExampleSound:READER_DOCK.withExampleSound!==false});};"
                + "const save=()=>AndroidHost.saveUiState(location.hash,Math.round(scrollX),Math.round(scrollY),readerSnapshot());"
                + "window.__androidSaveUi=save;"
                + "document.addEventListener('visibilitychange',()=>{if(document.hidden)save();});"
                + "document.addEventListener('click',event=>{const target=event.target;"
                + "const button=target&&target.closest&&target.closest('#reloadBtn,#globalReloadBtn,#dataReloadBtn,[onclick*=reloadData]');"
                + "if(!button||button.disabled)return;event.preventDefault();event.stopImmediatePropagation();"
                + "save();AndroidHost.reloadFromUser(location.hash,Math.round(scrollX),Math.round(scrollY));"
                + "},true);})()";
        webView.evaluateJavascript(script, ignored -> {
            if (!restoreOnNextPage && !reloadDataAfterPageLoad) return;
            boolean reloadData = reloadDataAfterPageLoad;
            restoreOnNextPage = false;
            reloadDataAfterPageLoad = false;
            reloadInProgress = false;
            restoreNavigationPosition(reloadData);
        });
    }

    private void restoreNavigationPosition(boolean reloadData) {
        SharedPreferences prefs = getSharedPreferences(NAV_PREFS, MODE_PRIVATE);
        String hash = prefs.getString(NAV_HASH, "#/");
        if (hash == null || !hash.startsWith("#/")) hash = "#/";
        int x = Math.max(0, prefs.getInt(NAV_X, 0));
        int y = Math.max(0, prefs.getInt(NAV_Y, 0));
        String readerState = reloadData ? "" : prefs.getString(NAV_READER, "");
        if (readerState == null) readerState = "";
        String script = "(()=>{let attempts=0;const run=async()=>{"
                + "const button=document.getElementById('reloadBtn');"
                + "if((!button||(" + reloadData + "&&button.disabled))&&attempts++<240){setTimeout(run,50);return;}"
                + "history.replaceState(null,''," + quoteJs(INDEX_URL + hash) + ");"
                + "if(typeof route==='function')route();"
                + "const restore=()=>scrollTo(" + x + "," + y + ");"
                + "setTimeout(restore,0);setTimeout(restore,250);setTimeout(restore,800);"
                + (!readerState.isEmpty()
                ? "setTimeout(()=>{let resumeAttempts=0;const resume=()=>{try{const state=JSON.parse(" + quoteJs(readerState) + ");"
                + "const root=document.getElementById('view');let scope=root;"
                + "if(state.path){for(const part of state.path.split('.')){"
                + "scope=scope&&scope.children[Number(part)];}}"
                + "const selector=state.kind==='dol'?'.dol-read-btn':'.section-read-btn';"
                + "const buttons=scope?Array.from(scope.querySelectorAll(selector)):[];"
                + "const accent=String(state.accent||'us').toLowerCase();"
                + "const trigger=buttons.find(b=>String(b.getAttribute('onclick')||'').toLowerCase().includes(\"'\"+accent+\"'\"))||buttons[0];"
                + "if(!trigger){if(resumeAttempts++<240)setTimeout(resume,250);return;}"
                + "const savedIndex=Math.max(0,Number(state.index)||0);"
                + "if(state.kind==='section'){window.__androidStartIndex=savedIndex;window.__androidResumeIndex=-1;window.__androidResumeText='';}"
                + "else{window.__androidStartIndex=-1;window.__androidResumeIndex=savedIndex;window.__androidResumeText=state.text||'';}trigger.click();"
                + "let checks=0;const finish=()=>{if((window.__androidResumeIndex>=0||window.__androidResumeText)&&checks++<600){setTimeout(finish,100);return;}"
                + "window.__androidResumeIndex=-1;window.__androidResumeText='';"
                + "if(typeof READER_DOCK!=='undefined'&&READER_DOCK.active){"
                + "READER_DOCK.oneOnly=!!state.oneOnly;READER_DOCK.withExampleSound=state.withExampleSound!==false;"
                + "if(state.paused&&!READER_DOCK.paused&&typeof readerDockTogglePause==='function')readerDockTogglePause();"
                + "if(typeof readerDockRender==='function')readerDockRender();}restore();};finish();"
                + "}catch(error){window.__androidResumeIndex=-1;window.__androidResumeText='';}};resume();},25);"
                : "")
                + (reloadData
                ? "if(typeof reloadData==='function'){await reloadData(false);setTimeout(restore,100);setTimeout(restore,700);}"
                : "")
                + "};run();})()";
        if (destroyed || webView == null) return;
        try {
            webView.evaluateJavascript(script, null);
        } catch (RuntimeException ignored) { }
    }

    private void recoverFromRendererLoss() {
        if (destroyed || rootView == null) return;
        WebView failedView = webView;
        if (failedView != null) {
            rootView.removeView(failedView);
            try {
                failedView.removeJavascriptInterface("AndroidDownloads");
                failedView.removeJavascriptInterface("AndroidHost");
                failedView.destroy();
            } catch (RuntimeException ignored) { }
        }
        webView = new WebView(this);
        rootView.addView(webView, 0, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT));
        configureWebView();
        loadingLayer.setVisibility(View.VISIBLE);
        loadCachedToolOnly();
    }

    private final class ToolWebViewClient extends WebViewClient {
        @Override
        public WebResourceResponse shouldInterceptRequest(WebView view,
                                                          WebResourceRequest request) {
            Uri uri = request.getUrl();
            String html = servedHtml;
            if (request.isForMainFrame() && html != null
                    && INDEX_URL.equals(uri.buildUpon().fragment(null).query(null).build().toString())) {
                return new WebResourceResponse("text/html", "UTF-8",
                        new ByteArrayInputStream(html.getBytes(StandardCharsets.UTF_8)));
            }
            return super.shouldInterceptRequest(view, request);
        }

        @Override
        public boolean onRenderProcessGone(WebView view, RenderProcessGoneDetail detail) {
            recoverFromRendererLoss();
            return true;
        }

        @Override
        public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
            if (!request.isForMainFrame()) return false;
            Uri uri = request.getUrl();
            if (isToolUrl(uri) || "about".equals(uri.getScheme())) return false;
            openExternal(uri);
            return true;
        }

        @Override
        public void onPageFinished(WebView view, String url) {
            loadingLayer.setVisibility(View.GONE);
            if (restoreOnNextPage) view.clearHistory();
            installAndroidRuntime();
        }
    }

    private final class ToolWebChromeClient extends WebChromeClient {
        @Override
        public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback,
                                         FileChooserParams params) {
            if (fileChooserCallback != null) fileChooserCallback.onReceiveValue(null);
            fileChooserCallback = callback;
            Intent intent = params.createIntent();
            intent.addCategory(Intent.CATEGORY_OPENABLE);
            try {
                startActivityForResult(intent, FILE_CHOOSER_REQUEST);
                return true;
            } catch (Exception error) {
                fileChooserCallback = null;
                Toast.makeText(MainActivity.this,
                        "No file picker is available.", Toast.LENGTH_SHORT).show();
                return false;
            }
        }

        @Override
        public boolean onCreateWindow(WebView view, boolean isDialog,
                                      boolean isUserGesture, android.os.Message resultMsg) {
            WebView popup = new WebView(MainActivity.this);
            popup.setWebViewClient(new WebViewClient() {
                @Override
                public boolean shouldOverrideUrlLoading(WebView child, WebResourceRequest request) {
                    openExternal(request.getUrl());
                    child.destroy();
                    return true;
                }
            });
            WebView.WebViewTransport transport = (WebView.WebViewTransport) resultMsg.obj;
            transport.setWebView(popup);
            resultMsg.sendToTarget();
            return true;
        }
    }

    private final class ToolDownloadListener implements DownloadListener {
        @Override
        public void onDownloadStart(String url, String userAgent, String contentDisposition,
                                    String mimeType, long contentLength) {
            String name = android.webkit.URLUtil.guessFileName(url, contentDisposition, mimeType);
            if (url.startsWith("blob:") || url.startsWith("data:")) {
                downloadBlob(url, mimeType, name);
                return;
            }
            try {
                DownloadManager.Request request = new DownloadManager.Request(Uri.parse(url));
                String cookies = CookieManager.getInstance().getCookie(url);
                if (cookies != null) request.addRequestHeader("Cookie", cookies);
                request.addRequestHeader("User-Agent", userAgent);
                request.setTitle(name);
                request.setMimeType(mimeType);
                request.setNotificationVisibility(
                        DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
                request.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, name);
                ((DownloadManager) getSystemService(DOWNLOAD_SERVICE)).enqueue(request);
                Toast.makeText(MainActivity.this,
                        "Downloading " + name, Toast.LENGTH_SHORT).show();
            } catch (Exception error) {
                Toast.makeText(MainActivity.this,
                        "Download could not start.", Toast.LENGTH_SHORT).show();
            }
        }
    }

    private void downloadBlob(String url, String mimeType, String name) {
        String script = "(async()=>{try{" +
                "const r=await fetch(" + quoteJs(url) + ");" +
                "const b=await r.blob();const a=new Uint8Array(await b.arrayBuffer());" +
                "let s='';for(let i=0;i<a.length;i+=32768){" +
                "s+=String.fromCharCode.apply(null,a.subarray(i,i+32768));}" +
                "AndroidDownloads.saveBase64(btoa(s)," + quoteJs(mimeType) + "," +
                quoteJs(name) + ");}catch(e){AndroidDownloads.failed();}})()";
        webView.evaluateJavascript(script, null);
    }

    private static String quoteJs(String text) {
        if (text == null) return "\"\"";
        return "\"" + text.replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\n", "\\n")
                .replace("\r", "\\r") + "\"";
    }

    private final class DownloadBridge {
        @JavascriptInterface
        public void saveBase64(String base64, String mimeType, String suggestedName) {
            ioExecutor.execute(() -> {
                try {
                    byte[] bytes = android.util.Base64.decode(base64, android.util.Base64.DEFAULT);
                    saveDownload(bytes, mimeType, suggestedName);
                    mainHandler.post(() -> Toast.makeText(MainActivity.this,
                            "Saved to Downloads: " + safeFileName(suggestedName, mimeType),
                            Toast.LENGTH_LONG).show());
                } catch (Exception error) {
                    failed();
                }
            });
        }

        @JavascriptInterface
        public void failed() {
            mainHandler.post(() -> Toast.makeText(MainActivity.this,
                    "Download failed.", Toast.LENGTH_SHORT).show());
        }
    }

    private void saveDownload(byte[] bytes, String mimeType, String suggestedName) throws Exception {
        String name = safeFileName(suggestedName, mimeType);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            ContentValues values = new ContentValues();
            values.put(MediaStore.Downloads.DISPLAY_NAME, name);
            values.put(MediaStore.Downloads.MIME_TYPE,
                    mimeType == null || mimeType.isEmpty() ? "application/octet-stream" : mimeType);
            values.put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS);
            values.put(MediaStore.Downloads.IS_PENDING, 1);
            Uri uri = getContentResolver().insert(
                    MediaStore.Downloads.EXTERNAL_CONTENT_URI, values);
            if (uri == null) throw new IllegalStateException("Could not create download");
            try (OutputStream output = getContentResolver().openOutputStream(uri)) {
                if (output == null) throw new IllegalStateException("Could not open download");
                output.write(bytes);
            }
            values.clear();
            values.put(MediaStore.Downloads.IS_PENDING, 0);
            getContentResolver().update(uri, values, null, null);
        } else {
            File directory = getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS);
            if (directory == null) throw new IllegalStateException("Downloads unavailable");
            try (OutputStream output = new FileOutputStream(new File(directory, name))) {
                output.write(bytes);
            }
        }
    }

    private static String safeFileName(String suggestedName, String mimeType) {
        String name = suggestedName == null ? "ielts-hourly-data" : suggestedName;
        name = name.replaceAll("[^a-zA-Z0-9._ -]", "_").trim();
        if (name.isEmpty()) name = "ielts-hourly-data";
        if (!name.contains(".")) {
            String extension = MimeTypeMap.getSingleton().getExtensionFromMimeType(mimeType);
            name += "." + (extension == null ? "json" : extension);
        }
        return name;
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != FILE_CHOOSER_REQUEST || fileChooserCallback == null) return;
        List<Uri> values = new ArrayList<>();
        if (resultCode == RESULT_OK && data != null) {
            if (data.getData() != null) values.add(data.getData());
            ClipData clip = data.getClipData();
            if (clip != null) {
                for (int i = 0; i < clip.getItemCount(); i++) {
                    values.add(clip.getItemAt(i).getUri());
                }
            }
        }
        fileChooserCallback.onReceiveValue(values.isEmpty() ? null : values.toArray(new Uri[0]));
        fileChooserCallback = null;
    }

    @Override
    public void onBackPressed() {
        handleBackNavigation();
    }

    @Override
    protected void onSaveInstanceState(Bundle state) {
        captureCurrentPosition();
        super.onSaveInstanceState(state);
    }

    @Override
    protected void onPause() {
        captureCurrentPosition();
        // Parent sounding and DOL audio intentionally keep the WebView's
        // playback coordinator active while another app or the lock screen is visible.
        try { CookieManager.getInstance().flush(); } catch (RuntimeException ignored) { }
        super.onPause();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (!destroyed && webView != null) {
            try { webView.onResume(); } catch (RuntimeException ignored) { }
            mainHandler.postDelayed(() -> dispatchMediaControl("restore-controls"), 180);
        }
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        if (intent != null && intent.getBooleanExtra("media-open", false)) {
            mainHandler.postDelayed(() -> dispatchMediaControl("restore-controls"), 220);
            mainHandler.postDelayed(() -> dispatchMediaControl("current"), 320);
        }
    }

    @Override
    protected void onDestroy() {
        destroyed = true;
        MediaPlaybackService.setListener(null);
        if (fileChooserCallback != null) fileChooserCallback.onReceiveValue(null);
        if (webView != null) {
            try { webView.removeJavascriptInterface("AndroidDownloads"); } catch (RuntimeException ignored) { }
            try { webView.removeJavascriptInterface("AndroidHost"); } catch (RuntimeException ignored) { }
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU && backCallback != null) {
            try { getOnBackInvokedDispatcher().unregisterOnBackInvokedCallback(backCallback); }
            catch (RuntimeException ignored) { }
        }
        if (textToSpeech != null) {
            try { textToSpeech.stop(); } catch (RuntimeException ignored) { }
            try { textToSpeech.shutdown(); } catch (RuntimeException ignored) { }
            textToSpeech = null;
            textToSpeechReady = false;
        }
        if (webView != null) {
            try { webView.destroy(); } catch (RuntimeException ignored) { }
            webView = null;
        }
        ioExecutor.shutdownNow();
        super.onDestroy();
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
