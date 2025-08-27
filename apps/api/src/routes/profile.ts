import { Elysia, t } from "elysia";
import { jwt } from "@elysiajs/jwt";
import { cookie } from "@elysiajs/cookie";
import { getPool, QueryBuilder } from "@lolita-fashion/db";

export const profileRoutes = new Elysia({ prefix: "/profile" })
  .use(
    jwt({
      name: "jwt",
      secret: process.env.JWT_SECRET || "mysql-jwt-secret-change-in-production",
      exp: "7d",
    }),
  )
  .use(cookie())

  // Get User Profile
  .get(
    "/",
    async ({ jwt, cookie: { auth } }) => {
      try {
        if (!auth.value) {
          return {
            success: false,
            error: "Authentication required",
          };
        }

        const payload = await jwt.verify(auth.value);
        if (!payload) {
          return {
            success: false,
            error: "Invalid token",
          };
        }

        const pool = await getPool();
        const queryBuilder = new QueryBuilder(pool);
        const user = await queryBuilder.getUserById(payload.userId as string);

        if (!user) {
          return {
            success: false,
            error: "User not found",
          };
        }

        return {
          success: true,
          user: {
            id: user.id,
            email: user.email,
            name: user.name,
            fullName: user.full_name,
            phone: user.phone,
            role: user.role,
            status: user.status,
            emailVerified: user.email_verified,
            phoneVerified: user.phone_verified,
            avatar: user.avatar,
            contactEmail: user.contact_email,
            contactPhone: user.contact_phone,
            createdAt: user.created_at,
            updatedAt: user.updated_at,
          },
        };
      } catch (error) {
        console.error("Get profile error:", error);
        return {
          success: false,
          error: "Failed to get user profile",
        };
      }
    },
    {
      detail: {
        tags: ["Profile"],
        summary: "Get user profile",
        description: "Get the current user's profile information",
      },
    },
  )

  // Update User Profile
  .put(
    "/",
    async ({ body, jwt, cookie: { auth } }) => {
      const requestId = Math.random().toString(36).substr(2, 9);
      console.log(`🔍 [${requestId}] Profile UPDATE request received:`, {
        timestamp: new Date().toISOString(),
        hasAuth: !!auth.value,
        bodyKeys: Object.keys(body || {}),
        body: body
      });

      try {
        if (!auth.value) {
          console.log(`❌ [${requestId}] Authentication required - no auth cookie`);
          return {
            success: false,
            error: "Authentication required",
          };
        }

        const payload = await jwt.verify(auth.value);
        if (!payload) {
          console.log(`❌ [${requestId}] Invalid token - JWT verification failed`);
          return {
            success: false,
            error: "Invalid token",
          };
        }

        console.log(`✅ [${requestId}] Authentication successful for user:`, payload.userId);

        const pool = await getPool();
        
        // Update user profile
        const sql = `
          UPDATE users 
          SET name = ?, full_name = ?, phone = ?, contact_email = ?, contact_phone = ?, updated_at = NOW()
          WHERE id = ?
        `;
        
        const updateParams = [
          body.name,
          body.fullName,
          body.phone,
          body.contactEmail,
          body.contactPhone,
          payload.userId as string,
        ];

        console.log(`🔄 [${requestId}] Executing SQL UPDATE:`, {
          sql: sql.replace(/\s+/g, ' ').trim(),
          params: updateParams,
          userId: payload.userId
        });
        
        const [result] = await pool.execute(sql, updateParams);
        
        console.log(`✅ [${requestId}] SQL UPDATE completed:`, {
          affectedRows: (result as any).affectedRows,
          changedRows: (result as any).changedRows,
          insertId: (result as any).insertId,
          warningCount: (result as any).warningCount
        });

        const response = {
          success: true,
          message: "Profile updated successfully",
        };

        console.log(`🎉 [${requestId}] Profile update SUCCESS, sending response:`, response);
        return response;

      } catch (error) {
        console.error(`❌ [${requestId}] Update profile error:`, {
          error: error,
          message: error instanceof Error ? error.message : 'Unknown error',
          stack: error instanceof Error ? error.stack : undefined
        });
        
        const errorResponse = {
          success: false,
          error: "Failed to update profile",
        };

        console.log(`💥 [${requestId}] Sending ERROR response:`, errorResponse);
        return errorResponse;
      }
    },
    {
      body: t.Object({
        name: t.String({ minLength: 1 }),
        fullName: t.Optional(t.String()),
        phone: t.Optional(t.String()),
        contactEmail: t.Optional(t.String({ format: "email" })),
        contactPhone: t.Optional(t.String()),
      }),
      detail: {
        tags: ["Profile"],
        summary: "Update user profile",
        description: "Update the current user's profile information",
      },
    },
  )

  // Get User Addresses
  .get(
    "/addresses",
    async ({ jwt, cookie: { auth } }) => {
      try {
        if (!auth.value) {
          return {
            success: false,
            error: "Authentication required",
          };
        }

        const payload = await jwt.verify(auth.value);
        if (!payload) {
          return {
            success: false,
            error: "Invalid token",
          };
        }

        const pool = await getPool();
        const queryBuilder = new QueryBuilder(pool);
        const addresses = await queryBuilder.getAddressesByUserId(payload.userId as string);

        return {
          success: true,
          addresses: addresses.map((address: any) => ({
            id: address.id,
            fullAddress: address.full_address,
            city: address.city,
            postalCode: address.postal_code,
            country: address.country,
            addressComments: address.address_comments,
            isDefault: address.is_default,
            createdAt: address.created_at,
            updatedAt: address.updated_at,
          })),
        };
      } catch (error) {
        console.error("Get addresses error:", error);
        return {
          success: false,
          error: "Failed to get user addresses",
        };
      }
    },
    {
      detail: {
        tags: ["Profile"],
        summary: "Get user addresses",
        description: "Get all addresses for the current user",
      },
    },
  )

  // Add User Address
  .post(
    "/addresses",
    async ({ body, jwt, cookie: { auth } }) => {
      try {
        if (!auth.value) {
          return {
            success: false,
            error: "Authentication required",
          };
        }

        const payload = await jwt.verify(auth.value);
        if (!payload) {
          return {
            success: false,
            error: "Invalid token",
          };
        }

        const pool = await getPool();
        const queryBuilder = new QueryBuilder(pool);
        
        const addressId = await queryBuilder.createAddress({
          user_id: payload.userId as string,
          full_address: body.fullAddress,
          city: body.city,
          postal_code: body.postalCode,
          country: body.country || 'Россия',
          address_comments: body.addressComments,
          is_default: body.isDefault || false,
        });

        return {
          success: true,
          message: "Address created successfully",
          addressId,
        };
      } catch (error) {
        console.error("Create address error:", error);
        return {
          success: false,
          error: "Failed to create address",
        };
      }
    },
    {
      body: t.Object({
        fullAddress: t.String({ minLength: 1 }),
        city: t.String({ minLength: 1 }),
        postalCode: t.Optional(t.String()),
        country: t.Optional(t.String()),
        addressComments: t.Optional(t.String()),
        isDefault: t.Optional(t.Boolean()),
      }),
      detail: {
        tags: ["Profile"],
        summary: "Add user address",
        description: "Add a new address for the current user",
      },
    },
  )

  // Update User Address
  .put(
    "/addresses/:addressId",
    async ({ params, body, jwt, cookie: { auth } }) => {
      try {
        if (!auth.value) {
          return {
            success: false,
            error: "Authentication required",
          };
        }

        const payload = await jwt.verify(auth.value);
        if (!payload) {
          return {
            success: false,
            error: "Invalid token",
          };
        }

        const pool = await getPool();
        const queryBuilder = new QueryBuilder(pool);
        
        // Check if address exists and belongs to user
        const existingAddress = await queryBuilder.getAddressById(params.addressId, payload.userId as string);
        if (!existingAddress) {
          return {
            success: false,
            error: "Address not found",
          };
        }

        const updated = await queryBuilder.updateAddress(params.addressId, payload.userId as string, {
          full_address: body.fullAddress,
          city: body.city,
          postal_code: body.postalCode,
          country: body.country,
          address_comments: body.addressComments,
          is_default: body.isDefault,
        });

        if (!updated) {
          return {
            success: false,
            error: "Failed to update address",
          };
        }

        return {
          success: true,
          message: "Address updated successfully",
        };
      } catch (error) {
        console.error("Update address error:", error);
        return {
          success: false,
          error: "Failed to update address",
        };
      }
    },
    {
      params: t.Object({
        addressId: t.String(),
      }),
      body: t.Object({
        fullAddress: t.String({ minLength: 1 }),
        city: t.String({ minLength: 1 }),
        postalCode: t.Optional(t.String()),
        country: t.Optional(t.String()),
        addressComments: t.Optional(t.String()),
        isDefault: t.Optional(t.Boolean()),
      }),
      detail: {
        tags: ["Profile"],
        summary: "Update user address",
        description: "Update an existing address for the current user",
      },
    },
  )

  // Delete User Address
  .delete(
    "/addresses/:addressId",
    async ({ params, jwt, cookie: { auth } }) => {
      try {
        if (!auth.value) {
          return {
            success: false,
            error: "Authentication required",
          };
        }

        const payload = await jwt.verify(auth.value);
        if (!payload) {
          return {
            success: false,
            error: "Invalid token",
          };
        }

        const pool = await getPool();
        const queryBuilder = new QueryBuilder(pool);
        
        // Check if address exists and belongs to user
        const existingAddress = await queryBuilder.getAddressById(params.addressId, payload.userId as string);
        if (!existingAddress) {
          return {
            success: false,
            error: "Address not found",
          };
        }

        const deleted = await queryBuilder.deleteAddress(params.addressId, payload.userId as string);

        if (!deleted) {
          return {
            success: false,
            error: "Failed to delete address",
          };
        }

        return {
          success: true,
          message: "Address deleted successfully",
        };
      } catch (error) {
        console.error("Delete address error:", error);
        return {
          success: false,
          error: "Failed to delete address",
        };
      }
    },
    {
      params: t.Object({
        addressId: t.String(),
      }),
      detail: {
        tags: ["Profile"],
        summary: "Delete user address",
        description: "Delete an address for the current user",
      },
    },
  );