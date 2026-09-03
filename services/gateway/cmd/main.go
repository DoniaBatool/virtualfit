package main

import (
	"database/sql"
	"log"
	"os"

	"github.com/gofiber/fiber/v3"
	"github.com/gofiber/fiber/v3/middleware/cors"
	"github.com/gofiber/fiber/v3/middleware/logger"
	"github.com/joho/godotenv"
	_ "github.com/lib/pq"

	"github.com/doniabatool/virtual-tryon/gateway/internal/routes"
)

func main() {
	// Load .env
	if err := godotenv.Load("../../.env"); err != nil {
		log.Println("No .env file — using environment variables")
	}

	// Connect to PostgreSQL
	db, err := sql.Open("postgres", os.Getenv("DATABASE_URL"))
	if err != nil {
		log.Fatalf("DB connect failed: %v", err)
	}
	defer db.Close()

	if err := db.Ping(); err != nil {
		log.Printf("⚠️  DB not reachable: %v — running without DB", err)
	} else {
		log.Println("✅ PostgreSQL connected")
	}

	// Fiber v3 app
	app := fiber.New(fiber.Config{
		AppName: "Virtual Try-On Gateway v1.0",
	})

	// Middleware
	app.Use(logger.New())
	app.Use(cors.New(cors.Config{
		AllowOrigins: []string{"http://localhost:3002"},
		AllowHeaders: []string{"Origin", "Content-Type", "Authorization"},
	}))

	// Health check
	app.Get("/health", func(c fiber.Ctx) error {
		return c.JSON(fiber.Map{
			"status":  "ok",
			"service": "virtual-tryon-gateway",
			"port":    "3004",
		})
	})

	// Register all routes
	routes.Register(app, db)

	port := os.Getenv("GATEWAY_PORT")
	if port == "" {
		port = "3004"
	}

	log.Printf("🚀 Gateway running on :%s", port)
	log.Fatal(app.Listen(":" + port))
}
