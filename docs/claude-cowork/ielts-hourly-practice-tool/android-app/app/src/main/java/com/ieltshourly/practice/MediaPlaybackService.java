package com.ieltshourly.practice;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.media.MediaMetadata;
import android.media.session.MediaSession;
import android.media.session.PlaybackState;
import android.os.Build;
import android.os.Bundle;
import android.os.IBinder;
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;
import android.view.View;
import android.widget.RemoteViews;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public final class MediaPlaybackService extends Service {
    public interface Listener {
        void onSpeechFinished(String utteranceId, int status);
        void onMediaControl(String action);
    }

    private static final String CHANNEL_ID = "study_app_playback";
    private static final int NOTIFICATION_ID = 4102;
    private static final String ACTION_INIT = "com.ieltshourly.practice.INIT_PLAYBACK";
    private static final String ACTION_SPEAK = "com.ieltshourly.practice.SPEAK";
    private static final String ACTION_STOP_SPEECH = "com.ieltshourly.practice.STOP_SPEECH";
    private static final String ACTION_UPDATE = "com.ieltshourly.practice.UPDATE_PLAYBACK";
    private static final String ACTION_END = "com.ieltshourly.practice.END_PLAYBACK";
    private static final String ACTION_CONTROL = "com.ieltshourly.practice.MEDIA_CONTROL";
    private static final String EXTRA_CONTROL = "control";

    private static volatile Listener listener;
    private static volatile boolean ttsFailed;
    private static volatile boolean ttsReady;

    private TextToSpeech textToSpeech;
    private MediaSession mediaSession;
    private String mode = "speech";
    private String title = "Study App";
    private String subtitle = "Parent sounding";
    private boolean playing;
    private long position;
    private long duration;
    private int controlPage;
    private PendingSpeech pendingSpeech;

    private static final class PendingSpeech {
        final String id;
        final String text;
        final String language;
        PendingSpeech(String id, String text, String language) {
            this.id = id;
            this.text = text;
            this.language = language;
        }
    }

    public static void setListener(Listener value) {
        listener = value;
    }

    public static boolean isTtsReadyOrInitializing() {
        return !ttsFailed;
    }

    public static void initialize(Context context) {
        Intent intent = new Intent(context, MediaPlaybackService.class).setAction(ACTION_INIT);
        context.startService(intent);
    }

    public static void speak(Context context, String id, String text, String language) {
        Intent intent = new Intent(context, MediaPlaybackService.class)
                .setAction(ACTION_SPEAK)
                .putExtra("id", id)
                .putExtra("text", text)
                .putExtra("language", language);
        startPlaybackService(context, intent);
    }

    public static void stopSpeech(Context context) {
        Intent intent = new Intent(context, MediaPlaybackService.class).setAction(ACTION_STOP_SPEECH);
        context.startService(intent);
    }

    public static void update(Context context, String mode, String title, String subtitle,
                              boolean playing, long position, long duration) {
        Intent intent = new Intent(context, MediaPlaybackService.class)
                .setAction(ACTION_UPDATE)
                .putExtra("mode", mode)
                .putExtra("title", title)
                .putExtra("subtitle", subtitle)
                .putExtra("playing", playing)
                .putExtra("position", position)
                .putExtra("duration", duration);
        startPlaybackService(context, intent);
    }

    public static void end(Context context) {
        context.startService(new Intent(context, MediaPlaybackService.class).setAction(ACTION_END));
    }

    private static void startPlaybackService(Context context, Intent intent) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) context.startForegroundService(intent);
        else context.startService(intent);
    }

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();
        mediaSession = new MediaSession(this, "StudyAppPlayback");
        mediaSession.setCallback(new MediaSession.Callback() {
            @Override public void onPlay() { dispatchControl("play"); }
            @Override public void onPause() { dispatchControl("pause"); }
            @Override public void onSkipToPrevious() { dispatchControl(directionalControl(-1)); }
            @Override public void onSkipToNext() { dispatchControl(directionalControl(1)); }
            @Override public void onRewind() { dispatchControl(directionalControl(-1)); }
            @Override public void onFastForward() { dispatchControl(directionalControl(1)); }
            @Override public void onSeekTo(long positionMs) {
                dispatchControl("seek-to:" + Math.max(0, positionMs));
            }
            @Override public void onStop() { dispatchControl("cancel"); }
            @Override public void onCustomAction(String action, Bundle extras) {
                dispatchControl(action);
            }
        });
        mediaSession.setActive(true);
        initializeTts();
    }

    private void initializeTts() {
        textToSpeech = new TextToSpeech(getApplicationContext(), status -> {
            ttsReady = status == TextToSpeech.SUCCESS;
            ttsFailed = !ttsReady;
            if (!ttsReady || textToSpeech == null) {
                PendingSpeech failed = pendingSpeech;
                pendingSpeech = null;
                if (failed != null) notifySpeechFinished(failed.id, 0);
                return;
            }
            textToSpeech.setSpeechRate(0.95f);
            textToSpeech.setOnUtteranceProgressListener(new UtteranceProgressListener() {
                @Override public void onStart(String utteranceId) {
                    playing = true;
                    refreshNotification();
                }
                @Override public void onDone(String utteranceId) { completeSpeech(utteranceId, 1); }
                @Override public void onStop(String utteranceId, boolean interrupted) {
                    completeSpeech(utteranceId, -1);
                }
                @Override public void onError(String utteranceId) { completeSpeech(utteranceId, 0); }
                @Override public void onError(String utteranceId, int errorCode) {
                    completeSpeech(utteranceId, 0);
                }
            });
            PendingSpeech queued = pendingSpeech;
            pendingSpeech = null;
            if (queued != null) speakNow(queued);
        });
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent == null) return START_STICKY;
        String action = intent.getAction();
        if (ACTION_SPEAK.equals(action)) {
            PendingSpeech speech = new PendingSpeech(
                    intent.getStringExtra("id"), intent.getStringExtra("text"),
                    intent.getStringExtra("language"));
            if (!"speech".equals(mode)) controlPage = 0;
            mode = "speech";
            title = safe(speech.text, "Parent sounding");
            subtitle = "Parent sounding";
            playing = true;
            startForeground(NOTIFICATION_ID, buildNotification());
            if (ttsReady) speakNow(speech);
            else if (!ttsFailed) pendingSpeech = speech;
            else notifySpeechFinished(speech.id, 0);
        } else if (ACTION_STOP_SPEECH.equals(action)) {
            if (textToSpeech != null) textToSpeech.stop();
            playing = false;
            refreshNotification();
        } else if (ACTION_UPDATE.equals(action)) {
            String nextMode = safe(intent.getStringExtra("mode"), "listening");
            if (!nextMode.equals(mode)) controlPage = 0;
            mode = nextMode;
            title = safe(intent.getStringExtra("title"), "DOL Listening");
            subtitle = safe(intent.getStringExtra("subtitle"), "Study App");
            playing = intent.getBooleanExtra("playing", false);
            position = Math.max(0, intent.getLongExtra("position", 0));
            duration = Math.max(0, intent.getLongExtra("duration", 0));
            startForeground(NOTIFICATION_ID, buildNotification());
        } else if (ACTION_CONTROL.equals(action)) {
            dispatchControl(intent.getStringExtra(EXTRA_CONTROL));
        } else if (ACTION_END.equals(action)) {
            playing = false;
            if (textToSpeech != null) textToSpeech.stop();
            mediaSession.setActive(false);
            stopForeground(true);
            stopSelf();
        }
        return START_STICKY;
    }

    private void speakNow(PendingSpeech speech) {
        if (speech == null || speech.id == null || speech.text == null || speech.text.trim().isEmpty()) {
            if (speech != null) notifySpeechFinished(speech.id, 0);
            return;
        }
        try {
            Locale locale = Locale.forLanguageTag(
                    speech.language == null || speech.language.isEmpty() ? "en-US" : speech.language);
            int languageResult = textToSpeech.setLanguage(locale);
            if (languageResult == TextToSpeech.LANG_MISSING_DATA
                    || languageResult == TextToSpeech.LANG_NOT_SUPPORTED) {
                notifySpeechFinished(speech.id, 0);
                return;
            }
            int result = textToSpeech.speak(speech.text.trim(), TextToSpeech.QUEUE_FLUSH,
                    new Bundle(), speech.id);
            if (result == TextToSpeech.ERROR) notifySpeechFinished(speech.id, 0);
        } catch (RuntimeException error) {
            notifySpeechFinished(speech.id, 0);
        }
    }

    private void completeSpeech(String utteranceId, int status) {
        playing = false;
        refreshNotification();
        notifySpeechFinished(utteranceId, status);
    }

    private void notifySpeechFinished(String utteranceId, int status) {
        Listener current = listener;
        if (current != null && utteranceId != null) current.onSpeechFinished(utteranceId, status);
    }

    private void dispatchControl(String control) {
        if (control == null) return;
        if ("cycle-controls".equals(control)) {
            int count = "listening".equals(mode) ? 3 : 4;
            controlPage = (controlPage + 1) % count;
            refreshNotification();
            return;
        }
        if ("play".equals(control)) playing = true;
        else if ("pause".equals(control)) playing = false;
        refreshNotification();
        Listener current = listener;
        if (current != null) current.onMediaControl(control);
    }

    private String directionalControl(int delta) {
        boolean next = delta > 0;
        if ("listening".equals(mode)) {
            return next ? "next-transcript" : "previous-transcript";
        }
        if (controlPage == 1) return next ? "next-section" : "previous-section";
        if (controlPage == 2) return next ? "example-sound" : "examples";
        if (controlPage == 3) return next ? "current" : "gap";
        return next ? "next" : "previous";
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return;
        NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID, "Study playback", NotificationManager.IMPORTANCE_LOW);
        channel.setDescription("Parent sounding and DOL Listening controls");
        channel.setShowBadge(false);
        getSystemService(NotificationManager.class).createNotificationChannel(channel);
    }

    private Notification.Action mediaAction(int icon, String label, String control, int requestCode) {
        return new Notification.Action.Builder(icon, label,
                controlIntent(control, requestCode)).build();
    }

    private Notification buildNotification() {
        Intent open = new Intent(this, MainActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_CLEAR_TOP)
                .putExtra("media-open", true);
        PendingIntent contentIntent = PendingIntent.getActivity(this, 0, open, pendingFlags());
        boolean listening = "listening".equals(mode);
        int pageCount = listening ? 3 : 4;
        controlPage = Math.floorMod(controlPage, pageCount);
        String pageLabel;
        List<Notification.Action> controls = new ArrayList<>();

        if (listening) {
            pageLabel = controlPage == 1 ? "Transcript" : controlPage == 2 ? "Sections" : "Time";
            controls.add(mediaAction(android.R.drawable.ic_menu_manage,
                    "Controls: " + pageLabel, "cycle-controls", 20));
            controls.add(mediaAction(android.R.drawable.ic_media_previous,
                    "Previous transcript", "previous-transcript", 21));
            controls.add(mediaAction(playing ? android.R.drawable.ic_media_pause : android.R.drawable.ic_media_play,
                    playing ? "Pause" : "Play", playing ? "pause" : "play", 22));
            controls.add(mediaAction(android.R.drawable.ic_media_next,
                    "Next transcript", "next-transcript", 23));
            controls.add(mediaAction(android.R.drawable.ic_menu_mylocation,
                    "Current", "current", 30));
        } else {
            pageLabel = controlPage == 1 ? "Sections" : controlPage == 2 ? "Options"
                    : controlPage == 3 ? "Playback" : "Items";
            controls.add(mediaAction(android.R.drawable.ic_menu_manage,
                    "Controls: " + pageLabel, "cycle-controls", 40));
            if (controlPage == 1) {
                controls.add(mediaAction(android.R.drawable.ic_media_rew,
                        "Previous section", "previous-section", 41));
                controls.add(mediaAction(playing ? android.R.drawable.ic_media_pause : android.R.drawable.ic_media_play,
                        playing ? "Pause" : "Play", playing ? "pause" : "play", 42));
                controls.add(mediaAction(android.R.drawable.ic_media_ff,
                        "Next section", "next-section", 43));
                controls.add(mediaAction(android.R.drawable.ic_menu_mylocation,
                        "Current", "current", 44));
            } else if (controlPage == 2) {
                controls.add(mediaAction(android.R.drawable.ic_menu_view,
                        "With examples", "examples", 45));
                controls.add(mediaAction(playing ? android.R.drawable.ic_media_pause : android.R.drawable.ic_media_play,
                        playing ? "Pause" : "Play", playing ? "pause" : "play", 46));
                controls.add(mediaAction(android.R.drawable.ic_btn_speak_now,
                        "Example sound", "example-sound", 47));
                controls.add(mediaAction(android.R.drawable.ic_menu_recent_history,
                        "One only", "one-only", 48));
            } else if (controlPage == 3) {
                controls.add(mediaAction(android.R.drawable.ic_menu_recent_history,
                        "Gap", "gap", 49));
                controls.add(mediaAction(playing ? android.R.drawable.ic_media_pause : android.R.drawable.ic_media_play,
                        playing ? "Pause" : "Play", playing ? "pause" : "play", 50));
                controls.add(mediaAction(android.R.drawable.ic_menu_mylocation,
                        "Current", "current", 51));
                controls.add(mediaAction(android.R.drawable.ic_menu_close_clear_cancel,
                        "Cancel", "cancel", 52));
            } else {
                controls.add(mediaAction(android.R.drawable.ic_media_previous,
                        "Previous", "previous", 53));
                controls.add(mediaAction(playing ? android.R.drawable.ic_media_pause : android.R.drawable.ic_media_play,
                        playing ? "Pause" : "Play", playing ? "pause" : "play", 54));
                controls.add(mediaAction(android.R.drawable.ic_media_next,
                        "Next", "next", 55));
                controls.add(mediaAction(android.R.drawable.ic_menu_mylocation,
                        "Current", "current", 56));
            }
        }

        long actions = PlaybackState.ACTION_PLAY | PlaybackState.ACTION_PAUSE
                | PlaybackState.ACTION_PLAY_PAUSE | PlaybackState.ACTION_SKIP_TO_PREVIOUS
                | PlaybackState.ACTION_SKIP_TO_NEXT | PlaybackState.ACTION_SEEK_TO
                | PlaybackState.ACTION_FAST_FORWARD | PlaybackState.ACTION_REWIND
                | PlaybackState.ACTION_STOP;
        PlaybackState.Builder playback = new PlaybackState.Builder()
                .setActions(actions)
                .setState(playing ? PlaybackState.STATE_PLAYING : PlaybackState.STATE_PAUSED,
                        position, playing ? 1f : 0f);
        addSystemCustomActions(playback, listening);
        mediaSession.setPlaybackState(playback.build());
        mediaSession.setMetadata(new MediaMetadata.Builder()
                .putString(MediaMetadata.METADATA_KEY_TITLE, title)
                .putString(MediaMetadata.METADATA_KEY_ARTIST, subtitle + " · Controls: " + pageLabel)
                .putLong(MediaMetadata.METADATA_KEY_DURATION, duration)
                .build());

        Notification.Builder builder = new Notification.Builder(this, CHANNEL_ID)
                .setSmallIcon(R.drawable.ic_launcher_foreground)
                .setContentTitle(title)
                .setContentText(subtitle + " · Controls: " + pageLabel)
                .setContentIntent(contentIntent)
                .setOnlyAlertOnce(true)
                .setOngoing(playing)
                .setVisibility(Notification.VISIBILITY_PUBLIC);
        for (Notification.Action control : controls) builder.addAction(control);
        builder.setCustomBigContentView(buildExpandedControls(listening));
        builder.setStyle(new Notification.DecoratedMediaCustomViewStyle()
                .setMediaSession(mediaSession.getSessionToken())
                .setShowActionsInCompactView(1, 2, 3));
        return builder.build();
    }

    private void addSystemCustomActions(PlaybackState.Builder state, boolean listening) {
        if (listening) {
            addSystemCustomAction(state, "previous-transcript", "Previous transcript",
                    android.R.drawable.ic_media_previous);
            addSystemCustomAction(state, "next-transcript", "Next transcript",
                    android.R.drawable.ic_media_next);
            addSystemCustomAction(state, "previous-section", "Previous section",
                    android.R.drawable.ic_media_rew);
            addSystemCustomAction(state, "next-section", "Next section",
                    android.R.drawable.ic_media_ff);
            addSystemCustomAction(state, "current", "Current",
                    android.R.drawable.ic_menu_mylocation);
            addSystemCustomAction(state, "speed", "Playback speed",
                    android.R.drawable.ic_menu_recent_history);
            addSystemCustomAction(state, "jump-step", "Jump seconds",
                    android.R.drawable.ic_menu_recent_history);
        } else {
            addSystemCustomAction(state, "previous-section", "Previous section",
                    android.R.drawable.ic_media_rew);
            addSystemCustomAction(state, "next-section", "Next section",
                    android.R.drawable.ic_media_ff);
            addSystemCustomAction(state, "current", "Current",
                    android.R.drawable.ic_menu_mylocation);
            addSystemCustomAction(state, "examples", "With examples",
                    android.R.drawable.ic_menu_view);
            addSystemCustomAction(state, "example-sound", "Example sound",
                    android.R.drawable.ic_btn_speak_now);
            addSystemCustomAction(state, "one-only", "One only",
                    android.R.drawable.ic_menu_recent_history);
            addSystemCustomAction(state, "gap", "Gap",
                    android.R.drawable.ic_menu_recent_history);
        }
    }

    private void addSystemCustomAction(PlaybackState.Builder state, String action,
                                       String label, int icon) {
        state.addCustomAction(new PlaybackState.CustomAction.Builder(action, label, icon).build());
    }

    private RemoteViews buildExpandedControls(boolean listening) {
        RemoteViews views = new RemoteViews(getPackageName(), R.layout.notification_media_controls);
        views.setTextViewText(R.id.notification_title, title);
        views.setTextViewText(R.id.notification_subtitle,
                subtitle + (listening ? " · Listening controls" : " · Parent sounding controls"));

        bindExpandedControl(views, R.id.control_r1_c1,
                listening ? "Prev transcript" : "Previous",
                listening ? "previous-transcript" : "previous", 101);
        bindExpandedControl(views, R.id.control_r1_c2,
                playing ? "Pause" : "Play", playing ? "pause" : "play", 102);
        bindExpandedControl(views, R.id.control_r1_c3,
                listening ? "Next transcript" : "Next",
                listening ? "next-transcript" : "next", 103);

        bindExpandedControl(views, R.id.control_r2_c1,
                listening ? "Back seconds" : "Prev section",
                listening ? "previous" : "previous-section", 104);
        bindExpandedControl(views, R.id.control_r2_c2, "Current", "current", 105);
        bindExpandedControl(views, R.id.control_r2_c3,
                listening ? "Next seconds" : "Next section",
                listening ? "next" : "next-section", 106);

        if (listening) {
            bindExpandedControl(views, R.id.control_r3_c1,
                    "Prev section", "previous-section", 107);
            bindExpandedControl(views, R.id.control_r3_c2,
                    "Stop", "cancel", 108);
            bindExpandedControl(views, R.id.control_r3_c3,
                    "Next section", "next-section", 109);
            bindExpandedControl(views, R.id.control_r4_c1,
                    listeningSpeedLabel(), "speed", 116);
            bindExpandedControl(views, R.id.control_r4_c2,
                    listeningJumpLabel(), "jump-step", 117);
            bindExpandedControl(views, R.id.control_r4_c3,
                    "Control set", "cycle-controls", 118);
            views.setViewVisibility(R.id.control_row_4, View.VISIBLE);
        } else {
            bindExpandedControl(views, R.id.control_r3_c1,
                    "Examples", "examples", 110);
            bindExpandedControl(views, R.id.control_r3_c2,
                    "Example sound", "example-sound", 111);
            bindExpandedControl(views, R.id.control_r3_c3,
                    "One only", "one-only", 112);
            bindExpandedControl(views, R.id.control_r4_c1,
                    "Gap", "gap", 113);
            bindExpandedControl(views, R.id.control_r4_c2,
                    "Cancel", "cancel", 114);
            bindExpandedControl(views, R.id.control_r4_c3,
                    "Control set", "cycle-controls", 115);
            views.setViewVisibility(R.id.control_row_4, View.VISIBLE);
        }
        return views;
    }

    private String listeningSpeedLabel() {
        for (String part : subtitle.split(" · ")) {
            String value = part.trim();
            if (value.matches("[0-9.]+x")) return "Speed · " + value;
        }
        return "Speed";
    }

    private String listeningJumpLabel() {
        for (String part : subtitle.split(" · ")) {
            String value = part.trim();
            if (value.startsWith("Jump ")) return value;
        }
        return "Jump seconds";
    }

    private void bindExpandedControl(RemoteViews views, int viewId, String label,
                                     String control, int requestCode) {
        views.setTextViewText(viewId, label);
        views.setOnClickPendingIntent(viewId, controlIntent(control, requestCode));
    }

    private PendingIntent controlIntent(String control, int requestCode) {
        Intent intent = new Intent(this, MediaPlaybackService.class)
                .setAction(ACTION_CONTROL)
                .putExtra(EXTRA_CONTROL, control);
        return PendingIntent.getService(this, requestCode, intent, pendingFlags());
    }

    private int pendingFlags() {
        int flags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) flags |= PendingIntent.FLAG_IMMUTABLE;
        return flags;
    }

    private void refreshNotification() {
        try {
            getSystemService(NotificationManager.class).notify(NOTIFICATION_ID, buildNotification());
        } catch (RuntimeException ignored) { }
    }

    private static String safe(String value, String fallback) {
        if (value == null || value.trim().isEmpty()) return fallback;
        String trimmed = value.trim();
        return trimmed.length() > 120 ? trimmed.substring(0, 117) + "..." : trimmed;
    }

    @Override public IBinder onBind(Intent intent) { return null; }

    @Override
    public void onDestroy() {
        if (textToSpeech != null) {
            try { textToSpeech.stop(); } catch (RuntimeException ignored) { }
            try { textToSpeech.shutdown(); } catch (RuntimeException ignored) { }
        }
        ttsReady = false;
        if (mediaSession != null) {
            mediaSession.setActive(false);
            mediaSession.release();
        }
        super.onDestroy();
    }
}
