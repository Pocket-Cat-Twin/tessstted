import { Elysia, t } from "elysia";
import { requireAuth } from "../middleware/auth";
// import { ValidationError } from "../middleware/error";
import { userProfileService } from "../services/user-profile";

export const profileRoutes = new Elysia({ prefix: "/profile" })
  .use(requireAuth)

  // Get user profile with subscription and addresses
  .get(
    "/",
    async ({ store }) => {
      const userId = store.user.id;
      const profile = await userProfileService.getUserProfile(userId);

      return {
        success: true,
        data: { profile },
      };
    },
    {
      detail: {
        summary: "Get user profile",
        description:
          "Get complete user profile including subscription details and addresses",
        tags: ["Profile"],
      },
    },
  )

  // Update profile information
  .put(
    "/",
    async ({ body, store }) => {
      const userId = store.user.id;

      await userProfileService.updateProfile(userId, body);

      return {
        success: true,
        message: "Profile updated successfully",
      };
    },
    {
      body: t.Object({
        name: t.Optional(t.String({ minLength: 1, maxLength: 100 })),
        fullName: t.Optional(t.String({ minLength: 1, maxLength: 200 })),
        contactPhone: t.Optional(t.String({ maxLength: 50 })),
        contactEmail: t.Optional(t.String({ format: "email", maxLength: 255 })),
        avatar: t.Optional(t.String()),
      }),
      detail: {
        summary: "Update user profile",
        description:
          "Update user profile information (name, contact details, avatar)",
        tags: ["Profile"],
      },
    },
  )

  // Get user addresses
  .get(
    "/addresses",
    async ({ store }) => {
      const userId = store.user.id;
      const profile = await userProfileService.getUserProfile(userId);

      return {
        success: true,
        data: { addresses: profile.addresses },
      };
    },
    {
      detail: {
        summary: "Get user addresses",
        description: "Get all delivery addresses for the user",
        tags: ["Profile"],
      },
    },
  )

  // Add new address
  .post(
    "/addresses",
    async ({ body, store }) => {
      const userId = store.user.id;

      const addressId = await userProfileService.addAddress(userId, body);

      return {
        success: true,
        message: "Address added successfully",
        data: { addressId },
      };
    },
    {
      body: t.Object({
        fullAddress: t.String({ minLength: 1, maxLength: 500 }),
        city: t.String({ minLength: 1, maxLength: 100 }),
        postalCode: t.Optional(t.String({ maxLength: 20 })),
        country: t.Optional(t.String({ maxLength: 100 })),
        addressComments: t.Optional(t.String({ maxLength: 500 })),
        isDefault: t.Optional(t.Boolean()),
      }),
      detail: {
        summary: "Add new address",
        description: "Add a new delivery address for the user",
        tags: ["Profile"],
      },
    },
  )

  // Update address
  .put(
    "/addresses/:addressId",
    async ({ params, body, store }) => {
      const userId = store.user.id;
      const { addressId } = params;

      await userProfileService.updateAddress(userId, addressId, body);

      return {
        success: true,
        message: "Address updated successfully",
      };
    },
    {
      params: t.Object({
        addressId: t.String(),
      }),
      body: t.Object({
        fullAddress: t.Optional(t.String({ minLength: 1, maxLength: 500 })),
        city: t.Optional(t.String({ minLength: 1, maxLength: 100 })),
        postalCode: t.Optional(t.String({ maxLength: 20 })),
        country: t.Optional(t.String({ maxLength: 100 })),
        addressComments: t.Optional(t.String({ maxLength: 500 })),
        isDefault: t.Optional(t.Boolean()),
      }),
      detail: {
        summary: "Update address",
        description: "Update an existing delivery address",
        tags: ["Profile"],
      },
    },
  )

  // Delete address
  .delete(
    "/addresses/:addressId",
    async ({ params, store }) => {
      const userId = store.user.id;
      const { addressId } = params;

      await userProfileService.deleteAddress(userId, addressId);

      return {
        success: true,
        message: "Address deleted successfully",
      };
    },
    {
      params: t.Object({
        addressId: t.String(),
      }),
      detail: {
        summary: "Delete address",
        description:
          "Delete a delivery address (cannot delete the only address)",
        tags: ["Profile"],
      },
    },
  )

  // Get subscription details
  .get(
    "/subscription",
    async ({ store }) => {
      const userId = store.user.id;
      const profile = await userProfileService.getUserProfile(userId);

      return {
        success: true,
        data: { subscription: profile.subscription },
      };
    },
    {
      detail: {
        summary: "Get subscription details",
        description: "Get current subscription tier and features",
        tags: ["Profile"],
      },
    },
  )

  // Get subscription history
  .get(
    "/subscription/history",
    async ({ store }) => {
      const userId = store.user.id;
      const history = await userProfileService.getSubscriptionHistory(userId);

      return {
        success: true,
        data: { history },
      };
    },
    {
      detail: {
        summary: "Get subscription history",
        description: "Get all past and current subscriptions",
        tags: ["Profile"],
      },
    },
  )

  // Check user permissions for specific actions
  .post(
    "/permissions/check",
    async ({ body, store }) => {
      const userId = store.user.id;
      const { actions } = body;

      const permissions: Record<string, boolean> = {};

      for (const action of actions) {
        permissions[action] = await userProfileService.canUserPerformAction(
          userId,
          action,
        );
      }

      return {
        success: true,
        data: { permissions },
      };
    },
    {
      body: t.Object({
        actions: t.Array(t.String()),
      }),
      detail: {
        summary: "Check user permissions",
        description:
          "Check if user can perform specific actions based on subscription tier",
        tags: ["Profile"],
      },
    },
  )

  // Get storage limits
  .get(
    "/storage-limit",
    async ({ store }) => {
      const userId = store.user.id;
      const limit = await userProfileService.getUserStorageLimit(userId);

      return {
        success: true,
        data: {
          maxStorageDays: limit,
          unlimited: limit === -1,
        },
      };
    },
    {
      detail: {
        summary: "Get storage limit",
        description: "Get maximum storage time based on subscription tier",
        tags: ["Profile"],
      },
    },
  );
