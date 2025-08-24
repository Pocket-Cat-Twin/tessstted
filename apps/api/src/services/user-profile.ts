import {
  db,
  users,
  userSubscriptions,
  subscriptionFeatures,
  customerAddresses,
  customers,
  eq,
  and,
  gte,
} from "@lolita-fashion/db";
import {
  getEffectiveTier,
  isSubscriptionActive,
  getDaysRemaining,
  SUBSCRIPTION_TIERS,
} from "@lolita-fashion/shared";
import {
  NotFoundError,
  ValidationError,
} from "../middleware/error";

export interface UserProfile {
  id: string;
  email?: string;
  phone?: string;
  name?: string;
  fullName?: string;
  contactPhone?: string;
  contactEmail?: string;
  registrationMethod: "email" | "phone";
  role: "user" | "admin";
  status: "pending" | "active" | "blocked";
  emailVerified: boolean;
  phoneVerified: boolean;
  avatar?: string;
  subscription: {
    currentTier: "free" | "group" | "elite" | "vip_temp";
    isActive: boolean;
    expiresAt?: Date;
    daysRemaining?: number;
    features: any;
    autoRenew: boolean;
  };
  addresses: Array<{
    id: string;
    fullAddress: string;
    city: string;
    postalCode?: string;
    country: string;
    addressComments?: string;
    isDefault: boolean;
  }>;
  createdAt: Date;
  lastLoginAt?: Date;
}

export interface UpdateProfileData {
  name?: string;
  fullName?: string;
  contactPhone?: string;
  contactEmail?: string;
  avatar?: string;
}

export interface CreateAddressData {
  fullAddress: string;
  city: string;
  postalCode?: string;
  country?: string;
  addressComments?: string;
  isDefault?: boolean;
}

export interface UpdateAddressData extends Partial<CreateAddressData> {}

class UserProfileService {
  /**
   * Get complete user profile with subscription and addresses
   */
  async getUserProfile(userId: string): Promise<UserProfile> {
    // Get user data
    const user = await db.query.users.findFirst({
      where: eq(users.id, userId),
    });

    if (!user) {
      throw new NotFoundError("User not found");
    }

    // Get current active subscription
    const activeSubscription = await db.query.userSubscriptions.findFirst({
      where: and(
        eq(userSubscriptions.userId, userId),
        eq(userSubscriptions.status, "active"),
        gte(userSubscriptions.endDate, new Date()), // Not expired
      ),
      orderBy: userSubscriptions.endDate, // Get the latest expiring one
    });

    // Determine effective subscription tier
    let currentTier: "free" | "group" | "elite" | "vip_temp" = "free";
    let isActive = true;
    let expiresAt: Date | undefined;
    let autoRenew = false;

    if (activeSubscription) {
      currentTier = activeSubscription.tier;
      isActive = isSubscriptionActive(activeSubscription.endDate);
      expiresAt = activeSubscription.endDate;
      autoRenew = activeSubscription.autoRenew;
    }

    // Get effective tier (falls back to free if subscription expired)
    const effectiveTier = getEffectiveTier(currentTier, expiresAt || null);

    // Get subscription features
    const features = await db.query.subscriptionFeatures.findFirst({
      where: eq(subscriptionFeatures.tier, effectiveTier),
    });

    // Get user addresses (find customer record first)
    let addresses: UserProfile["addresses"] = [];
    const customer = await db.query.customers.findFirst({
      where: eq(customers.email, user.email || ""),
      with: {
        addresses: true,
      },
    });

    if (customer?.addresses) {
      addresses = customer.addresses.map((addr) => ({
        id: addr.id,
        fullAddress: addr.fullAddress,
        city: addr.city || "",
        postalCode: addr.postalCode || undefined,
        country: addr.country || "Россия",
        addressComments: addr.addressComments || undefined,
        isDefault: addr.isDefault,
      }));
    }

    return {
      id: user.id,
      email: user.email || undefined,
      phone: user.phone || undefined,
      name: user.name || undefined,
      fullName: user.fullName || undefined,
      contactPhone: user.contactPhone || undefined,
      contactEmail: user.contactEmail || undefined,
      registrationMethod: user.registrationMethod,
      role: user.role,
      status: user.status,
      emailVerified: user.emailVerified,
      phoneVerified: user.phoneVerified,
      avatar: user.avatar || undefined,
      subscription: {
        currentTier: effectiveTier,
        isActive,
        expiresAt,
        daysRemaining: getDaysRemaining(expiresAt || null),
        features: features || SUBSCRIPTION_TIERS[effectiveTier].features,
        autoRenew,
      },
      addresses,
      createdAt: user.createdAt,
      lastLoginAt: user.lastLoginAt || undefined,
    };
  }

  /**
   * Update user profile information
   */
  async updateProfile(userId: string, data: UpdateProfileData): Promise<void> {
    const user = await db.query.users.findFirst({
      where: eq(users.id, userId),
    });

    if (!user) {
      throw new NotFoundError("User not found");
    }

    // Validate contact email if provided
    if (data.contactEmail && data.contactEmail === user.email) {
      throw new ValidationError(
        "Contact email cannot be the same as login email",
      );
    }

    // Validate contact phone if provided
    if (data.contactPhone && data.contactPhone === user.phone) {
      throw new ValidationError(
        "Contact phone cannot be the same as login phone",
      );
    }

    await db
      .update(users)
      .set({
        ...data,
        updatedAt: new Date(),
      })
      .where(eq(users.id, userId));
  }

  /**
   * Add new address for user
   */
  async addAddress(
    userId: string,
    addressData: CreateAddressData,
  ): Promise<string> {
    const user = await db.query.users.findFirst({
      where: eq(users.id, userId),
    });

    if (!user) {
      throw new NotFoundError("User not found");
    }

    // Find or create customer record
    let customer = await db.query.customers.findFirst({
      where: user.email
        ? eq(customers.email, user.email)
        : eq(customers.phone, user.phone!),
    });

    if (!customer) {
      // Create customer record
      const [newCustomer] = await db
        .insert(customers)
        .values({
          name: user.name || user.fullName || "Клиент",
          fullName: user.fullName,
          email: user.email,
          phone: user.phone,
          contactPhone: user.contactPhone,
        })
        .returning();
      customer = newCustomer;
    }

    // If this is the first address or marked as default, make it default
    const existingAddresses = await db.query.customerAddresses.findMany({
      where: eq(customerAddresses.customerId, customer.id),
    });

    const shouldBeDefault =
      addressData.isDefault || existingAddresses.length === 0;

    // If setting as default, unmark other addresses
    if (shouldBeDefault) {
      await db
        .update(customerAddresses)
        .set({ isDefault: false })
        .where(eq(customerAddresses.customerId, customer.id));
    }

    // Create address
    const [newAddress] = await db
      .insert(customerAddresses)
      .values({
        customerId: customer.id,
        fullAddress: addressData.fullAddress,
        city: addressData.city,
        postalCode: addressData.postalCode,
        country: addressData.country || "Россия",
        addressComments: addressData.addressComments,
        isDefault: shouldBeDefault,
      })
      .returning();

    return newAddress.id;
  }

  /**
   * Update existing address
   */
  async updateAddress(
    userId: string,
    addressId: string,
    data: UpdateAddressData,
  ): Promise<void> {
    // Verify user owns this address
    const address = await this.getUserAddress(userId, addressId);

    // If setting as default, unmark other addresses
    if (data.isDefault) {
      await db
        .update(customerAddresses)
        .set({ isDefault: false })
        .where(
          and(
            eq(customerAddresses.customerId, address.customerId),
            // Don't update the current address yet
          ),
        );
    }

    await db
      .update(customerAddresses)
      .set({
        ...data,
        updatedAt: new Date(),
      })
      .where(eq(customerAddresses.id, addressId));
  }

  /**
   * Delete address
   */
  async deleteAddress(userId: string, addressId: string): Promise<void> {
    // Verify user owns this address
    const address = await this.getUserAddress(userId, addressId);

    // Check if this is the only address
    const addressCount = await db.query.customerAddresses.findMany({
      where: eq(customerAddresses.customerId, address.customerId),
    });

    if (addressCount.length === 1) {
      throw new ValidationError(
        "Cannot delete the only address. Please add another address first.",
      );
    }

    // Delete the address
    await db
      .delete(customerAddresses)
      .where(eq(customerAddresses.id, addressId));

    // If this was the default address, make another one default
    if (address.isDefault) {
      const remainingAddresses = await db.query.customerAddresses.findMany({
        where: eq(customerAddresses.customerId, address.customerId),
        limit: 1,
      });

      if (remainingAddresses.length > 0) {
        await db
          .update(customerAddresses)
          .set({ isDefault: true })
          .where(eq(customerAddresses.id, remainingAddresses[0].id));
      }
    }
  }

  /**
   * Get user's address by ID (with ownership verification)
   */
  private async getUserAddress(userId: string, addressId: string) {
    const user = await db.query.users.findFirst({
      where: eq(users.id, userId),
    });

    if (!user) {
      throw new NotFoundError("User not found");
    }

    const customer = await db.query.customers.findFirst({
      where: user.email
        ? eq(customers.email, user.email)
        : eq(customers.phone, user.phone!),
    });

    if (!customer) {
      throw new NotFoundError("Customer record not found");
    }

    const address = await db.query.customerAddresses.findFirst({
      where: and(
        eq(customerAddresses.id, addressId),
        eq(customerAddresses.customerId, customer.id),
      ),
    });

    if (!address) {
      throw new NotFoundError("Address not found or access denied");
    }

    return address;
  }

  /**
   * Get user's subscription history
   */
  async getSubscriptionHistory(userId: string): Promise<
    Array<{
      id: string;
      tier: string;
      status: string;
      price: string;
      startDate: Date;
      endDate: Date;
      autoRenew: boolean;
      createdAt: Date;
    }>
  > {
    const subscriptions = await db.query.userSubscriptions.findMany({
      where: eq(userSubscriptions.userId, userId),
      orderBy: userSubscriptions.createdAt,
    });

    return subscriptions.map((sub) => ({
      id: sub.id,
      tier: sub.tier,
      status: sub.status,
      price: sub.price,
      startDate: sub.startDate,
      endDate: sub.endDate,
      autoRenew: sub.autoRenew,
      createdAt: sub.createdAt,
    }));
  }

  /**
   * Check if user can perform action based on subscription tier
   */
  async canUserPerformAction(userId: string, action: string): Promise<boolean> {
    const profile = await this.getUserProfile(userId);
    const features = profile.subscription.features;

    switch (action) {
      case "participate_in_promotions":
        return features.canParticipateInPromotions;
      case "combine_orders":
        return features.canCombineOrders;
      case "priority_processing":
        return features.hasPriorityProcessing;
      case "personal_support":
        return features.hasPersonalSupport;
      case "product_inspection":
        return features.hasProductInspection;
      default:
        return false;
    }
  }

  /**
   * Get storage time limit for user
   */
  async getUserStorageLimit(userId: string): Promise<number> {
    const profile = await this.getUserProfile(userId);
    return profile.subscription.features.maxStorageDays;
  }
}

// Export singleton instance
export const userProfileService = new UserProfileService();
