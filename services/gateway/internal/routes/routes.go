package routes

import (
	"bytes"
	"database/sql"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"net/url"
	"os"
	"time"

	"github.com/gofiber/fiber/v3"
	"golang.org/x/crypto/bcrypt"
	"github.com/doniabatool/virtual-tryon/gateway/internal/auth"
	"github.com/doniabatool/virtual-tryon/gateway/internal/middleware"
)

func Register(app *fiber.App, db *sql.DB) {
	// ─── DAPR subscriptions (must be public) ────────────────────────────────
	app.Get("/dapr/subscribe", daprSubscribeList())
	app.Post("/api/tryon-complete", daprTryonCompleteHandler(db))

	// ─── Auth routes (public) ────────────────────────────────────────────────
	authGroup := app.Group("/api/auth")
	authGroup.Post("/register", registerHandler(db))
	authGroup.Post("/login", loginHandler(db))

	// ─── Protected routes ────────────────────────────────────────────────────
	api := app.Group("/api", middleware.RequireAuth())

	// Try-on — proxy to Rust image-processor (which publishes DAPR event)
	api.Post("/tryon", tryOnHandler())
	api.Get("/tryon/:id", getTryOnResult(db))

	// Wardrobe
	api.Get("/wardrobe", getWardrobe(db))
	api.Post("/wardrobe", saveToWardrobe(db))
	api.Delete("/wardrobe/:id", deleteFromWardrobe(db))

	// Garments catalog
	api.Get("/garments", listGarments(db))

	// ML endpoints (proxied directly for measurements + search)
	api.Post("/measure",        proxyToML("/api/measure"))
	api.Post("/recommend-size", proxyToML("/api/recommend-size"))
	api.Get("/quantum-match",   proxyToML("/api/quantum-match"))
}

// ─── DAPR: what topics this gateway subscribes to ────────────────────────────

func daprSubscribeList() fiber.Handler {
	return func(c fiber.Ctx) error {
		return c.JSON([]fiber.Map{
			{
				"pubsubname": "pubsub",
				"topic":      "tryon.complete",
				"route":      "/api/tryon-complete",
			},
		})
	}
}

// ─── DAPR: receive tryon.complete event from ML pipeline ─────────────────────

type TryonCompleteEvent struct {
	RequestID       string  `json:"request_id"`
	ResultURL       string  `json:"result_url"`
	RecommendedSize string  `json:"recommended_size"`
	FitScore        int     `json:"fit_score"`
	InferenceTimeS  float64 `json:"inference_time_s"`
	Mode            string  `json:"mode"`
}

func daprTryonCompleteHandler(db *sql.DB) fiber.Handler {
	return func(c fiber.Ctx) error {
		// DAPR wraps payload in CloudEvents envelope
		type CloudEvent struct {
			Data TryonCompleteEvent `json:"data"`
		}
		var event CloudEvent
		if err := c.Bind().JSON(&event); err != nil {
			// Try direct parse (no envelope)
			var direct TryonCompleteEvent
			if err2 := c.Bind().JSON(&direct); err2 != nil {
				return c.Status(200).JSON(fiber.Map{"status": "parse_error"})
			}
			event.Data = direct
		}

		d := event.Data
		if d.RequestID == "" {
			return c.Status(200).JSON(fiber.Map{"status": "skipped"})
		}

		// Save result to database
		_, _ = db.Exec(
			`INSERT INTO tryon_results (id, result_image, model_used, inference_time_ms, created_at)
			 VALUES ($1, $2, $3, $4, NOW())
			 ON CONFLICT (id) DO UPDATE
			 SET result_image = EXCLUDED.result_image`,
			d.RequestID,
			d.ResultURL,
			d.Mode,
			int(d.InferenceTimeS*1000),
		)

		fmt.Printf("✅ tryon.complete: request=%s size=%s fit=%d%% mode=%s\n",
			d.RequestID, d.RecommendedSize, d.FitScore, d.Mode)

		return c.Status(200).JSON(fiber.Map{"status": "ok"})
	}
}

// ─── Auth handlers ────────────────────────────────────────────────────────────

type RegisterRequest struct {
	Name     string `json:"name"`
	Email    string `json:"email"`
	Password string `json:"password"`
}

func registerHandler(db *sql.DB) fiber.Handler {
	return func(c fiber.Ctx) error {
		var req RegisterRequest
		if err := c.Bind().JSON(&req); err != nil {
			return c.Status(400).JSON(fiber.Map{"error": "invalid request body"})
		}
		if req.Email == "" || req.Password == "" || req.Name == "" {
			return c.Status(400).JSON(fiber.Map{"error": "name, email and password are required"})
		}
		if len(req.Password) < 8 {
			return c.Status(400).JSON(fiber.Map{"error": "password must be at least 8 characters"})
		}

		hash, err := bcrypt.GenerateFromPassword([]byte(req.Password), bcrypt.DefaultCost)
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "internal error"})
		}

		var userID string
		err = db.QueryRow(
			`INSERT INTO users (email, name, password) VALUES ($1, $2, $3) RETURNING id`,
			req.Email, req.Name, string(hash),
		).Scan(&userID)
		if err != nil {
			return c.Status(409).JSON(fiber.Map{"error": "email already registered"})
		}

		token, err := auth.GenerateToken(userID, req.Email)
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "token generation failed"})
		}

		return c.Status(201).JSON(fiber.Map{
			"token": token, "user_id": userID, "email": req.Email, "name": req.Name,
		})
	}
}

type LoginRequest struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}

func loginHandler(db *sql.DB) fiber.Handler {
	return func(c fiber.Ctx) error {
		var req LoginRequest
		if err := c.Bind().JSON(&req); err != nil {
			return c.Status(400).JSON(fiber.Map{"error": "invalid request body"})
		}

		var userID, name, hashedPassword string
		err := db.QueryRow(
			`SELECT id, name, password FROM users WHERE email = $1`, req.Email,
		).Scan(&userID, &name, &hashedPassword)
		if err != nil {
			return c.Status(401).JSON(fiber.Map{"error": "invalid email or password"})
		}

		if err := bcrypt.CompareHashAndPassword([]byte(hashedPassword), []byte(req.Password)); err != nil {
			return c.Status(401).JSON(fiber.Map{"error": "invalid email or password"})
		}

		token, err := auth.GenerateToken(userID, req.Email)
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "token generation failed"})
		}

		return c.JSON(fiber.Map{
			"token": token, "user_id": userID, "email": req.Email, "name": name,
		})
	}
}

// ─── Try-on: proxy multipart to Rust image-processor ─────────────────────────

func tryOnHandler() fiber.Handler {
	imageProcessorURL := os.Getenv("IMAGE_PROCESSOR_URL")
	if imageProcessorURL == "" {
		imageProcessorURL = "http://localhost:8090"
	}
	client := &http.Client{Timeout: 60 * time.Second}

	return func(c fiber.Ctx) error {
		// Re-stream multipart body to Rust image-processor
		body := &bytes.Buffer{}
		writer := multipart.NewWriter(body)

		form, err := c.MultipartForm()
		if err != nil {
			return c.Status(400).JSON(fiber.Map{"error": "multipart form required"})
		}

		// Forward file fields
		for fieldName, files := range form.File {
			for _, fh := range files {
				part, _ := writer.CreateFormFile(fieldName, fh.Filename)
				f, _ := fh.Open()
				io.Copy(part, f)
				f.Close()
			}
		}

		// Forward value fields
		for fieldName, vals := range form.Value {
			for _, v := range vals {
				writer.WriteField(fieldName, v)
			}
		}
		writer.Close()

		resp, err := client.Post(
			imageProcessorURL+"/api/upload",
			writer.FormDataContentType(),
			body,
		)
		if err != nil {
			return c.Status(502).JSON(fiber.Map{"error": "image-processor unavailable"})
		}
		defer resp.Body.Close()

		respBody, _ := io.ReadAll(resp.Body)
		c.Set("Content-Type", "application/json")
		return c.Status(resp.StatusCode).Send(respBody)
	}
}

// ─── Get try-on result ────────────────────────────────────────────────────────

func getTryOnResult(db *sql.DB) fiber.Handler {
	return func(c fiber.Ctx) error {
		id := c.Params("id")

		var resultImage, modelUsed string
		var inferenceTimeMs int
		var createdAt time.Time

		err := db.QueryRow(
			`SELECT result_image, model_used, inference_time_ms, created_at
			 FROM tryon_results WHERE id = $1`, id,
		).Scan(&resultImage, &modelUsed, &inferenceTimeMs, &createdAt)

		if err == sql.ErrNoRows {
			return c.Status(202).JSON(fiber.Map{
				"status":     "processing",
				"request_id": id,
				"message":    "Result not ready yet — poll again in 5 seconds",
			})
		}
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "database error"})
		}

		return c.JSON(fiber.Map{
			"status":             "complete",
			"request_id":         id,
			"result_image_url":   resultImage,
			"model":              modelUsed,
			"inference_time_ms":  inferenceTimeMs,
			"completed_at":       createdAt,
		})
	}
}

// ─── Wardrobe handlers ────────────────────────────────────────────────────────

func getWardrobe(db *sql.DB) fiber.Handler {
	return func(c fiber.Ctx) error {
		userID := c.Locals("user_id").(string)
		rows, err := db.Query(
			`SELECT w.id, w.name, w.saved_at, tr.result_image
			 FROM wardrobe w JOIN tryon_results tr ON w.tryon_result_id = tr.id
			 WHERE w.user_id = $1 ORDER BY w.saved_at DESC`, userID,
		)
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "database error"})
		}
		defer rows.Close()

		type WardrobeItem struct {
			ID          string    `json:"id"`
			Name        string    `json:"name"`
			SavedAt     time.Time `json:"saved_at"`
			ResultImage string    `json:"result_image"`
		}
		var items []WardrobeItem
		for rows.Next() {
			var item WardrobeItem
			rows.Scan(&item.ID, &item.Name, &item.SavedAt, &item.ResultImage)
			items = append(items, item)
		}
		if items == nil {
			items = []WardrobeItem{}
		}
		return c.JSON(items)
	}
}

func saveToWardrobe(db *sql.DB) fiber.Handler {
	return func(c fiber.Ctx) error {
		userID := c.Locals("user_id").(string)
		type Req struct {
			TryonResultID string `json:"tryon_result_id"`
			Name          string `json:"name"`
		}
		var req Req
		c.Bind().JSON(&req)
		_, err := db.Exec(
			`INSERT INTO wardrobe (user_id, tryon_result_id, name) VALUES ($1, $2, $3)`,
			userID, req.TryonResultID, req.Name,
		)
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "save failed"})
		}
		return c.JSON(fiber.Map{"status": "saved"})
	}
}

func deleteFromWardrobe(db *sql.DB) fiber.Handler {
	return func(c fiber.Ctx) error {
		id := c.Params("id")
		userID := c.Locals("user_id").(string)
		db.Exec(`DELETE FROM wardrobe WHERE id = $1 AND user_id = $2`, id, userID)
		return c.JSON(fiber.Map{"deleted": id})
	}
}

// ─── Garments ─────────────────────────────────────────────────────────────────

func listGarments(db *sql.DB) fiber.Handler {
	return func(c fiber.Ctx) error {
		category := c.Query("category", "")
		query := `SELECT id, name, category, brand, color, image_url FROM garments`
		args := []interface{}{}
		if category != "" {
			query += ` WHERE category = $1`
			args = append(args, category)
		}
		query += ` ORDER BY created_at DESC LIMIT 50`

		rows, err := db.Query(query, args...)
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "database error"})
		}
		defer rows.Close()

		var garments []fiber.Map
		for rows.Next() {
			var id, name, cat, brand, color, imageURL string
			rows.Scan(&id, &name, &cat, &brand, &color, &imageURL)
			garments = append(garments, fiber.Map{
				"id": id, "name": name, "category": cat,
				"brand": brand, "color": color, "image_url": imageURL,
			})
		}
		if garments == nil {
			garments = []fiber.Map{}
		}
		return c.JSON(garments)
	}
}

// ─── ML proxy ─────────────────────────────────────────────────────────────────

func proxyToML(path string) fiber.Handler {
	mlURL := os.Getenv("ML_PIPELINE_URL")
	if mlURL == "" {
		mlURL = "http://localhost:8001"
	}
	client := &http.Client{Timeout: 120 * time.Second}

	return func(c fiber.Ctx) error {
		reqURL := mlURL + path
		if c.Method() == "GET" && len(c.Queries()) > 0 {
			params := url.Values{}
			for k, v := range c.Queries() {
				params.Set(k, v)
			}
			reqURL += "?" + params.Encode()
		}

		var req *http.Request
		var err error
		if c.Method() == "POST" {
			req, err = http.NewRequest("POST", reqURL, bytes.NewReader(c.Body()))
			req.Header.Set("Content-Type", c.Get("Content-Type"))
		} else {
			req, err = http.NewRequest("GET", reqURL, nil)
		}
		if err != nil {
			return c.Status(502).JSON(fiber.Map{"error": "proxy error"})
		}

		resp, err := client.Do(req)
		if err != nil {
			return c.Status(502).JSON(fiber.Map{"error": "ml-pipeline unavailable"})
		}
		defer resp.Body.Close()

		respBody, _ := io.ReadAll(resp.Body)
		c.Set("Content-Type", "application/json")
		return c.Status(resp.StatusCode).Send(respBody)
	}
}
