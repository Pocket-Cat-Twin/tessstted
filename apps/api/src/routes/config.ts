import { Elysia, t } from 'elysia';
import { 
  db, 
  config, 
  faqs,
  eq, 
  desc, 
  asc,
  sql 
} from '@yuyu/db';
import { 
  configUpdateSchema,
  faqCreateSchema,
  faqUpdateSchema
} from '@yuyu/shared';
import { requireAdmin } from '../middleware/auth';
import { NotFoundError, ValidationError } from '../middleware/error';

export const configRoutes = new Elysia({ prefix: '/config' })
  
  // Public routes

  // Get public configuration (non-sensitive values)
  .get('/public', async () => {
    const publicConfigs = await db.query.config.findMany({
      where: sql`${config.key} IN ('site_name', 'site_description', 'contact_email', 'contact_phone', 'telegram_link', 'vk_link', 'current_kurs')`,
      columns: {
        key: true,
        value: true,
        description: true,
      },
    });

    // Convert to key-value object
    const configObject = publicConfigs.reduce((acc, cfg) => {
      acc[cfg.key] = cfg.value;
      return acc;
    }, {} as Record<string, string>);

    return {
      success: true,
      data: { config: configObject },
    };
  }, {
    detail: {
      summary: 'Get public configuration',
      tags: ['Config'],
    },
  })

  // Get current currency rate
  .get('/kurs', async () => {
    const kursConfig = await db.query.config.findFirst({
      where: eq(config.key, 'current_kurs'),
    });

    const kurs = kursConfig ? parseFloat(kursConfig.value) : 13.5;

    return {
      success: true,
      data: { kurs },
    };
  }, {
    detail: {
      summary: 'Get current currency rate',
      tags: ['Config'],
    },
  })

  // Get FAQ list
  .get('/faq', async () => {
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
  }, {
    detail: {
      summary: 'Get FAQ list',
      tags: ['Config'],
    },
  })

  // Admin routes
  .use(requireAdmin)

  // Get all configuration
  .get('/', async () => {
    const configs = await db.query.config.findMany({
      orderBy: asc(config.key),
    });

    return {
      success: true,
      data: { configs },
    };
  }, {
    detail: {
      summary: 'Get all configuration (Admin)',
      tags: ['Config'],
    },
  })

  // Get configuration by key
  .get('/:key', async ({ params: { key } }) => {
    const configItem = await db.query.config.findFirst({
      where: eq(config.key, key),
    });

    if (!configItem) {
      throw new NotFoundError('Configuration not found');
    }

    return {
      success: true,
      data: { config: configItem },
    };
  }, {
    params: t.Object({
      key: t.String(),
    }),
    detail: {
      summary: 'Get configuration by key (Admin)',
      tags: ['Config'],
    },
  })

  // Update configuration
  .put('/:key', async ({ params: { key }, body }) => {
    const validation = configUpdateSchema.safeParse(body);
    if (!validation.success) {
      throw new ValidationError('Invalid configuration data');
    }

    const { value, description } = validation.data;

    // Find existing config
    const existingConfig = await db.query.config.findFirst({
      where: eq(config.key, key),
    });

    if (!existingConfig) {
      throw new NotFoundError('Configuration not found');
    }

    // Update config
    const [updatedConfig] = await db.update(config)
      .set({
        value,
        ...(description && { description }),
        updatedAt: new Date(),
      })
      .where(eq(config.key, key))
      .returning();

    return {
      success: true,
      message: 'Configuration updated successfully',
      data: { config: updatedConfig },
    };
  }, {
    params: t.Object({
      key: t.String(),
    }),
    body: t.Object({
      value: t.String(),
      description: t.Optional(t.String()),
    }),
    detail: {
      summary: 'Update configuration (Admin)',
      tags: ['Config'],
    },
  })

  // Create new configuration
  .post('/', async ({ body, set }) => {
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
      throw new ValidationError('Configuration key already exists');
    }

    // Create config
    const [newConfig] = await db.insert(config).values({
      key,
      value,
      description,
      type: (type as any) || 'string',
    }).returning();

    set.status = 201;
    return {
      success: true,
      message: 'Configuration created successfully',
      data: { config: newConfig },
    };
  }, {
    body: t.Object({
      key: t.String({ minLength: 1 }),
      value: t.String(),
      description: t.Optional(t.String()),
      type: t.Optional(t.String()),
    }),
    detail: {
      summary: 'Create configuration (Admin)',
      tags: ['Config'],
    },
  })

  // Delete configuration
  .delete('/:key', async ({ params: { key } }) => {
    const configItem = await db.query.config.findFirst({
      where: eq(config.key, key),
    });

    if (!configItem) {
      throw new NotFoundError('Configuration not found');
    }

    // Delete config
    await db.delete(config).where(eq(config.key, key));

    return {
      success: true,
      message: 'Configuration deleted successfully',
    };
  }, {
    params: t.Object({
      key: t.String(),
    }),
    detail: {
      summary: 'Delete configuration (Admin)',
      tags: ['Config'],
    },
  })

  // FAQ Management

  // Get all FAQs (admin)
  .get('/faq/all', async () => {
    const faqList = await db.query.faqs.findMany({
      orderBy: asc(faqs.order),
    });

    return {
      success: true,
      data: { faqs: faqList },
    };
  }, {
    detail: {
      summary: 'Get all FAQs (Admin)',
      tags: ['Config'],
    },
  })

  // Get FAQ by ID
  .get('/faq/:id', async ({ params: { id } }) => {
    const faq = await db.query.faqs.findFirst({
      where: eq(faqs.id, id),
    });

    if (!faq) {
      throw new NotFoundError('FAQ not found');
    }

    return {
      success: true,
      data: { faq },
    };
  }, {
    params: t.Object({
      id: t.String(),
    }),
    detail: {
      summary: 'Get FAQ by ID (Admin)',
      tags: ['Config'],
    },
  })

  // Create FAQ
  .post('/faq', async ({ body, set }) => {
    const validation = faqCreateSchema.safeParse(body);
    if (!validation.success) {
      throw new ValidationError('Invalid FAQ data');
    }

    const faqData = validation.data;

    // Create FAQ
    const [newFaq] = await db.insert(faqs).values(faqData).returning();

    set.status = 201;
    return {
      success: true,
      message: 'FAQ created successfully',
      data: { faq: newFaq },
    };
  }, {
    body: t.Object({
      question: t.String({ minLength: 1 }),
      answer: t.String({ minLength: 1 }),
      order: t.Optional(t.Number()),
      isActive: t.Optional(t.Boolean()),
    }),
    detail: {
      summary: 'Create FAQ (Admin)',
      tags: ['Config'],
    },
  })

  // Update FAQ
  .put('/faq/:id', async ({ params: { id }, body }) => {
    const validation = faqUpdateSchema.safeParse(body);
    if (!validation.success) {
      throw new ValidationError('Invalid FAQ update data');
    }

    const updateData = validation.data;

    // Find existing FAQ
    const existingFaq = await db.query.faqs.findFirst({
      where: eq(faqs.id, id),
    });

    if (!existingFaq) {
      throw new NotFoundError('FAQ not found');
    }

    // Update FAQ
    const [updatedFaq] = await db.update(faqs)
      .set({
        ...updateData,
        updatedAt: new Date(),
      })
      .where(eq(faqs.id, id))
      .returning();

    return {
      success: true,
      message: 'FAQ updated successfully',
      data: { faq: updatedFaq },
    };
  }, {
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
      summary: 'Update FAQ (Admin)',
      tags: ['Config'],
    },
  })

  // Delete FAQ
  .delete('/faq/:id', async ({ params: { id } }) => {
    const faq = await db.query.faqs.findFirst({
      where: eq(faqs.id, id),
    });

    if (!faq) {
      throw new NotFoundError('FAQ not found');
    }

    // Delete FAQ
    await db.delete(faqs).where(eq(faqs.id, id));

    return {
      success: true,
      message: 'FAQ deleted successfully',
    };
  }, {
    params: t.Object({
      id: t.String(),
    }),
    detail: {
      summary: 'Delete FAQ (Admin)',
      tags: ['Config'],
    },
  })

  // Reorder FAQs
  .post('/faq/reorder', async ({ body }) => {
    const { faqIds } = body as { faqIds: string[] };

    // Update order for each FAQ
    const updatePromises = faqIds.map((faqId, index) =>
      db.update(faqs)
        .set({ order: index + 1, updatedAt: new Date() })
        .where(eq(faqs.id, faqId))
    );

    await Promise.all(updatePromises);

    return {
      success: true,
      message: 'FAQ order updated successfully',
    };
  }, {
    body: t.Object({
      faqIds: t.Array(t.String()),
    }),
    detail: {
      summary: 'Reorder FAQs (Admin)',
      tags: ['Config'],
    },
  });