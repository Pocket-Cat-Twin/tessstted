import { Elysia, t } from "elysia";

// Config routes for application configuration data
export const configRoutes = new Elysia({ prefix: "/config" })

  // Base config endpoint
  .get(
    "/",
    async () => {
      console.log("📋 Fetching base config");
      
      try {
        // Return basic application configuration
        return {
          success: true,
          data: {
            version: "2.0.0-mysql",
            environment: process.env.NODE_ENV || "development",
            features: {
              emailLogin: true,
              phoneLogin: true,
              subscription: true,
              orders: true,
              stories: true,
            },
            limits: {
              maxOrderWeight: 50, // kg
              maxOrderVolume: 2, // cbm
              maxFileSize: 10 * 1024 * 1024, // 10MB
            },
            settings: {
              currency: "CNY",
              defaultLanguage: "zh",
              timezone: "Asia/Shanghai",
            },
          },
        };
      } catch (error) {
        console.error("❌ Config fetch error:", error);
        return {
          success: false,
          error: "CONFIG_FETCH_FAILED",
          message: "Failed to fetch configuration",
        };
      }
    },
    {
      detail: {
        tags: ["Config"],
        summary: "Get base configuration",
        description: "Retrieve basic application configuration settings",
      },
    }
  )

  // Exchange rates endpoint
  .get(
    "/kurs",
    async () => {
      console.log("💱 Fetching exchange rates");
      
      try {
        // Mock exchange rates - in production this would come from external API
        const baseRates = {
          CNY_TO_USD: 0.14,
          CNY_TO_EUR: 0.13,
          CNY_TO_RUB: 12.5,
          USD_TO_CNY: 7.15,
          EUR_TO_CNY: 7.7,
          RUB_TO_CNY: 0.08,
        };

        // Add 1-2% variance for realistic rates
        const rates: Record<string, number> = {};
        for (const [pair, baseRate] of Object.entries(baseRates)) {
          const variance = (Math.random() - 0.5) * 0.02; // ±1% variance
          rates[pair] = Number((baseRate * (1 + variance)).toFixed(4));
        }

        return {
          success: true,
          data: {
            rates,
            lastUpdated: new Date().toISOString(),
            source: "Internal Exchange Service",
            note: "Rates are updated every 30 minutes during business hours",
          },
        };
      } catch (error) {
        console.error("❌ Exchange rates fetch error:", error);
        return {
          success: false,
          error: "EXCHANGE_RATES_FAILED",
          message: "Failed to fetch exchange rates",
        };
      }
    },
    {
      detail: {
        tags: ["Config"],
        summary: "Get exchange rates",
        description: "Retrieve current exchange rates for currency conversion",
      },
    }
  )

  // FAQ endpoint
  .get(
    "/faq",
    async () => {
      console.log("❓ Fetching FAQ data");
      
      try {
        return {
          success: true,
          data: {
            categories: [
              {
                id: "shipping",
                name: "Shipping & Delivery",
                items: [
                  {
                    question: "How long does shipping take?",
                    answer: "Standard shipping takes 7-14 business days, express shipping takes 3-5 business days.",
                  },
                  {
                    question: "What are the shipping costs?",
                    answer: "Shipping costs depend on weight and destination. Use our calculator for exact pricing.",
                  },
                ],
              },
              {
                id: "orders",
                name: "Orders & Payments",
                items: [
                  {
                    question: "How can I track my order?",
                    answer: "You can track your order using the tracking number provided in your email confirmation.",
                  },
                  {
                    question: "What payment methods do you accept?",
                    answer: "We accept major credit cards, PayPal, and bank transfers.",
                  },
                ],
              },
              {
                id: "account",
                name: "Account & Subscription",
                items: [
                  {
                    question: "How do I upgrade my subscription?",
                    answer: "Visit your account page and select the subscription tier you want to upgrade to.",
                  },
                  {
                    question: "Can I cancel my subscription?",
                    answer: "Yes, you can cancel your subscription at any time from your account settings.",
                  },
                ],
              },
            ],
            lastUpdated: new Date().toISOString(),
          },
        };
      } catch (error) {
        console.error("❌ FAQ fetch error:", error);
        return {
          success: false,
          error: "FAQ_FETCH_FAILED", 
          message: "Failed to fetch FAQ data",
        };
      }
    },
    {
      detail: {
        tags: ["Config"],
        summary: "Get FAQ data",
        description: "Retrieve frequently asked questions and answers",
      },
    }
  )

  // Application settings endpoint
  .get(
    "/settings",
    async () => {
      console.log("⚙️ Fetching app settings");
      
      try {
        return {
          success: true,
          data: {
            ui: {
              theme: "lolita-pink",
              showAnimations: true,
              compactMode: false,
            },
            notifications: {
              orderUpdates: true,
              subscriptionAlerts: true,
              promotions: false,
            },
            locale: {
              language: "zh-CN",
              currency: "CNY",
              dateFormat: "YYYY-MM-DD",
              timezone: "Asia/Shanghai",
            },
            features: {
              darkMode: false,
              advancedSearch: true,
              bulkOperations: true,
            },
          },
        };
      } catch (error) {
        console.error("❌ Settings fetch error:", error);
        return {
          success: false,
          error: "SETTINGS_FETCH_FAILED",
          message: "Failed to fetch application settings",
        };
      }
    },
    {
      detail: {
        tags: ["Config"],
        summary: "Get application settings", 
        description: "Retrieve user interface and application configuration settings",
      },
    }
  );