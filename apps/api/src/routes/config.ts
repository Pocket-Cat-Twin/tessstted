import { Elysia, t } from "elysia";
import { db, config, faqs, eq, asc, sql } from "@lolita-fashion/db";
import {
  configUpdateSchema,
  faqCreateSchema,
  faqUpdateSchema,
} from "@lolita-fashion/shared";
import { requireAdmin } from "../middleware/auth";
import { NotFoundError, ValidationError } from "../middleware/error";

export const configRoutes = new Elysia({ prefix: "/config" })

  // Public routes

  // Get public configuration (non-sensitive values)
  .get(
    "/public",
    async () => {
      const publicConfigs = await db.query.config.findMany({
        where: sql`${config.key} IN ('site_name', 'site_description', 'contact_email', 'contact_phone', 'telegram_link', 'vk_link', 'current_kurs')`,
        columns: {
          key: true,
          value: true,
          description: true,
        },
      });

      // Convert to key-value object
      const configObject = publicConfigs.reduce(
        (acc, cfg) => {
          acc[cfg.key] = cfg.value;
          return acc;
        },
        {} as Record<string, string>,
      );

      return {
        success: true,
        data: { config: configObject },
      };
    },
    {
      detail: {
        summary: "Get public configuration",
        tags: ["Config"],
      },
    },
  )

  // Get current currency rate
  .get(
    "/kurs",
    async () => {
      const kursConfig = await db.query.config.findFirst({
        where: eq(config.key, "current_kurs"),
      });

      const kurs = kursConfig ? parseFloat(kursConfig.value) : 13.5;

      return {
        success: true,
        data: { kurs },
      };
    },
    {
      detail: {
        summary: "Get current currency rate",
        tags: ["Config"],
      },
    },
  )

  // Get FAQ list
  .get(
    "/faq",
    async () => {
      const faqList = await db.query.faqs.findMany({
        where: eq(faqs.isActive, true),
        orderBy: asc(faqs.order),
        columns: {
          id: true,
          question: true,
          answer: true,
          order: true,
        },
      });

      return {
        success: true,
        data: { faqs: faqList },
      };
    },
    {
      detail: {
        summary: "Get FAQ list",
        tags: ["Config"],
      },
    },
  )

  // Admin routes
  .use(requireAdmin)

  // Update currency rate (admin)
  .put(
    "/kurs",
    async ({ body }) => {
      const { kurs } = body;

      // Validate kurs value
      if (typeof kurs !== "number" || kurs <= 0) {
        throw new ValidationError("Currency rate must be a positive number");
      }

      // Update or create the currency rate config
      const existingKurs = await db.query.config.findFirst({
        where: eq(config.key, "current_kurs"),
      });

      if (existingKurs) {
        // Update existing
        await db
          .update(config)
          .set({
            value: kurs.toString(),
            updatedAt: new Date(),
          })
          .where(eq(config.key, "current_kurs"));
      } else {
        // Create new
        await db.insert(config).values({
          key: "current_kurs",
          value: kurs.toString(),
          description: "Current exchange rate from CNY to RUB",
          type: "number",
        });
      }

      return {
        success: true,
        message: "Currency rate updated successfully",
        data: { kurs },
      };
    },
    {
      body: t.Object({
        kurs: t.Number({ minimum: 0.01, maximum: 1000 }),
      }),
      detail: {
        summary: "Update currency rate (Admin)",
        description: "Update the current exchange rate from CNY to RUB",
        tags: ["Config"],
      },
    },
  )

  // Get currency rate history (admin)
  .get(
    "/kurs/history",
    async ({ query }) => {
      const limit = parseInt(query.limit || "10") || 10;

      // For now, we'll create a simple history from the config table
      // In future, you might want a dedicated currency_history table
      const kursConfig = await db.query.config.findFirst({
        where: eq(config.key, "current_kurs"),
      });

      const currentRate = kursConfig ? parseFloat(kursConfig.value) : 13.5;

      // Mock history data - in reality you'd store rate changes with timestamps
      const history = [
        {
          date: kursConfig?.updatedAt || new Date(),
          rate: currentRate,
          updatedBy: "admin",
        },
      ];

      return {
        success: true,
        data: {
          currentRate,
          history: history.slice(0, limit),
        },
      };
    },
    {
      query: t.Object({
        limit: t.Optional(t.String()),
      }),
      detail: {
        summary: "Get currency rate history (Admin)",
        description: "Get history of currency rate changes",
        tags: ["Config"],
      },
    },
  )

  // Commission Settings Management

  // Get commission settings
  .get(
    "/commission",
    async () => {
      const commissionSettings = await db.query.config.findMany({
        where: sql`${config.key} LIKE 'commission_%'`,
      });

      // Default commission settings based on the technical specification
      const defaultSettings = {
        commission_low_threshold: "100", // Items < 100 CNY
        commission_low_rate: "0.10", // 10% markup
        commission_standard_threshold: "1000", // Items 100-1000 CNY
        commission_standard_rate: "0.15", // 15% markup
        commission_high_flat_fee: "15", // Items > 1000 CNY: +15 CNY
      };

      // Convert to object with current values or defaults
      const settings = { ...defaultSettings };
      commissionSettings.forEach((setting) => {
        if (setting.key in settings) {
          (settings as any)[setting.key] = setting.value;
        }
      });

      return {
        success: true,
        data: {
          settings,
          description: {
            commission_low_threshold:
              "Price threshold for low commission rate (CNY)",
            commission_low_rate:
              "Commission rate for items below low threshold (decimal)",
            commission_standard_threshold:
              "Price threshold for standard commission rate (CNY)",
            commission_standard_rate:
              "Commission rate for items in standard range (decimal)",
            commission_high_flat_fee:
              "Flat fee for items above high threshold (CNY)",
          },
        },
      };
    },
    {
      detail: {
        summary: "Get commission settings (Admin)",
        description: "Get current commission calculation settings",
        tags: ["Config"],
      },
    },
  )

  // Update commission settings
  .put(
    "/commission",
    async ({ body }) => {
      const { settings } = body;

      // Validate settings
      const allowedKeys = [
        "commission_low_threshold",
        "commission_low_rate",
        "commission_standard_threshold",
        "commission_standard_rate",
        "commission_high_flat_fee",
      ];

      for (const [key, value] of Object.entries(settings)) {
        if (!allowedKeys.includes(key)) {
          throw new ValidationError(`Invalid commission setting key: ${key}`);
        }

        const numValue = parseFloat(value as string);
        if (isNaN(numValue) || numValue < 0) {
          throw new ValidationError(
            `Commission setting ${key} must be a positive number`,
          );
        }

        // Check if setting exists
        const existingSetting = await db.query.config.findFirst({
          where: eq(config.key, key),
        });

        if (existingSetting) {
          // Update existing
          await db
            .update(config)
            .set({
              value: value as string,
              updatedAt: new Date(),
            })
            .where(eq(config.key, key));
        } else {
          // Create new
          await db.insert(config).values({
            key,
            value: value as string,
            description: `Commission setting: ${key}`,
            type: "number",
          });
        }
      }

      return {
        success: true,
        message: "Commission settings updated successfully",
        data: { settings },
      };
    },
    {
      body: t.Object({
        settings: t.Record(t.String(), t.Union([t.String(), t.Number()])),
      }),
      detail: {
        summary: "Update commission settings (Admin)",
        description: "Update commission calculation settings",
        tags: ["Config"],
      },
    },
  )

  // Test commission calculation with current settings
  .post(
    "/commission/calculate",
    async ({ body }) => {
      const { priceYuan, exchangeRate } = body;

      // Get current settings
      const commissionSettings = await db.query.config.findMany({
        where: sql`${config.key} LIKE 'commission_%'`,
      });

      // Build settings object
      const settings = {
        lowThreshold: 100,
        lowRate: 0.1,
        standardThreshold: 1000,
        standardRate: 0.15,
        highFlatFee: 15,
      };

      commissionSettings.forEach((setting) => {
        switch (setting.key) {
          case "commission_low_threshold":
            settings.lowThreshold = parseFloat(setting.value);
            break;
          case "commission_low_rate":
            settings.lowRate = parseFloat(setting.value);
            break;
          case "commission_standard_threshold":
            settings.standardThreshold = parseFloat(setting.value);
            break;
          case "commission_standard_rate":
            settings.standardRate = parseFloat(setting.value);
            break;
          case "commission_high_flat_fee":
            settings.highFlatFee = parseFloat(setting.value);
            break;
        }
      });

      // Calculate commission using current settings
      const originalPriceRuble = priceYuan * exchangeRate;
      let finalPriceRuble: number;
      let commissionYuan: number;
      let commissionRate: number;
      let calculationType: string;

      if (priceYuan < settings.lowThreshold) {
        finalPriceRuble = originalPriceRuble * (1 + settings.lowRate);
        commissionRate = settings.lowRate;
        commissionYuan = priceYuan * settings.lowRate;
        calculationType = "percentage_low";
      } else if (
        priceYuan >= settings.lowThreshold &&
        priceYuan <= settings.standardThreshold
      ) {
        finalPriceRuble = originalPriceRuble * (1 + settings.standardRate);
        commissionRate = settings.standardRate;
        commissionYuan = priceYuan * settings.standardRate;
        calculationType = "percentage_standard";
      } else {
        commissionYuan = settings.highFlatFee;
        finalPriceRuble = (priceYuan + commissionYuan) * exchangeRate;
        commissionRate = commissionYuan / priceYuan;
        calculationType = "flat_fee_high";
      }

      const commissionRuble = commissionYuan * exchangeRate;

      return {
        success: true,
        data: {
          input: { priceYuan, exchangeRate },
          result: {
            originalPriceYuan: priceYuan,
            originalPriceRuble: Number(originalPriceRuble.toFixed(2)),
            commissionYuan: Number(commissionYuan.toFixed(2)),
            commissionRuble: Number(commissionRuble.toFixed(2)),
            finalPriceRuble: Number(finalPriceRuble.toFixed(2)),
            commissionRate: Number(commissionRate.toFixed(4)),
            calculationType,
          },
          settings,
        },
      };
    },
    {
      body: t.Object({
        priceYuan: t.Number({ minimum: 0.01 }),
        exchangeRate: t.Number({ minimum: 0.01 }),
      }),
      detail: {
        summary: "Test commission calculation (Admin)",
        description: "Calculate commission with current settings for testing",
        tags: ["Config"],
      },
    },
  )

  // Get all configuration
  .get(
    "/",
    async () => {
      const configs = await db.query.config.findMany({
        orderBy: asc(config.key),
      });

      return {
        success: true,
        data: { configs },
      };
    },
    {
      detail: {
        summary: "Get all configuration (Admin)",
        tags: ["Config"],
      },
    },
  )

  // Get configuration by key
  .get(
    "/:key",
    async ({ params: { key } }) => {
      const configItem = await db.query.config.findFirst({
        where: eq(config.key, key),
      });

      if (!configItem) {
        throw new NotFoundError("Configuration not found");
      }

      return {
        success: true,
        data: { config: configItem },
      };
    },
    {
      params: t.Object({
        key: t.String(),
      }),
      detail: {
        summary: "Get configuration by key (Admin)",
        tags: ["Config"],
      },
    },
  )

  // Update configuration
  .put(
    "/:key",
    async ({ params: { key }, body }) => {
      const validation = configUpdateSchema.safeParse(body);
      if (!validation.success) {
        throw new ValidationError("Invalid configuration data");
      }

      const { value, description } = validation.data;

      // Find existing config
      const existingConfig = await db.query.config.findFirst({
        where: eq(config.key, key),
      });

      if (!existingConfig) {
        throw new NotFoundError("Configuration not found");
      }

      // Update config
      const [updatedConfig] = await db
        .update(config)
        .set({
          value,
          ...(description && { description }),
          updatedAt: new Date(),
        })
        .where(eq(config.key, key))
        .returning();

      return {
        success: true,
        message: "Configuration updated successfully",
        data: { config: updatedConfig },
      };
    },
    {
      params: t.Object({
        key: t.String(),
      }),
      body: t.Object({
        value: t.String(),
        description: t.Optional(t.String()),
      }),
      detail: {
        summary: "Update configuration (Admin)",
        tags: ["Config"],
      },
    },
  )

  // Create new configuration
  .post(
    "/",
    async ({ body, set }) => {
      const { key, value, description, type } = body as {
        key: string;
        value: string;
        description?: string;
        type?: string;
      };

      // Check if key already exists
      const existingConfig = await db.query.config.findFirst({
        where: eq(config.key, key),
      });

      if (existingConfig) {
        throw new ValidationError("Configuration key already exists");
      }

      // Create config
      const [newConfig] = await db
        .insert(config)
        .values({
          key,
          value,
          description,
          type: (type as any) || "string",
        })
        .returning();

      set.status = 201;
      return {
        success: true,
        message: "Configuration created successfully",
        data: { config: newConfig },
      };
    },
    {
      body: t.Object({
        key: t.String({ minLength: 1 }),
        value: t.String(),
        description: t.Optional(t.String()),
        type: t.Optional(t.String()),
      }),
      detail: {
        summary: "Create configuration (Admin)",
        tags: ["Config"],
      },
    },
  )

  // Delete configuration
  .delete(
    "/:key",
    async ({ params: { key } }) => {
      const configItem = await db.query.config.findFirst({
        where: eq(config.key, key),
      });

      if (!configItem) {
        throw new NotFoundError("Configuration not found");
      }

      // Delete config
      await db.delete(config).where(eq(config.key, key));

      return {
        success: true,
        message: "Configuration deleted successfully",
      };
    },
    {
      params: t.Object({
        key: t.String(),
      }),
      detail: {
        summary: "Delete configuration (Admin)",
        tags: ["Config"],
      },
    },
  )

  // FAQ Management

  // Get all FAQs (admin)
  .get(
    "/faq/all",
    async () => {
      const faqList = await db.query.faqs.findMany({
        orderBy: asc(faqs.order),
      });

      return {
        success: true,
        data: { faqs: faqList },
      };
    },
    {
      detail: {
        summary: "Get all FAQs (Admin)",
        tags: ["Config"],
      },
    },
  )

  // Get FAQ by ID
  .get(
    "/faq/:id",
    async ({ params: { id } }) => {
      const faq = await db.query.faqs.findFirst({
        where: eq(faqs.id, id),
      });

      if (!faq) {
        throw new NotFoundError("FAQ not found");
      }

      return {
        success: true,
        data: { faq },
      };
    },
    {
      params: t.Object({
        id: t.String(),
      }),
      detail: {
        summary: "Get FAQ by ID (Admin)",
        tags: ["Config"],
      },
    },
  )

  // Create FAQ
  .post(
    "/faq",
    async ({ body, set }) => {
      const validation = faqCreateSchema.safeParse(body);
      if (!validation.success) {
        throw new ValidationError("Invalid FAQ data");
      }

      const faqData = validation.data;

      // Create FAQ
      const [newFaq] = await db.insert(faqs).values(faqData).returning();

      set.status = 201;
      return {
        success: true,
        message: "FAQ created successfully",
        data: { faq: newFaq },
      };
    },
    {
      body: t.Object({
        question: t.String({ minLength: 1 }),
        answer: t.String({ minLength: 1 }),
        order: t.Optional(t.Number()),
        isActive: t.Optional(t.Boolean()),
      }),
      detail: {
        summary: "Create FAQ (Admin)",
        tags: ["Config"],
      },
    },
  )

  // Update FAQ
  .put(
    "/faq/:id",
    async ({ params: { id }, body }) => {
      const validation = faqUpdateSchema.safeParse(body);
      if (!validation.success) {
        throw new ValidationError("Invalid FAQ update data");
      }

      const updateData = validation.data;

      // Find existing FAQ
      const existingFaq = await db.query.faqs.findFirst({
        where: eq(faqs.id, id),
      });

      if (!existingFaq) {
        throw new NotFoundError("FAQ not found");
      }

      // Update FAQ
      const [updatedFaq] = await db
        .update(faqs)
        .set({
          ...updateData,
          updatedAt: new Date(),
        })
        .where(eq(faqs.id, id))
        .returning();

      return {
        success: true,
        message: "FAQ updated successfully",
        data: { faq: updatedFaq },
      };
    },
    {
      params: t.Object({
        id: t.String(),
      }),
      body: t.Object({
        question: t.Optional(t.String()),
        answer: t.Optional(t.String()),
        order: t.Optional(t.Number()),
        isActive: t.Optional(t.Boolean()),
      }),
      detail: {
        summary: "Update FAQ (Admin)",
        tags: ["Config"],
      },
    },
  )

  // Delete FAQ
  .delete(
    "/faq/:id",
    async ({ params: { id } }) => {
      const faq = await db.query.faqs.findFirst({
        where: eq(faqs.id, id),
      });

      if (!faq) {
        throw new NotFoundError("FAQ not found");
      }

      // Delete FAQ
      await db.delete(faqs).where(eq(faqs.id, id));

      return {
        success: true,
        message: "FAQ deleted successfully",
      };
    },
    {
      params: t.Object({
        id: t.String(),
      }),
      detail: {
        summary: "Delete FAQ (Admin)",
        tags: ["Config"],
      },
    },
  )

  // Reorder FAQs
  .post(
    "/faq/reorder",
    async ({ body }) => {
      const { faqIds } = body as { faqIds: string[] };

      // Update order for each FAQ
      const updatePromises = faqIds.map((faqId, index) =>
        db
          .update(faqs)
          .set({ order: index + 1, updatedAt: new Date() })
          .where(eq(faqs.id, faqId)),
      );

      await Promise.all(updatePromises);

      return {
        success: true,
        message: "FAQ order updated successfully",
      };
    },
    {
      body: t.Object({
        faqIds: t.Array(t.String()),
      }),
      detail: {
        summary: "Reorder FAQs (Admin)",
        tags: ["Config"],
      },
    },
  );
