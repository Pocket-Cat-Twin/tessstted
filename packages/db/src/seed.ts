import { db } from "./connection";
import {
  users,
  config,
  faqs,
  emailTemplates,
  orders,
  orderGoods,
  stories,
  customers,
  customerAddresses,
  subscriptionFeatures,
  userSubscriptions,
  blogCategories,
  storyCategoryRelations,
  storyTags,
  storyTagRelations,
} from "./schema";
// Removed unused import: generateRandomString

export async function seedDatabase() {
  console.log("🌱 Seeding database...");
  try {
    // Get or create admin user
    let adminUser = await db.query.users.findFirst({
      where: (users, { eq }) => eq(users.email, "admin@yuyulolita.com"),
    });

    if (!adminUser) {
      const inserted = await db
        .insert(users)
        .values({
          email: "admin@yuyulolita.com",
          password:
            "$2b$12$LQv3c1yqBwlzKzn8.OdKqOGaV9UlwT0jqk1QBgm1eJ8GhGYf9XVCG", // password: admin123
          name: "Администратор",
          fullName: "Администратор Системы",
          registrationMethod: "email",
          role: "admin",
          status: "active",
          emailVerified: true,
          phoneVerified: false,
        })
        .returning();
      adminUser = inserted[0];
      if (!adminUser) {
        throw new Error("Failed to create admin user");
      }
      console.log("✅ Admin user created:", adminUser.email);
    } else {
      console.log("✅ Admin user already exists:", adminUser.email);
    }

    // Get or create regular user
    let regularUser = await db.query.users.findFirst({
      where: (users, { eq }) => eq(users.email, "user@example.com"),
    });

    if (!regularUser) {
      const inserted = await db
        .insert(users)
        .values({
          email: "user@example.com",
          password:
            "$2b$12$LQv3c1yqBwlzKzn8.OdKqOGaV9UlwT0jqk1QBgm1eJ8GhGYf9XVCG", // password: user123
          name: "Анна",
          fullName: "Анна Петровна",
          registrationMethod: "email",
          contactPhone: "+7 (999) 123-45-67",
          role: "user",
          status: "active",
          emailVerified: true,
          phoneVerified: false,
        })
        .returning();
      regularUser = inserted[0];
      if (!regularUser) {
        throw new Error("Failed to create regular user");
      }
      console.log("✅ Regular user created:", regularUser.email);
    } else {
      console.log("✅ Regular user already exists:", regularUser.email);
    }

    // Create a phone-registered user
    let phoneUser = await db.query.users.findFirst({
      where: (users, { eq }) => eq(users.phone, "+79991234568"),
    });

    if (!phoneUser) {
      const inserted = await db
        .insert(users)
        .values({
          phone: "+79991234568",
          password:
            "$2b$12$LQv3c1yqBwlzKzn8.OdKqOGaV9UlwT0jqk1QBgm1eJ8GhGYf9XVCG", // password: user123
          name: "Мария",
          fullName: "Мария Соколова",
          registrationMethod: "phone",
          contactEmail: "maria@example.com",
          role: "user",
          status: "active",
          emailVerified: false,
          phoneVerified: true,
        })
        .returning();
      phoneUser = inserted[0];
      if (!phoneUser) {
        throw new Error("Failed to create phone user");
      }
      console.log("✅ Phone user created:", phoneUser.phone);
    } else {
      console.log("✅ Phone user already exists:", phoneUser.phone);
    }

    // Seed subscription features
    const existingFeatures = await db.query.subscriptionFeatures.findFirst();

    if (!existingFeatures) {
      const subscriptionFeaturesData = [
        {
          tier: "free" as const,
          maxStorageDays: 14,
          processingTimeHours: 120, // 5 рабочих дней
          supportResponseHours: 48,
          canParticipateInPromotions: false,
          canCombineOrders: false,
          hasPriorityProcessing: false,
          hasPersonalSupport: false,
          hasProductInspection: false,
          description:
            "Обычный подписчик (БЕСПЛАТНО) - редкие заказы, знакомство с сервисом",
        },
        {
          tier: "group" as const,
          maxStorageDays: 90, // 3 месяца
          processingTimeHours: 72, // 2–4 рабочих дня
          supportResponseHours: 24,
          canParticipateInPromotions: true,
          canCombineOrders: true,
          hasPriorityProcessing: false,
          hasPersonalSupport: false,
          hasProductInspection: false,
          description:
            "Групповая подписка (990₽/месяц) - накопительные заказы, совместные покупки",
        },
        {
          tier: "elite" as const,
          maxStorageDays: -1, // без ограничений
          processingTimeHours: 24, // быстрая обработка
          supportResponseHours: 12, // быстрые ответы до 12 часов
          canParticipateInPromotions: true,
          canCombineOrders: true,
          hasPriorityProcessing: true,
          hasPersonalSupport: true,
          hasProductInspection: true,
          description:
            "Элитный подписчик (1990₽/месяц) - активные клиенты, ценящие скорость и сервис",
        },
        {
          tier: "vip_temp" as const,
          maxStorageDays: 30,
          processingTimeHours: 12, // экстренная обработка
          supportResponseHours: 6,
          canParticipateInPromotions: false,
          canCombineOrders: true,
          hasPriorityProcessing: true,
          hasPersonalSupport: true,
          hasProductInspection: true,
          description:
            "Разовый VIP-доступ (890₽ на 7 дней) - срочные разовые заказы",
        },
      ];

      await db.insert(subscriptionFeatures).values(subscriptionFeaturesData);
      console.log("✅ Subscription features seeded");
    } else {
      console.log("✅ Subscription features already exist");
    }

    // Create test subscriptions for users
    const existingSubscriptions = await db.query.userSubscriptions.findFirst();

    if (!existingSubscriptions && regularUser && phoneUser) {
      const subscriptionsData = [
        {
          userId: regularUser.id,
          tier: "elite" as const,
          status: "active" as const,
          price: "1990.00",
          startDate: new Date("2024-01-01T00:00:00Z"),
          endDate: new Date("2024-02-01T00:00:00Z"),
          autoRenew: true,
        },
        {
          userId: phoneUser.id,
          tier: "group" as const,
          status: "active" as const,
          price: "990.00",
          startDate: new Date("2024-01-15T00:00:00Z"),
          endDate: new Date("2024-02-15T00:00:00Z"),
          autoRenew: false,
        },
      ];

      await db.insert(userSubscriptions).values(subscriptionsData);
      console.log("✅ Test subscriptions created");
    } else {
      console.log("✅ Test subscriptions already exist");
    }

    // Create test customers
    let testCustomers = await db.query.customers.findMany();

    if (testCustomers.length === 0) {
      // Seed test customers
      const customersData = [
        {
          name: "Анна Петрова",
          email: "anna@example.com",
          phone: "+7 (999) 123-45-67",
        },
        {
          name: "Мария Соколова",
          email: "maria@example.com",
          phone: "+7 (999) 234-56-78",
        },
        {
          name: "Екатерина Волкова",
          email: "kate@example.com",
          phone: "+7 (999) 345-67-89",
        },
        {
          name: "Ольга Лебедева",
          email: "olga@example.com",
          phone: "+7 (999) 456-78-90",
        },
        {
          name: "Светлана Козлова",
          email: "svetlana@example.com",
          phone: "+7 (999) 567-89-01",
        },
      ];

      const insertedCustomers = await db
        .insert(customers)
        .values(customersData)
        .returning();
      
      if (insertedCustomers.length < 5) {
        throw new Error("Failed to create all customers");
      }
      console.log("✅ Test customers created:", insertedCustomers.length);

      // Create addresses for each customer
      const addressesData = [
        {
          customerId: insertedCustomers[0]?.id || "",
          fullAddress: "г. Москва, ул. Ленина, д. 10, кв. 5",
          city: "Москва",
          postalCode: "101000",
          isDefault: true,
        },
        {
          customerId: insertedCustomers[1]?.id || "",
          fullAddress: "г. Санкт-Петербург, Невский пр., д. 25, кв. 12",
          city: "Санкт-Петербург",
          postalCode: "191011",
          isDefault: true,
        },
        {
          customerId: insertedCustomers[2]?.id || "",
          fullAddress: "г. Новосибирск, ул. Красный пр., д. 18, кв. 3",
          city: "Новосибирск",
          postalCode: "630007",
          isDefault: true,
        },
        {
          customerId: insertedCustomers[3]?.id || "",
          fullAddress: "г. Екатеринбург, ул. Малышева, д. 42, кв. 8",
          city: "Екатеринбург",
          postalCode: "620014",
          isDefault: true,
        },
        {
          customerId: insertedCustomers[4]?.id || "",
          fullAddress: "г. Казань, ул. Баумана, д. 7, кв. 15",
          city: "Казань",
          postalCode: "420012",
          isDefault: true,
        },
      ];

      await db.insert(customerAddresses).values(addressesData);
      console.log("✅ Customer addresses created:", addressesData.length);

      testCustomers = insertedCustomers;
    } else {
      console.log("✅ Test customers already exist:", testCustomers.length);
    }

    // Check if config already exists
    const existingConfig = await db.query.config.findFirst();

    if (!existingConfig) {
      // Seed configuration
      const configData = [
        {
          key: "current_kurs",
          value: "13.5",
          description: "Текущий курс юаня к рублю",
          type: "number" as const,
        },
        {
          key: "default_commission_rate",
          value: "0.10",
          description: "Комиссия по умолчанию (10%)",
          type: "number" as const,
        },
        {
          key: "site_name",
          value: "YuYu Lolita Shopping",
          description: "Название сайта",
          type: "string" as const,
        },
        {
          key: "site_description",
          value: "Заказы товаров из Китая с доставкой в Россию",
          description: "Описание сайта",
          type: "string" as const,
        },
        {
          key: "contact_email",
          value: "info@yuyulolita.com",
          description: "Email для связи",
          type: "string" as const,
        },
        {
          key: "contact_phone",
          value: "+7 (999) 123-45-67",
          description: "Телефон для связи",
          type: "string" as const,
        },
        {
          key: "telegram_link",
          value: "https://t.me/YuyuLolitaShopping",
          description: "Ссылка на Telegram",
          type: "string" as const,
        },
        {
          key: "vk_link",
          value: "https://vk.com/yuyulolitashopping",
          description: "Ссылка на VK",
          type: "string" as const,
        },
        {
          key: "max_file_size",
          value: "10485760",
          description: "Максимальный размер файла (10MB)",
          type: "number" as const,
        },
        {
          key: "allowed_file_types",
          value: "image/jpeg,image/jpg,image/png,image/gif,image/webp",
          description: "Разрешенные типы файлов",
          type: "string" as const,
        },
      ];

      await db.insert(config).values(configData);
      console.log("✅ Configuration seeded");
    } else {
      console.log("✅ Configuration already exists");
    }

    // Check if FAQ already exists
    const existingFaq = await db.query.faqs.findFirst();

    if (!existingFaq) {
      // Seed FAQ
      const faqData = [
        {
          question: "Как сделать заказ?",
          answer:
            'Для создания заказа нажмите кнопку "Создать новый заказ" на главной странице, заполните информацию о товарах и контактные данные.',
          order: 1,
        },
        {
          question: "Какая комиссия за заказ?",
          answer:
            "Стандартная комиссия составляет 10% от стоимости товара. Окончательная сумма рассчитывается автоматически.",
          order: 2,
        },
        {
          question: "Как происходит оплата?",
          answer:
            "После подтверждения заказа вам будут высланы реквизиты для оплаты. Оплату можно произвести банковской картой или переводом.",
          order: 3,
        },
        {
          question: "Сколько времени занимает доставка?",
          answer:
            "Доставка из Китая обычно занимает 2-4 недели в зависимости от способа доставки и таможенного оформления.",
          order: 4,
        },
        {
          question: "Можно ли отследить заказ?",
          answer:
            "Да, после отправки товара вы получите трек-номер для отслеживания посылки.",
          order: 5,
        },
      ];

      await db.insert(faqs).values(faqData);
      console.log("✅ FAQ seeded");
    } else {
      console.log("✅ FAQ already exists");
    }

    // Check if email templates already exist
    const existingTemplates = await db.query.emailTemplates.findFirst();

    if (!existingTemplates) {
      // Seed email templates
      const emailTemplatesData = [
        {
          name: "welcome",
          displayName: "Приветственное письмо",
          subject: "Добро пожаловать в YuYu Lolita Shopping!",
          htmlContent: `
          <h1>Добро пожаловать, {{name}}!</h1>
          <p>Спасибо за регистрацию в YuYu Lolita Shopping.</p>
          <p>Для подтверждения email перейдите по ссылке:</p>
          <a href="{{verificationUrl}}">Подтвердить email</a>
        `,
          textContent:
            "Добро пожаловать, {{name}}! Для подтверждения email перейдите по ссылке: {{verificationUrl}}",
          availableVariables: "name, verificationUrl",
        },
        {
          name: "password_reset",
          displayName: "Сброс пароля",
          subject: "Сброс пароля - YuYu Lolita Shopping",
          htmlContent: `
          <h1>Сброс пароля</h1>
          <p>Для сброса пароля перейдите по ссылке:</p>
          <a href="{{resetUrl}}">Сбросить пароль</a>
          <p>Если вы не запрашивали сброс пароля, проигнорируйте это письмо.</p>
        `,
          textContent: "Для сброса пароля перейдите по ссылке: {{resetUrl}}",
          availableVariables: "resetUrl",
        },
        {
          name: "order_created",
          displayName: "Уведомление о создании заказа",
          subject: "Новый заказ #{{orderNumber}} создан",
          htmlContent: `
          <h1>Заказ #{{orderNumber}} создан</h1>
          <p>Здравствуйте, {{customerName}}!</p>
          <p>Ваш заказ успешно создан и передан в обработку.</p>
          <p><strong>Сумма заказа:</strong> {{totalAmount}} ₽</p>
          <p>Вы можете отследить статус заказа по ссылке:</p>
          <a href="{{orderUrl}}">Посмотреть заказ</a>
        `,
          textContent:
            "Заказ #{{orderNumber}} создан. Сумма: {{totalAmount}} ₽. Ссылка: {{orderUrl}}",
          availableVariables: "orderNumber, customerName, totalAmount, orderUrl",
        },
      ];

      await db.insert(emailTemplates).values(emailTemplatesData);
      console.log("✅ Email templates seeded");
    } else {
      console.log("✅ Email templates already exist");
    }

    // Check if orders already exist
    const existingOrders = await db.query.orders.findFirst();

    if (!existingOrders && regularUser) {
      // Ensure we have enough customers for orders
      if (testCustomers.length < 3) {
        throw new Error("Not enough customers available for creating orders");
      }
      
      // Seed orders
      const orderData = [
        {
          nomerok: "YL123456",
          userId: regularUser.id,
          customerId: testCustomers[0]?.id || "",
          customerName: testCustomers[0]?.name || "Unknown Customer",
          customerPhone: testCustomers[0]?.phone || "+7 (999) 000-00-00",
          customerEmail: testCustomers[0]?.email || "unknown@example.com",
          deliveryAddress: "г. Москва, ул. Ленина, д. 10, кв. 5",
          deliveryMethod: "СДЭК",
          paymentMethod: "Банковская карта",
          status: "processing" as const,
          subtotalYuan: "200.00",
          totalCommission: "275.00",
          currentKurs: "13.50",
          totalYuan: "200.00",
          totalRuble: "2750.00",
          notes: "Заказ создан автоматически при инициализации",
          createdAt: new Date("2024-01-01T10:00:00Z"),
          updatedAt: new Date("2024-01-02T14:30:00Z"),
        },
        {
          nomerok: "YL789012",
          userId: regularUser.id,
          customerId: testCustomers[1]?.id || "",
          customerName: testCustomers[1]?.name || "Unknown Customer",
          customerPhone: testCustomers[1]?.phone || "+7 (999) 000-00-00",
          customerEmail: testCustomers[1]?.email || "unknown@example.com",
          deliveryAddress: "г. Санкт-Петербург, Невский пр., д. 25, кв. 12",
          deliveryMethod: "Почта России",
          paymentMethod: "СБП",
          status: "shipped" as const,
          subtotalYuan: "150.00",
          totalCommission: "208.75",
          currentKurs: "13.50",
          totalYuan: "150.00",
          totalRuble: "2087.50",
          trackingNumber: "RG123456789CN",
          notes: "Заказ отправлен, трек-номер предоставлен",
          createdAt: new Date("2024-01-02T10:00:00Z"),
          updatedAt: new Date("2024-01-10T09:15:00Z"),
        },
        {
          nomerok: "YL345678",
          userId: regularUser.id,
          customerId: testCustomers[2]?.id || "",
          customerName: testCustomers[2]?.name || "Unknown Customer",
          customerPhone: testCustomers[2]?.phone || "+7 (999) 000-00-00",
          customerEmail: testCustomers[2]?.email || "unknown@example.com",
          deliveryAddress: "г. Новосибирск, ул. Красный пр., д. 18, кв. 3",
          deliveryMethod: "СДЭК",
          paymentMethod: "Банковская карта",
          status: "created" as const,
          subtotalYuan: "300.00",
          totalCommission: "412.50",
          currentKurs: "13.50",
          totalYuan: "300.00",
          totalRuble: "4125.00",
          notes: "Новый заказ, ожидает подтверждения",
          createdAt: new Date("2024-01-03T15:30:00Z"),
          updatedAt: new Date("2024-01-03T15:30:00Z"),
        },
      ];

      const insertedOrders = await db
        .insert(orders)
        .values(orderData)
        .returning();
      
      if (insertedOrders.length < 3) {
        throw new Error("Failed to create all orders");
      }
      console.log("✅ Orders seeded");

      // Seed order goods
      const orderGoodsData = [
        {
          orderId: insertedOrders[0]?.id || "",
          name: "Платье Sweet Lolita розовое",
          link: "https://example.com/dress1",
          quantity: 1,
          priceYuan: "200.00",
          commission: "20.00",
          totalYuan: "220.00",
          totalRuble: "2970.00",
        },
        {
          orderId: insertedOrders[1]?.id || "",
          name: "Блузка Gothic Lolita чёрная",
          link: "https://example.com/blouse1",
          quantity: 1,
          priceYuan: "150.00",
          commission: "15.00",
          totalYuan: "165.00",
          totalRuble: "2227.50",
        },
        {
          orderId: insertedOrders[2]?.id || "",
          name: "Юбка Classic Lolita синяя",
          link: "https://example.com/skirt1",
          quantity: 1,
          priceYuan: "180.00",
          commission: "18.00",
          totalYuan: "198.00",
          totalRuble: "2673.00",
        },
        {
          orderId: insertedOrders[2]?.id || "",
          name: "Аксессуары для волос",
          link: "https://example.com/accessories1",
          quantity: 1,
          priceYuan: "120.00",
          commission: "12.00",
          totalYuan: "132.00",
          totalRuble: "1782.00",
        },
      ];

      await db.insert(orderGoods).values(orderGoodsData);
      console.log("✅ Order goods seeded");
    } else {
      console.log("✅ Orders already exist");
    }

    // Check if stories already exist
    const existingStories = await db.query.stories.findFirst();

    if (!existingStories && regularUser && adminUser) {
      // Seed stories
      const storiesData = [
        {
          title: "Мой первый заказ Lolita платья",
          link: "moy-pervyy-zakaz-lolita-platya",
          content: `
          <h2>Как я открыла для себя мир Lolita</h2>
          <p>Всё началось с случайного просмотра аниме, где я увидела невероятно красивые платья в стиле Lolita. Я была поражена их элегантностью и детализацией.</p>
          <p>После долгих поисков я нашла YuYu Lolita Shopping и решила сделать свой первый заказ. Процесс оказался очень простым и удобным.</p>
          <p>Платье пришло через 3 недели в отличном состоянии. Качество превзошло все мои ожидания!</p>
        `,
          excerpt:
            "История о том, как я открыла для себя мир Lolita и сделала свой первый заказ через YuYu Lolita Shopping.",
          thumbnail: "https://example.com/images/story1.jpg",
          authorId: regularUser.id,
          status: "published" as const,
          publishedAt: new Date("2024-01-15T10:00:00Z"),
        },
        {
          title: "Гид по стилям Lolita для начинающих",
          link: "gid-po-stilyam-lolita-dlya-nachinayuschih",
          content: `
          <h2>Основные стили Lolita</h2>
          <p><strong>Sweet Lolita</strong> - самый популярный стиль, характеризующийся пастельными цветами, рюшами и милыми принтами.</p>
          <p><strong>Gothic Lolita</strong> - тёмный и элегантный стиль с использованием чёрного, белого и тёмно-красного цветов.</p>
          <p><strong>Classic Lolita</strong> - более зрелый и утончённый стиль с использованием приглушённых цветов.</p>
          <p>Каждый стиль имеет свои особенности и подходит для разных случаев и предпочтений.</p>
        `,
          excerpt:
            "Подробный гид по основным стилям Lolita моды для тех, кто только начинает своё знакомство с этим направлением.",
          thumbnail: "https://example.com/images/story2.jpg",
          authorId: adminUser.id,
          status: "published" as const,
          publishedAt: new Date("2024-01-20T14:00:00Z"),
        },
        {
          title: "Как правильно ухаживать за Lolita платьями",
          link: "kak-pravilno-uhazhivat-za-lolita-platyami",
          content: `
          <h2>Секреты долговечности ваших платьев</h2>
          <p>Правильный уход за Lolita платьями поможет сохранить их красоту на долгие годы.</p>
          <p><strong>Стирка:</strong> Используйте деликатный режим в холодной воде. Лучше всего стирать вручную.</p>
          <p><strong>Сушка:</strong> Никогда не используйте сушилку. Сушите платья в расправленном виде на плоской поверхности.</p>
          <p><strong>Хранение:</strong> Храните платья на вешалках в чехлах из натуральных тканей.</p>
          <p><strong>Глажка:</strong> Используйте низкую температуру и гладьте через ткань.</p>
        `,
          excerpt:
            "Полезные советы по уходу за Lolita платьями, которые помогут сохранить их первозданный вид.",
          thumbnail: "https://example.com/images/story3.jpg",
          authorId: adminUser.id,
          status: "published" as const,
          publishedAt: new Date("2024-01-25T16:00:00Z"),
        },
      ];

      const insertedStories = await db
        .insert(stories)
        .values(storiesData)
        .returning();
      
      if (insertedStories.length < 3) {
        throw new Error("Failed to create all stories");
      }
      console.log("✅ Stories seeded");

      // Create blog categories
      const existingCategories = await db.query.blogCategories.findFirst();

      if (!existingCategories) {
        const categoriesData = [
          {
            name: "Товары",
            slug: "tovary",
            description: "Обзоры товаров, новинки, рекомендации",
            color: "#EC4899",
            order: 1,
            metaTitle: "Товары | YuYu Lolita Shopping",
            metaDescription: "Обзоры и рекомендации товаров в стиле Lolita",
          },
          {
            name: "Новости",
            slug: "novosti",
            description: "Новости магазина и индустрии",
            color: "#3B82F6",
            order: 2,
            metaTitle: "Новости | YuYu Lolita Shopping",
            metaDescription: "Последние новости из мира Lolita моды",
          },
          {
            name: "Акции",
            slug: "akcii",
            description: "Скидки, акции и специальные предложения",
            color: "#F59E0B",
            order: 3,
            metaTitle: "Акции | YuYu Lolita Shopping",
            metaDescription: "Актуальные акции и специальные предложения",
          },
          {
            name: "Гайды",
            slug: "gaidy",
            description: "Полезные руководства и советы",
            color: "#10B981",
            order: 4,
            metaTitle: "Гайды | YuYu Lolita Shopping",
            metaDescription: "Полезные советы по стилю Lolita и покупкам",
          },
        ];

        const insertedCategories = await db
          .insert(blogCategories)
          .values(categoriesData)
          .returning();
        
        if (insertedCategories.length < 4) {
          throw new Error("Failed to create all blog categories");
        }
        console.log("✅ Blog categories seeded");

        // Create tags
        const tagsData = [
          { name: "Sweet Lolita", slug: "sweet-lolita", color: "#EC4899" },
          { name: "Gothic Lolita", slug: "gothic-lolita", color: "#1F2937" },
          { name: "Classic Lolita", slug: "classic-lolita", color: "#6B7280" },
          { name: "Платья", slug: "platya", color: "#F472B6" },
          { name: "Аксессуары", slug: "aksessuary", color: "#A78BFA" },
          { name: "Уход", slug: "uhod", color: "#34D399" },
          { name: "Новичкам", slug: "novichkam", color: "#60A5FA" },
          { name: "Советы", slug: "sovety", color: "#FBBF24" },
        ];

        const insertedTags = await db
          .insert(storyTags)
          .values(tagsData)
          .returning();
        
        if (insertedTags.length < 8) {
          throw new Error("Failed to create all story tags");
        }
        console.log("✅ Story tags seeded");

        // Link stories with categories and tags
        const categoryRelationsData = [
          {
            storyId: insertedStories[0]?.id || "",
            categoryId: insertedCategories[0]?.id || "",
          }, // Товары
          {
            storyId: insertedStories[1]?.id || "",
            categoryId: insertedCategories[3]?.id || "",
          }, // Гайды
          {
            storyId: insertedStories[2]?.id || "",
            categoryId: insertedCategories[3]?.id || "",
          }, // Гайды
        ];

        const tagRelationsData = [
          { storyId: insertedStories[0]?.id || "", tagId: insertedTags[0]?.id || "" }, // Sweet Lolita
          { storyId: insertedStories[0]?.id || "", tagId: insertedTags[3]?.id || "" }, // Платья
          { storyId: insertedStories[1]?.id || "", tagId: insertedTags[6]?.id || "" }, // Новичкам
          { storyId: insertedStories[1]?.id || "", tagId: insertedTags[7]?.id || "" }, // Советы
          { storyId: insertedStories[2]?.id || "", tagId: insertedTags[5]?.id || "" }, // Уход
          { storyId: insertedStories[2]?.id || "", tagId: insertedTags[7]?.id || "" }, // Советы
        ];

        await db.insert(storyCategoryRelations).values(categoryRelationsData);
        await db.insert(storyTagRelations).values(tagRelationsData);
        console.log("✅ Story-category and story-tag relations created");
      } else {
        console.log("✅ Blog categories already exist");
      }
    } else {
      console.log("✅ Stories already exist");
    }

    console.log("🎉 Database seeding completed successfully!");
    console.log("");
    console.log("👤 Test users created:");
    console.log("📧 Admin: admin@yuyulolita.com / password: admin123");
    console.log("👤 User: user@example.com / password: user123");
    console.log("📱 Phone User: +79991234568 / password: user123");
    console.log("");
    console.log("🎯 Subscription system:");
    console.log("💎 4 subscription tiers with features configured");
    console.log("📊 Test subscriptions: Elite, Group plans active");
    console.log("");
    console.log("📦 E-commerce data:");
    console.log("📦 Test orders created: 3 orders with goods");
    console.log("👥 Test customers: 5 customers with addresses");
    console.log("");
    console.log("📝 Content system:");
    console.log("📖 Test stories: 3 published stories with categories/tags");
    console.log("🏷️ Blog categories: Товары, Новости, Акции, Гайды");
    console.log("🔖 Story tags: 8 tags for content classification");
    console.log("");
    console.log("⚙️ Configuration:");
    console.log("💰 Currency rates, commission settings");
    console.log("❓ FAQ system populated");
    console.log("📧 Email templates configured");
  } catch (error) {
    console.error("❌ Seeding failed:", error);
    process.exit(1);
  }
}

if (import.meta.main) {
  seedDatabase();
}
