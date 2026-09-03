/// Virtual Try-On — Rust Image Processor  (Week 4 — Full DAPR Integration)
/// Axum web server — Port 8090
///
/// Flow:
/// 1. Accept multipart upload (person_image + garment_image)
/// 2. Resize: person → 512×512, garment → 768×1024  (Lanczos3, 10× faster than Python PIL)
/// 3. Upload both to MinIO (S3-compatible)
/// 4. Publish DAPR event "images.ready" → Python ML pipeline picks up automatically

use axum::{
    extract::Multipart,
    http::StatusCode,
    response::Json,
    routing::{get, post},
    Router,
};
use aws_sdk_s3::{
    config::{Builder, Credentials, Region},
    primitives::ByteStream,
    Client as S3Client,
};
use reqwest::Client as HttpClient;
use serde::Serialize;
use serde_json::{json, Value};
use std::net::SocketAddr;
use std::sync::Arc;
use tower_http::cors::{Any, CorsLayer};
use tracing::{error, info, warn};
use uuid::Uuid;

// ─── Shared app state ─────────────────────────────────────────────────────────

#[derive(Clone)]
struct AppState {
    s3:          Arc<S3Client>,
    http:        Arc<HttpClient>,
    minio_bucket: String,
    minio_url:   String,
    dapr_port:   String,
}

// ─── Response types ───────────────────────────────────────────────────────────

#[derive(Serialize)]
struct UploadResponse {
    request_id:        String,
    person_image_url:  String,
    garment_image_url: String,
    status:            String,
    dapr_published:    bool,
}

#[derive(Serialize)]
struct HealthResponse {
    status:         String,
    service:        String,
    port:           u16,
    minio_endpoint: String,
    dapr_port:      String,
}

// ─── Main ─────────────────────────────────────────────────────────────────────

#[tokio::main]
async fn main() {
    dotenvy::from_path("../../.env").ok();
    dotenvy::dotenv().ok();

    tracing_subscriber::fmt()
        .with_env_filter("image_processor=info,tower_http=warn")
        .init();

    // MinIO / S3 config
    let endpoint  = std::env::var("MINIO_ENDPOINT")
        .unwrap_or_else(|_| "http://localhost:9000".to_string());
    let access    = std::env::var("MINIO_ACCESS_KEY")
        .unwrap_or_else(|_| "minioadmin".to_string());
    let secret    = std::env::var("MINIO_SECRET_KEY")
        .unwrap_or_else(|_| "minioadmin".to_string());
    let bucket    = std::env::var("MINIO_BUCKET")
        .unwrap_or_else(|_| "tryon-images".to_string());
    let dapr_port = std::env::var("DAPR_HTTP_PORT")
        .unwrap_or_else(|_| "3502".to_string());

    let creds  = Credentials::new(&access, &secret, None, None, "minio");
    let region = Region::new("us-east-1");

    let s3_config = Builder::new()
        .endpoint_url(&endpoint)
        .credentials_provider(creds)
        .region(region)
        .force_path_style(true)  // MinIO requires path-style
        .build();

    let s3  = Arc::new(S3Client::from_conf(s3_config));
    let http = Arc::new(HttpClient::new());

    // Ensure bucket exists
    ensure_bucket(&s3, &bucket).await;

    let state = AppState {
        s3,
        http,
        minio_bucket: bucket,
        minio_url:    endpoint,
        dapr_port,
    };

    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods(Any)
        .allow_headers(Any);

    let app = Router::new()
        .route("/health",     get(health_handler))
        .route("/api/upload", post(upload_handler))
        .with_state(state)
        .layer(cors);

    let port: u16 = std::env::var("IMAGE_PROCESSOR_PORT")
        .unwrap_or_else(|_| "8090".to_string())
        .parse()
        .unwrap_or(8090);

    let addr = SocketAddr::from(([0, 0, 0, 0], port));
    info!("🦀 Rust Image Processor running on :{}", port);

    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}

// ─── Ensure MinIO bucket exists ───────────────────────────────────────────────

async fn ensure_bucket(s3: &S3Client, bucket: &str) {
    match s3.head_bucket().bucket(bucket).send().await {
        Ok(_) => info!("✅ MinIO bucket '{}' exists", bucket),
        Err(_) => {
            match s3.create_bucket().bucket(bucket).send().await {
                Ok(_)  => info!("✅ Created MinIO bucket '{}'", bucket),
                Err(e) => warn!("⚠️  Could not create bucket: {}", e),
            }
        }
    }
}

// ─── Health ───────────────────────────────────────────────────────────────────

async fn health_handler(
    axum::extract::State(state): axum::extract::State<AppState>,
) -> Json<HealthResponse> {
    Json(HealthResponse {
        status:         "ok".to_string(),
        service:        "image-processor".to_string(),
        port:           8090,
        minio_endpoint: state.minio_url.clone(),
        dapr_port:      state.dapr_port.clone(),
    })
}

// ─── Upload handler ───────────────────────────────────────────────────────────

async fn upload_handler(
    axum::extract::State(state): axum::extract::State<AppState>,
    mut multipart: Multipart,
) -> Result<Json<UploadResponse>, (StatusCode, Json<Value>)> {
    let request_id = Uuid::new_v4().to_string();
    let mut person_bytes:  Option<Vec<u8>> = None;
    let mut garment_bytes: Option<Vec<u8>> = None;
    let mut height_cm: f32 = 165.0;

    // ── Parse multipart ───────────────────────────────────────────────────────
    while let Ok(Some(field)) = multipart.next_field().await {
        let name = field.name().unwrap_or("").to_string();
        match name.as_str() {
            "person_image" => {
                person_bytes = Some(field.bytes().await
                    .map_err(|e| err(StatusCode::BAD_REQUEST, &e.to_string()))?.to_vec());
            }
            "garment_image" => {
                garment_bytes = Some(field.bytes().await
                    .map_err(|e| err(StatusCode::BAD_REQUEST, &e.to_string()))?.to_vec());
            }
            "height_cm" => {
                let text = field.text().await.unwrap_or_default();
                height_cm = text.parse().unwrap_or(165.0);
            }
            _ => {}
        }
    }

    let person_data  = person_bytes.ok_or(err(StatusCode::BAD_REQUEST, "person_image required"))?;
    let garment_data = garment_bytes.ok_or(err(StatusCode::BAD_REQUEST, "garment_image required"))?;

    // ── Resize (blocking — spawn to thread pool) ──────────────────────────────
    let person_data_r  = person_data.clone();
    let garment_data_r = garment_data.clone();

    let person_resized = tokio::task::spawn_blocking(move || {
        resize_image(&person_data_r, 512, 512)
    }).await.unwrap().map_err(|e| err(StatusCode::INTERNAL_SERVER_ERROR, &e))?;

    let garment_resized = tokio::task::spawn_blocking(move || {
        resize_image(&garment_data_r, 768, 1024)
    }).await.unwrap().map_err(|e| err(StatusCode::INTERNAL_SERVER_ERROR, &e))?;

    info!("✅ Resized — person: {}KB, garment: {}KB",
        person_resized.len() / 1024, garment_resized.len() / 1024);

    // ── Upload to MinIO ───────────────────────────────────────────────────────
    let person_key  = format!("uploads/{}/person.jpg",  request_id);
    let garment_key = format!("uploads/{}/garment.jpg", request_id);

    upload_to_minio(&state.s3, &state.minio_bucket, &person_key, person_resized, "image/jpeg").await
        .map_err(|e| err(StatusCode::INTERNAL_SERVER_ERROR, &e))?;

    upload_to_minio(&state.s3, &state.minio_bucket, &garment_key, garment_resized, "image/jpeg").await
        .map_err(|e| err(StatusCode::INTERNAL_SERVER_ERROR, &e))?;

    let person_url  = format!("{}/{}/{}", state.minio_url, state.minio_bucket, person_key);
    let garment_url = format!("{}/{}/{}", state.minio_url, state.minio_bucket, garment_key);

    info!("📦 Uploaded to MinIO: {} | {}", person_url, garment_url);

    // ── Publish DAPR event "images.ready" ─────────────────────────────────────
    let dapr_published = publish_dapr_event(
        &state.http,
        &state.dapr_port,
        "images.ready",
        json!({
            "request_id":        request_id,
            "person_image_url":  person_url,
            "garment_image_url": garment_url,
            "height_cm":         height_cm,
        }),
    ).await;

    Ok(Json(UploadResponse {
        request_id,
        person_image_url:  person_url,
        garment_image_url: garment_url,
        status: "uploaded".to_string(),
        dapr_published,
    }))
}

// ─── MinIO upload ─────────────────────────────────────────────────────────────

async fn upload_to_minio(
    s3:     &S3Client,
    bucket: &str,
    key:    &str,
    data:   Vec<u8>,
    mime:   &str,
) -> Result<(), String> {
    s3.put_object()
        .bucket(bucket)
        .key(key)
        .body(ByteStream::from(data))
        .content_type(mime)
        .send()
        .await
        .map_err(|e| format!("MinIO upload failed: {}", e))?;
    Ok(())
}

// ─── DAPR event publish ───────────────────────────────────────────────────────

async fn publish_dapr_event(
    http:      &HttpClient,
    dapr_port: &str,
    topic:     &str,
    payload:   Value,
) -> bool {
    let url = format!("http://localhost:{}/v1.0/publish/pubsub/{}", dapr_port, topic);
    match http
        .post(&url)
        .header("Content-Type", "application/json")
        .json(&payload)
        .send()
        .await
    {
        Ok(resp) if resp.status().is_success() => {
            info!("📤 DAPR event published: {}", topic);
            true
        }
        Ok(resp) => {
            warn!("⚠️  DAPR publish returned {}: {}", resp.status(), topic);
            false
        }
        Err(e) => {
            warn!("⚠️  DAPR publish failed (non-blocking): {}", e);
            false
        }
    }
}

// ─── Image resize ─────────────────────────────────────────────────────────────

fn resize_image(data: &[u8], width: u32, height: u32) -> Result<Vec<u8>, String> {
    let img = image::load_from_memory(data)
        .map_err(|e| format!("Decode failed: {}", e))?;

    let resized = img.resize_exact(width, height, image::imageops::FilterType::Lanczos3);

    let mut out    = Vec::new();
    let mut cursor = std::io::Cursor::new(&mut out);
    resized
        .write_to(&mut cursor, image::ImageFormat::Jpeg)
        .map_err(|e| format!("JPEG encode failed: {}", e))?;

    Ok(out)
}

// ─── Error helper ─────────────────────────────────────────────────────────────

fn err(status: StatusCode, msg: &str) -> (StatusCode, Json<Value>) {
    error!("❌ {}", msg);
    (status, Json(json!({"error": msg})))
}
