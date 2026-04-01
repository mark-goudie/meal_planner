import { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "com.goudie.mealplanner",
  appName: "Meal Planner",
  webDir: "www",
  server: {
    // Point to the live Railway deployment
    url: "https://exciting-analysis-production-29fa.up.railway.app",
    cleartext: false,
  },
  ios: {
    scheme: "Meal Planner",
    backgroundColor: "#1a1a2e",
    contentInset: "always",
    preferredContentMode: "mobile",
  },
  plugins: {
    SplashScreen: {
      launchAutoHide: true,
      backgroundColor: "#1a1a2e",
      showSpinner: false,
      launchShowDuration: 1500,
    },
    StatusBar: {
      style: "DARK",
      backgroundColor: "#1a1a2e",
    },
  },
};

export default config;
