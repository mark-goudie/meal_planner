# Capacitor iOS Wrapper — Design Spec

**Date:** 2026-04-02
**Status:** In Progress

## Overview

Wrap the existing Django web app (deployed at Railway) in a native iOS shell using Capacitor. The Django app stays exactly as-is — Capacitor creates a WebView that loads the Railway URL. This gives us App Store distribution, native splash screen, app icon, and future native capabilities.

## Architecture

```
┌─────────────────────────┐
│   iOS App (Capacitor)   │
│  ┌───────────────────┐  │
│  │     WKWebView     │  │
│  │                   │  │
│  │  Loads Railway    │  │
│  │  URL via HTTPS    │  │
│  │                   │  │
│  └───────────────────┘  │
│  Native: splash, icon,  │
│  status bar, push tokens │
└─────────────────────────┘
         │ HTTPS
         ▼
┌─────────────────────────┐
│  Railway (Django 5.2)   │
│  PostgreSQL, Gunicorn   │
└─────────────────────────┘
```

## What Capacitor Provides

- **WKWebView** — loads our Railway URL in a native container
- **App icon** — uses our existing 1024x1024 icon
- **Splash screen** — native iOS launch screen (replaces web splash)
- **Status bar** — integrates with iOS status bar (dark theme)
- **No browser chrome** — no URL bar, no tabs, pure app experience
- **App Store distribution** — submit via Xcode/App Store Connect
- **TestFlight** — beta testing before public launch

## Project Structure

```
meal_planner/
├── native/                    # Capacitor project (new)
│   ├── package.json           # npm dependencies
│   ├── capacitor.config.ts    # Capacitor configuration
│   ├── www/                   # Minimal web shell (redirects to Railway)
│   │   └── index.html         # Loading screen → redirect
│   └── ios/                   # Generated Xcode project
│       └── App/
│           ├── App/
│           │   ├── Assets.xcassets/  # App icons
│           │   └── Info.plist        # iOS config
│           └── App.xcodeproj
├── recipes/                   # Existing Django app (unchanged)
└── ...
```

## Capacitor Configuration

```typescript
// capacitor.config.ts
import { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.goudie.mealplanner',
  appName: 'Meal Planner',
  webDir: 'www',
  server: {
    url: 'https://exciting-analysis-production-29fa.up.railway.app',
    cleartext: false,
  },
  ios: {
    scheme: 'Meal Planner',
    backgroundColor: '#1a1a2e',
  },
  plugins: {
    SplashScreen: {
      launchAutoHide: true,
      backgroundColor: '#1a1a2e',
      showSpinner: false,
      launchShowDuration: 1500,
    },
    StatusBar: {
      style: 'DARK',
      backgroundColor: '#1a1a2e',
    },
  },
};

export default config;
```

## Key Decisions

### App ID
`com.goudie.mealplanner` — follows reverse-domain convention. Must be unique in the App Store.

### Server URL
Points to the Railway deployment. When the user opens the app, Capacitor loads this URL in a native WebView. All authentication, HTMX, Alpine.js work exactly as they do in the browser.

### www/ directory
Capacitor requires a web directory. We use a minimal `index.html` that shows a loading state and redirects to the Railway URL. This is only used as a fallback — the `server.url` config makes Capacitor go directly to Railway.

### Offline handling
When offline, the service worker we already built kicks in — cached recipes are available, and the offline fallback page shows for uncached content. This works inside the Capacitor WebView the same way it works in Safari.

## Setup Steps

1. Initialize npm project in `native/`
2. Install Capacitor: `npm install @capacitor/core @capacitor/cli @capacitor/ios`
3. Create `capacitor.config.ts`
4. Create minimal `www/index.html`
5. Run `npx cap add ios` — generates Xcode project
6. Generate app icon (1024x1024) and add to Xcode assets
7. Configure launch screen in Xcode (dark background + icon)
8. Build and test in Xcode simulator
9. Test on physical device via Xcode
10. Archive and upload to App Store Connect
11. Submit for TestFlight beta testing
12. Submit for App Store review

## Prerequisites

- [x] Xcode installed
- [x] Node.js installed
- [ ] Apple Developer Account ($99/year)
- [x] App deployed to Railway with HTTPS
- [x] App icon (512x512 exists, need 1024x1024)
- [x] Privacy Policy URL (/privacy/)
- [x] Terms of Service URL (/terms/)

## App Store Metadata Needed

- **App Name:** Meal Planner
- **Subtitle:** Your living cookbook
- **Category:** Food & Drink
- **Description:** Plan weekly meals, cook step-by-step, shop with a shared list. AI-powered recipe generation and URL import. Share with your household.
- **Keywords:** meal planner, recipe, cooking, shopping list, meal prep, weekly menu, family dinner
- **Screenshots:** 6.7" (iPhone 15 Pro Max) and 6.5" (iPhone 14 Plus) — at least 3 per size
- **Privacy Policy URL:** https://exciting-analysis-production-29fa.up.railway.app/privacy/
