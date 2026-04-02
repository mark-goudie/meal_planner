# TestFlight Setup Implementation Plan

> **For agentic workers:** This plan involves Xcode UI actions and App Store Connect web configuration — not typical code implementation. Steps use checkbox (`- [ ]`) syntax for tracking. Most steps require Mark to perform actions in Xcode or a browser, with Claude assisting on file edits.

**Goal:** Get the Meal Planner Capacitor app uploaded to TestFlight so Mark and his wife can test on real iPhones and iPads.

**Architecture:** The app is a Capacitor native wrapper (iOS WebView) pointing to the live Railway deployment. We need to: configure Info.plist for App Store compliance, register the app in App Store Connect, archive in Xcode, upload to TestFlight, and add internal testers.

**Tech Stack:** Xcode, App Store Connect, Capacitor 8.3.0, iOS 15.0+ deployment target

---

## Important Context

### What "Personal Team" means
If you see "Mark E Goudie (Personal Team)" in Xcode's signing dropdown, confirm this is your **paid** Apple Developer Program team ($99/year). A free Personal Team cannot upload to TestFlight. The paid program was activated on April 2, 2026 — if it's still processing, Xcode may not show distribution capabilities yet. You can check at https://developer.apple.com/account — look for "Membership" showing "Apple Developer Program."

### Internal vs External TestFlight
- **Internal testers** (you + your wife): No Apple review required. Builds available within minutes of processing. Up to 100 testers.
- **External testers**: Requires Apple beta review (24-48 hours). Not needed for your use case right now.

### The remote URL consideration
Your app loads all content from Railway (`https://exciting-analysis-production-29fa.up.railway.app`). This is fine for TestFlight internal testing — no review gatekeeping. For eventual App Store submission, Apple may reject under Guideline 4.2 (Minimum Functionality) if the app is seen as a simple website wrapper. We'll address this later when you're ready to submit — not now.

---

## Task 1: Update Info.plist for App Store Compliance

**Why:** Without `ITSAppUsesNonExemptEncryption`, every TestFlight build gets stuck in "Missing Compliance" status in App Store Connect and you have to manually clear it each time. Adding it now saves repeated friction.

**Files:**
- Modify: `native/ios/App/App/Info.plist`

- [ ] **Step 1: Add export compliance flag to Info.plist**

Add this key-value pair inside the top-level `<dict>`, before the closing `</dict>`:

```xml
<key>ITSAppUsesNonExemptEncryption</key>
<false/>
```

Your app uses HTTPS (standard TLS) to communicate with Railway — this is exempt encryption, so `false` is correct. This prevents App Store Connect from blocking your build behind a compliance questionnaire.

- [ ] **Step 2: Verify the edit**

Open `native/ios/App/App/Info.plist` and confirm the new key is present and the XML is well-formed (no unclosed tags, key is inside the `<dict>` block).

- [ ] **Step 3: Sync the change to the Xcode project**

```bash
cd /Users/markgoudie/Projects/meal_planner/native && npx cap sync ios
```

This copies the updated config into the iOS project. **You must run this before every archive** if you've changed any Capacitor config or web assets.

- [ ] **Step 4: Commit**

```bash
cd /Users/markgoudie/Projects/meal_planner
git add native/ios/App/App/Info.plist
git commit -m "chore: add export compliance flag to Info.plist for TestFlight"
```

---

## Task 2: Register Your App ID in Apple Developer Portal

**Why:** Before you can create an app record in App Store Connect, the Bundle ID must be registered as an App ID. Automatic signing may have already done this — but if not, you need to do it manually.

- [ ] **Step 1: Check if the App ID already exists**

1. Go to https://developer.apple.com/account/resources/identifiers/list
2. Sign in with your Apple Developer account
3. Look for `com.goudie.mealplanner` in the list

If it's there → skip to Task 3.
If it's not there → continue to Step 2.

- [ ] **Step 2: Register the App ID (only if not already registered)**

1. On the Identifiers page, click the **"+"** button
2. Select **"App IDs"** and click Continue
3. Select **"App"** (not App Clip) and click Continue
4. Fill in:
   - **Description:** `Meal Planner`
   - **Bundle ID:** Select "Explicit" and enter `com.goudie.mealplanner`
5. Under **Capabilities**, leave defaults for now (you can add Push Notifications capability later)
6. Click **Continue**, then **Register**

---

## Task 3: Create the App Record in App Store Connect

**Why:** App Store Connect needs an app record before it can receive uploaded builds. This is where TestFlight lives.

- [ ] **Step 1: Create a new app**

1. Go to https://appstoreconnect.apple.com/apps
2. Click the **"+"** button in the top-left, then **"New App"**
3. Fill in:
   - **Platforms:** check **iOS**
   - **Name:** `Meal Planner` (if taken, try `Meal Planner - Weekly Menu` or similar)
   - **Primary Language:** English (Australia) or English (U.K.)
   - **Bundle ID:** Select `com.goudie.mealplanner` from the dropdown
   - **SKU:** `mealplanner` (internal identifier, not visible to users, must be unique across your apps)
   - **User Access:** Full Access
4. Click **Create**

If the Bundle ID doesn't appear in the dropdown, go back to Task 2 and register it first.

- [ ] **Step 2: Note the Apple ID**

After creation, App Store Connect shows your app's dashboard. Note the **Apple ID** (a numeric ID visible in the App Information section). You won't need it immediately, but it's useful for troubleshooting.

---

## Task 4: Verify Xcode Signing Configuration

**Why:** Signing issues are the #1 cause of failed archive uploads for newcomers. Let's verify everything before archiving.

**Lesson learned:** Xcode shows two teams — "Mark E Goudie (Personal Team)" (free) and your paid Apple Developer Program team. You **must** select the paid team, not the Personal Team. The free Personal Team cannot distribute to TestFlight.

- [x] **Step 1: Open the project in Xcode**

```bash
open /Users/markgoudie/Projects/meal_planner/native/ios/App/App.xcodeproj
```

- [x] **Step 2: Check signing settings**

1. In the left sidebar (Project Navigator), click on **"App"** (the top-level project, blue icon)
2. In the center pane, select the **"App"** target (under TARGETS, not PROJECT)
3. Click the **"Signing & Capabilities"** tab
4. Verify:
   - **"Automatically manage signing"** is checked
   - **Team** shows your **paid** developer account name — **not** "Personal Team (Free)". You may see two entries for your name; pick the one without "(Personal Team)".
   - **Bundle Identifier** shows `com.goudie.mealplanner`
   - **Signing Certificate** shows "Apple Development" or "Apple Distribution" (not an error)
   - **Provisioning Profile** shows "Xcode Managed Profile" (not an error)

If you see a red error like "No profiles for 'com.goudie.mealplanner' were found":
- Try unchecking and re-checking "Automatically manage signing"
- Ensure your **paid** team is selected (not free Personal Team)
- Xcode may need a moment to download profiles from Apple's servers

- [x] **Step 3: Check the Release signing configuration**

Still in Signing & Capabilities:
1. Look at the top of the signing section — there should be **Debug** and **Release** tabs/segments
2. Click **Release**
3. Verify it also shows your paid team and has no errors
4. The Release config is what gets used when you archive

- [x] **Step 4: Verify version numbers**

1. Click the **"General"** tab (same target)
2. Check:
   - **Version** is `1.0` (this is the user-visible version, `MARKETING_VERSION`)
   - **Build** is `1` (this is the build number, `CURRENT_PROJECT_VERSION`)
3. These are fine for your first upload. You'll increment **Build** for each subsequent upload.

---

## Task 5: Archive the App

**Why:** Archiving creates a signed release build that can be uploaded to TestFlight.

**Lesson learned:** The app icon PNG must not have an alpha channel. If you get "Invalid large app icon... can't be transparent or contain an alpha channel", strip the alpha from the icon PNG (flatten onto solid background) and re-archive.

- [x] **Step 1: Select the correct build destination**

In the Xcode toolbar (top center), click the device/simulator dropdown and select:
- **"Any iOS Device (arm64)"**

You **cannot** archive when a simulator is selected. The "Any iOS Device" option tells Xcode to build for real hardware.

- [x] **Step 2: Run a clean build first (recommended)**

From the menu bar: **Product → Clean Build Folder** (or press `Shift + Cmd + K`).

This avoids stale build artifacts causing issues.

- [x] **Step 3: Archive**

From the menu bar: **Product → Archive**

This will take 1-3 minutes. Xcode compiles a release build, signs it, and creates an archive. When complete, the **Organizer** window opens automatically.

**If the archive fails:** Common causes:
- Signing error → Go back to Task 4 and verify signing
- Build error → Read the error in the Issue Navigator (Cmd + 5). Share the error text and I can help diagnose.

---

## Task 6: Upload to TestFlight

**Why:** This sends the archived build to Apple's servers where TestFlight can distribute it to internal testers.

- [x] **Step 1: Start distribution**

In the Organizer window (if it closed, reopen via **Window → Organizer**):

1. Select your archive (it will be listed with today's date and the version number)
2. Click **"Distribute App"**

- [x] **Step 2: Choose distribution method**

Select **"TestFlight Internal Only"**. This is the simplest path for internal testing — it uploads directly for TestFlight distribution without requiring a full App Store Connect app record.

(The alternative "App Store Connect" option also works but is designed for builds that may also go to the App Store. Use that later when you're ready for public submission.)

- [x] **Step 3: Upload**

Xcode handles signing automatically and uploads the build. This takes 1-5 minutes depending on internet speed.

- [x] **Step 4: Verify in App Store Connect**

After upload succeeds, click **"Show in App Store Connect"** (or go to https://appstoreconnect.apple.com and find your app under the TestFlight tab):
- Your build will show status **"Processing"** — this typically takes 5-30 minutes
- Once processing completes, the status changes to **"Ready to Test"**
- The `ITSAppUsesNonExemptEncryption` flag from Task 1 prevents the build getting stuck in "Missing Compliance"

---

## Task 7: Add Internal Testers and Install

**Why:** Internal testers get builds immediately with no Apple review. This is how you and your wife will test.

- [x] **Step 1: Add yourself as an internal tester**

1. In App Store Connect, go to your app → **TestFlight** tab
2. Click **"Internal Testing"** in the left sidebar
3. Click **"+"** to create a new internal testing group (name it e.g., "Family")
4. Click the group, then **"+"** next to Testers
5. Add your Apple ID email address
6. Your build should automatically be available to this group

- [ ] **Step 2: Add your wife as an App Store Connect user**

Internal testers must be App Store Connect users. To add your wife:

1. Go to https://appstoreconnect.apple.com → **Users and Access**
2. Click **"+"** to add a new user
3. Enter her name and Apple ID email
4. For **Role**, select **"Marketing"** or **"Customer Support"** (these are the least-privileged roles that still allow TestFlight access). Alternatively, **"Developer"** works too.
5. Click **Invite**
6. She'll receive an email invitation — she must accept it

- [ ] **Step 3: Add your wife to the testing group**

1. Go back to your app → **TestFlight** → **Internal Testing** → your group
2. Click **"+"** next to Testers
3. Add her email (she must have accepted the App Store Connect invite first)

- [x] **Step 4: Install TestFlight on your iPhones**

1. On each iPhone, open the App Store and search for **"TestFlight"** (it's a free Apple app)
2. Install it

- [x] **Step 5: Install the Meal Planner build**

1. Open TestFlight on your iPhone
2. You should see "Meal Planner" listed with the build available
3. Tap **"Install"**
4. The app installs on your home screen — you can now use it like any other app

If the app doesn't appear in TestFlight:
- Check that the build finished processing in App Store Connect
- Check that you were added to an internal testing group
- You may receive an email from TestFlight with a link — tapping it on your phone opens TestFlight directly

- [x] **Step 6: Verify the app works on device**

Open the installed app and check:
- Splash screen appears briefly with dark background
- The app loads your Railway deployment
- You can log in and navigate
- The status bar text is visible (white on dark)
- Content doesn't get hidden behind the notch or Dynamic Island (safe area)
- Scrolling feels smooth
- The keyboard doesn't obscure input fields

Note any issues — these will become your next round of improvements.

---

## Post-Setup: What to Know Going Forward

### Uploading new builds
Every time you want to test a change:
1. Deploy your changes to Railway (the app loads remotely, so code changes are instant without re-uploading)
2. If you changed **native config** (Info.plist, Capacitor config, plugins): run `npx cap sync ios`, increment the **Build** number in Xcode General tab, then archive and upload again
3. Internal testers get new builds automatically in TestFlight

### Build number rules
- **Version** (`1.0`): User-visible version string. Change for significant releases.
- **Build** (`1`, `2`, `3`...): Must be unique per version. Increment for every upload. App Store Connect rejects duplicate build numbers.

### Build expiry
TestFlight builds expire after **90 days**. You'll need to upload a fresh build before then if you're still testing.

### Your advantage with a remote URL
Since your app loads from Railway, most changes (new features, bug fixes, styling) are live instantly for TestFlight testers without needing to re-archive and upload. You only need a new build when changing native configuration.
