import nodemailer from "nodemailer";

export enum EmailType {
  WELCOME = "welcome",
  EMAIL_VERIFICATION = "email_verification",
  PASSWORD_RESET = "password_reset",
  ORDER_CREATED = "order_created",
  ORDER_STATUS_UPDATED = "order_status_updated",
  SUBSCRIPTION_EXPIRING = "subscription_expiring",
  SUBSCRIPTION_EXPIRED = "subscription_expired",
  SUBSCRIPTION_RENEWED = "subscription_renewed",
}

// Email transporter configuration
const createTransporter = () => {
  return nodemailer.createTransport({
    host: process.env.SMTP_HOST || "smtp.gmail.com",
    port: parseInt(process.env.SMTP_PORT || "587"),
    secure: false, // true for 465, false for other ports
    auth: {
      user: process.env.SMTP_USER,
      pass: process.env.SMTP_PASSWORD,
    },
  });
};

// Email template processor
function processTemplate(
  template: string,
  variables: Record<string, any>,
): string {
  let processed = template;

  // Replace variables in format {{variableName}}
  for (const [key, value] of Object.entries(variables)) {
    const regex = new RegExp(`{{${key}}}`, "g");
    processed = processed.replace(regex, String(value));
  }

  return processed;
}

// Get email template from hardcoded templates (simplified for MySQL migration)
async function getEmailTemplate(templateName: string) {
  const templates: Record<string, { name: string, subject: string, htmlContent: string, textContent?: string }> = {
    [EmailType.WELCOME]: {
      name: "welcome",
      subject: "Welcome to YuYu Lolita Shopping - {{name}}!",
      htmlContent: `
        <h1>Welcome {{name}}!</h1>
        <p>Thank you for joining YuYu Lolita Shopping.</p>
        <p>Please verify your email by clicking this link: <a href="{{verificationUrl}}">Verify Email</a></p>
      `,
      textContent: "Welcome {{name}}! Please verify your email: {{verificationUrl}}"
    },
    [EmailType.EMAIL_VERIFICATION]: {
      name: "email_verification",
      subject: "Verify Your Email - YuYu Lolita",
      htmlContent: `
        <h1>Email Verification</h1>
        <p>Please verify your email by clicking this link: <a href="{{verificationUrl}}">Verify Email</a></p>
      `,
    },
    [EmailType.PASSWORD_RESET]: {
      name: "password_reset",
      subject: "Reset Your Password - YuYu Lolita",
      htmlContent: `
        <h1>Password Reset</h1>
        <p>Hi {{name}}, click this link to reset your password: <a href="{{resetUrl}}">Reset Password</a></p>
      `,
    },
    [EmailType.ORDER_CREATED]: {
      name: "order_created",
      subject: "Order Created #{{orderNumber}} - YuYu Lolita",
      htmlContent: `
        <h1>Order Created</h1>
        <p>Hi {{customerName}}, your order #{{orderNumber}} has been created successfully.</p>
        <p>Total: ¥{{totalAmount}}</p>
        <p><a href="{{orderUrl}}">View Order</a></p>
      `,
    },
    [EmailType.ORDER_STATUS_UPDATED]: {
      name: "order_status_updated",
      subject: "Order Update #{{orderNumber}} - YuYu Lolita",
      htmlContent: `
        <h1>Order Status Update</h1>
        <p>Hi {{customerName}}, your order #{{orderNumber}} status has been updated to: {{newStatus}}</p>
        <p><a href="{{orderUrl}}">View Order</a></p>
      `,
    },
    [EmailType.SUBSCRIPTION_EXPIRING]: {
      name: "subscription_expiring",
      subject: "Subscription Expiring Soon - YuYu Lolita",
      htmlContent: `
        <h1>Subscription Expiring</h1>
        <p>Hi {{name}}, your {{tier}} subscription will expire in {{daysRemaining}} days.</p>
        <p><a href="{{subscriptionsUrl}}">Renew Subscription</a></p>
      `,
    },
    [EmailType.SUBSCRIPTION_EXPIRED]: {
      name: "subscription_expired",
      subject: "Subscription Expired - YuYu Lolita",
      htmlContent: `
        <h1>Subscription Expired</h1>
        <p>Hi {{name}}, your {{tier}} subscription has expired.</p>
        <p><a href="{{subscriptionsUrl}}">Renew Subscription</a></p>
      `,
    },
    [EmailType.SUBSCRIPTION_RENEWED]: {
      name: "subscription_renewed",
      subject: "Subscription Renewed - YuYu Lolita",
      htmlContent: `
        <h1>Subscription Renewed</h1>
        <p>Hi {{name}}, your {{tier}} subscription has been renewed until {{nextExpirationDate}}.</p>
      `,
    },
  };

  return templates[templateName] || null;
}

// Build email URLs
function buildEmailUrls(variables: Record<string, any>) {
  const baseUrl = process.env.PUBLIC_WEB_URL || "http://localhost:5173";

  return {
    ...variables,
    baseUrl,
    verificationUrl: variables.verificationToken
      ? `${baseUrl}/verify-email?token=${variables.verificationToken}`
      : undefined,
    resetUrl: variables.resetToken
      ? `${baseUrl}/reset-password?token=${variables.resetToken}`
      : undefined,
    orderUrl: variables.orderNumber
      ? `${baseUrl}/order/${variables.orderNumber}`
      : undefined,
  };
}

// Send email function
export async function sendEmail(
  type: EmailType,
  to: string,
  variables: Record<string, any> = {},
): Promise<void> {
  try {
    // Get email template
    const template = await getEmailTemplate(type);

    if (!template) {
      console.error(`Email template not found: ${type}`);
      return;
    }

    // Process variables with URLs
    const processedVariables = buildEmailUrls(variables);

    // Process template content
    const subject = processTemplate(template.subject, processedVariables);
    const htmlContent = processTemplate(
      template.htmlContent,
      processedVariables,
    );
    const textContent = template.textContent
      ? processTemplate(template.textContent, processedVariables)
      : undefined;

    // Create transporter
    const transporter = createTransporter();

    // Send email
    const info = await transporter.sendMail({
      from: `"YuYu Lolita Shopping" <${process.env.SMTP_FROM || process.env.SMTP_USER}>`,
      to,
      subject,
      html: htmlContent,
      text: textContent,
    });

    console.log("Email sent successfully:", info.messageId);
  } catch (error) {
    console.error("Failed to send email:", error);
    throw error;
  }
}

// Send welcome email
export async function sendWelcomeEmail(
  email: string,
  name: string,
  verificationToken: string,
) {
  return sendEmail(EmailType.WELCOME, email, {
    name,
    verificationToken,
  });
}

// Send password reset email
export async function sendPasswordResetEmail(
  email: string,
  name: string,
  resetToken: string,
) {
  return sendEmail(EmailType.PASSWORD_RESET, email, {
    name,
    resetToken,
  });
}

// Send order notification email
export async function sendOrderCreatedEmail(
  email: string,
  customerName: string,
  orderNumber: string,
  totalAmount: number,
  orderDetails?: {
    items: Array<{ name: string; quantity: number; price: number }>;
    deliveryAddress: string;
    estimatedProcessingTime: string;
  },
) {
  return sendEmail(EmailType.ORDER_CREATED, email, {
    customerName,
    orderNumber,
    totalAmount,
    items: orderDetails?.items || [],
    deliveryAddress: orderDetails?.deliveryAddress || "",
    estimatedProcessingTime: orderDetails?.estimatedProcessingTime || "",
  });
}

// Send order status update email
export async function sendOrderStatusUpdateEmail(
  email: string,
  customerName: string,
  orderNumber: string,
  oldStatus: string,
  newStatus: string,
  statusMessage?: string,
  trackingInfo?: {
    trackingNumber?: string;
    carrier?: string;
    trackingUrl?: string;
  },
) {
  return sendEmail(EmailType.ORDER_STATUS_UPDATED, email, {
    customerName,
    orderNumber,
    oldStatus,
    newStatus,
    statusMessage: statusMessage || "",
    trackingNumber: trackingInfo?.trackingNumber || "",
    carrier: trackingInfo?.carrier || "",
    trackingUrl: trackingInfo?.trackingUrl || "",
  });
}

// Send order payment confirmation email
export async function sendOrderPaymentConfirmationEmail(
  email: string,
  customerName: string,
  orderNumber: string,
  paymentAmount: number,
  paymentMethod: string,
  transactionId?: string,
) {
  return sendEmail(EmailType.ORDER_STATUS_UPDATED, email, {
    customerName,
    orderNumber,
    paymentAmount,
    paymentMethod,
    transactionId: transactionId || "",
    paymentStatus: "confirmed",
  });
}

// Send order ready for pickup email
export async function sendOrderReadyForPickupEmail(
  email: string,
  customerName: string,
  orderNumber: string,
  pickupAddress: string,
  pickupHours: string,
  readyDate: string,
) {
  return sendEmail(EmailType.ORDER_STATUS_UPDATED, email, {
    customerName,
    orderNumber,
    pickupAddress,
    pickupHours,
    readyDate,
    orderStatus: "ready_for_pickup",
  });
}

// Send order shipped email
export async function sendOrderShippedEmail(
  email: string,
  customerName: string,
  orderNumber: string,
  trackingNumber: string,
  carrier: string,
  estimatedDeliveryDate: string,
  trackingUrl?: string,
) {
  return sendEmail(EmailType.ORDER_STATUS_UPDATED, email, {
    customerName,
    orderNumber,
    trackingNumber,
    carrier,
    estimatedDeliveryDate,
    trackingUrl: trackingUrl || "",
    orderStatus: "shipped",
  });
}

// Send order delivered email
export async function sendOrderDeliveredEmail(
  email: string,
  customerName: string,
  orderNumber: string,
  deliveryDate: string,
  deliveryAddress: string,
) {
  return sendEmail(EmailType.ORDER_STATUS_UPDATED, email, {
    customerName,
    orderNumber,
    deliveryDate,
    deliveryAddress,
    orderStatus: "delivered",
  });
}

// Send order delayed email
export async function sendOrderDelayedEmail(
  email: string,
  customerName: string,
  orderNumber: string,
  delayReason: string,
  newEstimatedDate: string,
  compensationOffer?: string,
) {
  return sendEmail(EmailType.ORDER_STATUS_UPDATED, email, {
    customerName,
    orderNumber,
    delayReason,
    newEstimatedDate,
    compensationOffer: compensationOffer || "",
    orderStatus: "delayed",
  });
}

// Send order cancelled email
export async function sendOrderCancelledEmail(
  email: string,
  customerName: string,
  orderNumber: string,
  cancellationReason: string,
  refundAmount?: number,
  refundMethod?: string,
) {
  return sendEmail(EmailType.ORDER_STATUS_UPDATED, email, {
    customerName,
    orderNumber,
    cancellationReason,
    refundAmount: refundAmount || 0,
    refundMethod: refundMethod || "",
    orderStatus: "cancelled",
  });
}

// Send subscription expiring warning email
export async function sendSubscriptionExpiringEmail(
  email: string,
  name: string,
  tier: string,
  daysRemaining: number,
  expirationDate: string,
) {
  return sendEmail(EmailType.SUBSCRIPTION_EXPIRING, email, {
    name,
    tier,
    daysRemaining,
    expirationDate,
    subscriptionsUrl: `${process.env.PUBLIC_WEB_URL || "http://localhost:5173"}/subscriptions`,
  });
}

// Send subscription expired notification email
export async function sendSubscriptionExpiredEmail(
  email: string,
  name: string,
  tier: string,
  expiredDate: string,
) {
  return sendEmail(EmailType.SUBSCRIPTION_EXPIRED, email, {
    name,
    tier,
    expiredDate,
    subscriptionsUrl: `${process.env.PUBLIC_WEB_URL || "http://localhost:5173"}/subscriptions`,
  });
}

// Send subscription renewed confirmation email
export async function sendSubscriptionRenewedEmail(
  email: string,
  name: string,
  tier: string,
  renewedDate: string,
  nextExpirationDate: string,
) {
  return sendEmail(EmailType.SUBSCRIPTION_RENEWED, email, {
    name,
    tier,
    renewedDate,
    nextExpirationDate,
    subscriptionsUrl: `${process.env.PUBLIC_WEB_URL || "http://localhost:5173"}/subscriptions`,
  });
}

// Generic send email function for tests
export async function sendEmailGeneric(
  to: string,
  subject: string,
  content: string,
  _category?: string,
  textContent?: string,
) {
  // This is a simplified version for testing
  const transporter = createTransporter();
  
  try {
    const result = await transporter.sendMail({
      from: process.env.SMTP_FROM || "noreply@yuyu.com",
      to,
      subject,
      html: content,
      text: textContent,
    });

    return {
      success: true,
      providerId: result.messageId,
      messageId: result.messageId,
    };
  } catch (error) {
    return {
      success: false,
      error: (error as Error).message,
    };
  }
}

// Send verification email with code
export async function sendVerificationEmail(
  email: string,
  code?: string,
) {
  const verificationCode = code || Math.random().toString(36).substring(2, 8).toUpperCase();
  
  const result = await sendEmailGeneric(
    email,
    "Email Verification - YuYu Lolita Shopping",
    `<h1>Email Verification</h1><p>Your verification code is: <strong>${verificationCode}</strong></p>`,
    "verification"
  );

  return {
    ...result,
    code: verificationCode,
  };
}

// Send order notification email
export async function sendOrderNotificationEmail(
  email: string,
  orderData: any,
) {
  const subject = `Новый заказ #${orderData.nomerok}`;
  const content = `
    <h1>Заказ #${orderData.nomerok} создан</h1>
    <p>Здравствуйте, ${orderData.customerName}!</p>
    <p>Ваш заказ успешно создан.</p>
    <p>Товары:</p>
    <ul>
      ${orderData.items?.map((item: any) => `<li>${item.name} - ${item.price}₽</li>`).join('')}
    </ul>
  `;

  return sendEmailGeneric(email, subject, content, "order");
}

// Send subscription notification email
export async function sendSubscriptionNotificationEmail(
  email: string,
  subscriptionData: any,
) {
  const subject = `Уведомление о подписке`;
  const content = `
    <h1>Информация о подписке</h1>
    <p>Тип подписки: ${subscriptionData.tier}</p>
    <p>Возможности:</p>
    <ul>
      ${subscriptionData.features?.map((feature: string) => `<li>${feature}</li>`).join('')}
    </ul>
  `;

  return sendEmailGeneric(email, subject, content, "subscription");
}

// Update email status (for tracking)
export async function updateEmailStatus(
  _providerId: string,
  _status: string,
  _message?: string,
) {
  // This would typically update the database
  // For now, just return success
  return { success: true };
}

// Track email events
export async function trackEmailEvent(
  _providerId: string,
  _event: string,
  _data?: string,
) {
  // This would typically update the database
  // For now, just return success
  return { success: true };
}

// Send email with attachments
export async function sendEmailWithAttachments(
  to: string,
  subject: string,
  content: string,
  attachments: any[],
  _category?: string,
) {
  const transporter = createTransporter();
  
  try {
    const result = await transporter.sendMail({
      from: process.env.SMTP_FROM || "noreply@yuyu.com",
      to,
      subject,
      html: content,
      attachments,
    });

    return {
      success: true,
      providerId: result.messageId,
      messageId: result.messageId,
    };
  } catch (error) {
    return {
      success: false,
      error: (error as Error).message,
    };
  }
}

// Verify email configuration
export async function testEmailConfiguration(): Promise<boolean> {
  try {
    const transporter = createTransporter();
    await transporter.verify();
    return true;
  } catch (error) {
    console.error("Email configuration test failed:", error);
    return false;
  }
}

// Email service object for testing compatibility
export const emailService = {
  sendEmail: sendEmailGeneric,
  sendVerificationEmail,
  sendOrderNotificationEmail,
  sendSubscriptionNotificationEmail,
  sendPasswordResetEmail,
  updateEmailStatus,
  trackEmailEvent,
  sendEmailWithAttachments,
  testConfiguration: testEmailConfiguration,
};
