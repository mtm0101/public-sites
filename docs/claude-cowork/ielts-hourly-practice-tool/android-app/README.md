# IELTS Hourly Android

A deliberately thin Android WebView wrapper for the existing IELTS Hourly Practice Tool. It is sized responsively by the existing page and targets modern Samsung Ultra devices, including the Galaxy S22 Ultra and S25 Ultra.

## Runtime behavior

- Opening, resuming, switching to, rotating, or backing out of the app never fetches HTML or lesson data.
- The current HTML is cached in private app storage and reused until the user explicitly taps `Reload data`.
- `Reload data` fetches the latest published `index.html`, activates it, and then runs the page's normal manifest/data reload.
- Switching apps preserves the live WebView, active parent-level reader controls, queue position, pause/options state, route, and exact scroll position.
- WebView state is never placed in Android's saved-instance Bundle. Cached HTML is served through URL-only history, avoiding oversized lifecycle transactions even with a large IndexedDB.
- The renderer remains at bound process priority while the app is backgrounded. If Android still reclaims it or recreates the process, the app recovers from its private cached HTML and reconstructs the saved reader and navigation state without a network reload.
- Section readers restart directly at their saved queue index instead of silently replaying earlier items, making cold restoration effectively immediate.
- Ordinary Back navigation uses WebView history, and Back at the root moves the task to the background without destroying it.
- Parent-level reading uses Android TTS completion callbacks so each queued word and sentence finishes before the next begins, with the original web audio as fallback.
- The APK also includes an exact copy of the repository's current `../index.html` as a final first-run fallback.
- The published tool folder is supplied as the WebView base URL, so `Reload data` reads the same `manifest.json` and `data/` paths as the website.
- The original JavaScript's S3 URLs are unchanged. `Save to S3` and reload-time S3 merges therefore use the same bucket and filenames.
- IndexedDB, local storage, cookies, file import, and JSON downloads remain persistent inside the app.

Updating the website's `index.html`, manifest, or study data does not require rebuilding the APK. Tap `Reload data` inside the tool when you want to fetch and activate those updates.

## Two side-by-side apps

The project builds two independently installable variants. They use different package IDs, so Android keeps their IndexedDB, preferences, history, filters, and S3 configuration separate.

- `primary`: **IELTS Hourly**, blue icon, package `com.ieltshourly.practice`, version `1.6.1`
- `secondary`: **IELTS Hourly 2**, purple double-page icon, package `com.ieltshourly.practice.secondary`, version `1.6.2`

Both version names come from the shared `releaseMinor` value in `app/build.gradle`. Increase it once for every release: `1.6.1`/`1.6.2` becomes `1.7.1`/`1.7.2`, then `1.8.1`/`1.8.2`. Android version codes are derived from the same value and remain upgrade-safe.

## Build

Open this folder in Android Studio and build the `app` configuration, or run:

```powershell
.\gradlew.bat assembleRelease
```

One command builds both installable release APKs:

- `app/build/outputs/apk/primary/release/ielts-hourly-primary-release-1.6.1.apk`
- `app/build/outputs/apk/secondary/release/ielts-hourly-secondary-release-1.6.2.apk`

Requirements: JDK 17 and Android SDK 35. The app's minimum Android version is Android 8 (API 26); it targets Android 15 (API 35).

## Refresh the bundled fallback

After a major web update, refreshing the fallback is optional but recommended before producing a new APK:

```powershell
Copy-Item ..\index.html app\src\main\assets\fallback-index.html -Force
```

Normal users receive the current remote HTML only after tapping `Reload data`.
