import nodemailer from 'nodemailer';
import { db, emailTemplates, eq, and } from '@yuyu/db';

export enum EmailType {
  WELCOME = 'welcome',
  EMAIL_VERIFICATION = 'email_verification', 
  PASSWORD_RESET = 'password_reset',
  ORDER_CREATED = 'order_created',
  ORDER_STATUS_UPDATED = 'order_status_updated',
}

// Email transporter configuration
const createTransporter = () => {
  return nodemailer.createTransport({
    host: process.env.SMTP_HOST || 'smtp.gmail.com',
    port: parseInt(process.env.SMTP_PORT || '587'),
    secure: false, // true for 465, false for other ports
    auth: {
      user: process.env.SMTP_USER,
      pass: process.env.SMTP_PASSWORD,
    },
  });
};

// Email template processor
function processTemplate(template: string, variables: Record<string, any>): string {
  let processed = template;
  
  // Replace variables in format {{variableName}}
  for (const [key, value] of Object.entries(variables)) {
    const regex = new RegExp(`{{${key}}}`, 'g');
    processed = processed.replace(regex, String(value));
  }
  
  return processed;
}

// Get email template from database
async function getEmailTemplate(templateName: string) {
  const template = await db.query.emailTemplates.findFirst({
    where: and(
      eq(emailTemplates.name, templateName),
      eq(emailTemplates.isActive, true)
    ),
  });
  
  return template;
}

// Build email URLs
function buildEmailUrls(variables: Record<string, any>) {
  const baseUrl = process.env.PUBLIC_WEB_URL || 'http://localhost:5173';
  
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
  variables: Record<string, any> = {}
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
    const htmlContent = processTemplate(template.htmlContent, processedVariables);
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

    console.log('Email sent successfully:', info.messageId);
  } catch (error) {
    console.error('Failed to send email:', error);
    throw error;
  }
}

// Send welcome email
export async function sendWelcomeEmail(email: string, name: string, verificationToken: string) {
  return sendEmail(EmailType.WELCOME, email, {
    name,
    verificationToken,
  });
}

// Send password reset email
export async function sendPasswordResetEmail(email: string, name: string, resetToken: string) {
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
  totalAmount: number
) {
  return sendEmail(EmailType.ORDER_CREATED, email, {
    customerName,
    orderNumber,
    totalAmount,
  });
}

// Verify email configuration
export async function testEmailConfiguration(): Promise<boolean> {
  try {
    const transporter = createTransporter();
    await transporter.verify();
    return true;
  } catch (error) {
    console.error('Email configuration test failed:', error);
    return false;
  }
}