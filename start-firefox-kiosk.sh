#!/bin/bash
# Firefox Kiosk Startup Script
# Ensures clean Firefox profile with kiosk-optimized defaults

PROFILE_DIR="$HOME/.mozilla/firefox/kiosk-profile"
PROFILE_INI="$HOME/.mozilla/firefox/profiles.ini"

# Remove old Firefox profile to prevent corruption issues
echo "Cleaning old Firefox profile..."
rm -rf "$HOME/.mozilla/firefox"

# Create Firefox directories
mkdir -p "$HOME/.mozilla/firefox"

# Create profiles.ini
cat > "$PROFILE_INI" << 'EOF'
[General]
StartWithLastProfile=1
Version=2

[Profile0]
Name=kiosk-profile
IsRelative=1
Path=kiosk-profile
Default=1
EOF

# Create the profile directory
mkdir -p "$PROFILE_DIR"

# Create prefs.js with kiosk-optimized settings
cat > "$PROFILE_DIR/prefs.js" << 'EOF'
// Kiosk-optimized Firefox preferences
user_pref("browser.startup.homepage", "http://localhost/view");
user_pref("browser.startup.page", 1);
user_pref("browser.shell.checkDefaultBrowser", false);
user_pref("browser.rights.3.shown", true);
user_pref("browser.aboutwelcome.enabled", false);
user_pref("browser.tabs.warnOnClose", false);
user_pref("browser.sessionstore.resume_from_crash", false);
user_pref("toolkit.telemetry.reportingpolicy.firstRun", false);
user_pref("datareporting.policy.dataSubmissionPolicyBypassNotification", true);
user_pref("browser.download.panel.shown", true);
user_pref("browser.download.useDownloadDir", true);
user_pref("security.sandbox.content.level", 0);
user_pref("browser.cache.disk.enable", false);
user_pref("browser.cache.memory.enable", true);
user_pref("browser.cache.memory.capacity", 65536);
user_pref("permissions.default.microphone", 2);
user_pref("permissions.default.camera", 2);
user_pref("permissions.default.geo", 2);
user_pref("permissions.default.desktop-notification", 2);
EOF

# Create user.js for additional settings
cat > "$PROFILE_DIR/user.js" << 'EOF'
// Disable crash reporting and updates
user_pref("browser.crashReports.unsubmittedCheck.enabled", false);
user_pref("app.update.enabled", false);
user_pref("app.update.auto", false);
EOF

# Start unclutter in background
unclutter -idle 0.1 -root &

# Launch Firefox in kiosk mode with the profile
exec firefox --kiosk --profile "$PROFILE_DIR" http://localhost/view
