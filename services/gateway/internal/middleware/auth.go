package middleware

import (
	"strings"

	"github.com/gofiber/fiber/v3"
	"github.com/doniabatool/virtual-tryon/gateway/internal/auth"
)

// RequireAuth validates JWT token from Authorization header
func RequireAuth() fiber.Handler {
	return func(c fiber.Ctx) error {
		header := c.Get("Authorization")
		if header == "" {
			return c.Status(401).JSON(fiber.Map{"error": "missing Authorization header"})
		}

		parts := strings.SplitN(header, " ", 2)
		if len(parts) != 2 || parts[0] != "Bearer" {
			return c.Status(401).JSON(fiber.Map{"error": "invalid Authorization format"})
		}

		claims, err := auth.ValidateToken(parts[1])
		if err != nil {
			return c.Status(401).JSON(fiber.Map{"error": "invalid or expired token"})
		}

		// Store claims in context for handlers
		c.Locals("user_id", claims.UserID)
		c.Locals("email", claims.Email)
		return c.Next()
	}
}
