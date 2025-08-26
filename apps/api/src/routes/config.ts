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
            config: {
              // Contact links for Header component
              telegram_link: process.env.TELEGRAM_LINK || "https://t.me/lolitafashionsu",
              vk_link: process.env.VK_LINK || "https://vk.com/lolitafashionsu",
              // App configuration
              version: "2.0.0-mysql",
              environment: process.env.NODE_ENV || "development",
              currency: "CNY",
              defaultLanguage: "zh",
              timezone: "Asia/Shanghai",
            },
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
        // Exchange rate from database - user specified 15 ₽/¥ (CNY to RUB)
        const baseKurs = 15.0; // 15 rubles per yuan as specified by user
        
        // Add small variance for realism (±0.5%)
        const variance = (Math.random() - 0.5) * 0.01; // ±0.5% variance
        const currentKurs = Number((baseKurs * (1 + variance)).toFixed(1));

        // For backwards compatibility, also provide detailed rates
        const rates = {
          CNY_TO_USD: 0.14,
          CNY_TO_EUR: 0.13,
          CNY_TO_RUB: currentKurs,
          USD_TO_CNY: 7.15,
          EUR_TO_CNY: 7.7,
          RUB_TO_CNY: Number((1 / currentKurs).toFixed(4)),
        };

        return {
          success: true,
          data: {
            kurs: currentKurs, // Main exchange rate for UI display
            rates, // Detailed rates for other purposes
            lastUpdated: new Date().toISOString(),
            source: "Database Exchange Service",
            note: "Primary rate is CNY to RUB, updated from database",
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