/**
 * API client — all requests go through Go Gateway :3004
 */

const BASE_URL = process.env.NEXT_PUBLIC_GATEWAY_URL ?? "http://localhost:3004";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = typeof document !== "undefined"
    ? document.cookie.match(/token=([^;]+)/)?.[1]
    : null;

  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error ?? `Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

export const apiClient = {
  register: (name: string, email: string, password: string) =>
    request<{ token: string; user_id: string; name: string }>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ name, email, password }),
    }),

  login: (email: string, password: string) =>
    request<{ token: string; user_id: string; name: string }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  // ─── Try-On ────────────────────────────────────────────────────────────────
  tryOn: (personImage: File, garmentImage: File) => {
    const form = new FormData();
    form.append("person_image", personImage);
    form.append("garment_image", garmentImage);
    return request<{ request_id: string; result_url?: string; status: string }>(
      "/api/tryon",
      { method: "POST", body: form, headers: {} }  // no Content-Type for multipart
    );
  },

  measureBody: (personImage: File) => {
    const form = new FormData();
    form.append("person_image", personImage);
    return request<{
      shoulder_cm: number; chest_cm: number;
      waist_cm: number; hip_cm: number; height_cm: number;
    }>("/api/measure", { method: "POST", body: form, headers: {} });
  },

  recommendSize: (measurements: Record<string, number>) =>
    request<{ predicted_size: string; fit_score: number }>("/api/recommend-size", {
      method: "POST",
      body: JSON.stringify(measurements),
    }),

  quantumMatch: (bodyType: string, category: string) =>
    request<{ matches: Array<{ garment_id: string; quantum_score: number; name: string }> }>(
      `/api/quantum-match?body_type=${bodyType}&category=${category}`
    ),

  // ─── Garments ──────────────────────────────────────────────────────────────
  listGarments: (category?: string) =>
    request<Garment[]>(`/api/garments${category ? `?category=${category}` : ""}`),

  // ─── Wardrobe ──────────────────────────────────────────────────────────────
  getWardrobe: () => request<WardrobeItem[]>("/api/wardrobe"),

  saveToWardrobe: (tryonResultId: string, name: string) =>
    request<{ id: string }>("/api/wardrobe", {
      method: "POST",
      body: JSON.stringify({ tryon_result_id: tryonResultId, name }),
    }),

  deleteFromWardrobe: (id: string) =>
    request<void>(`/api/wardrobe/${id}`, { method: "DELETE" }),
};

// ─── Types ────────────────────────────────────────────────────────────────────

export interface Garment {
  id: string;
  name: string;
  category: string;
  brand: string;
  color: string;
  image_url: string;
  sizes: string[];
}

export interface WardrobeItem {
  id: string;
  name: string;
  saved_at: string;
  result_image: string;
}
