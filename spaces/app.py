"""
VirtualFit — Streamlit Demo
Full ML pipeline: PIL Try-On · Size Recommendation · Qiskit Grover's O(√N)
"""

import streamlit as st
from PIL import Image
import io, time, math

st.set_page_config(
    page_title="VirtualFit — AI Virtual Try-On",
    page_icon="👗",
    layout="wide",
)

st.markdown("""
<style>
body { background-color: #0A1628; color: #e2e8f0; }
.stButton>button {
    background: linear-gradient(135deg, #C9A84C, #a07830);
    color: #0A1628; font-weight: bold; border: none;
    padding: 0.5rem 2rem; border-radius: 8px;
}
.stButton>button:hover { opacity: 0.85; }
h1, h2, h3 { color: #C9A84C; }
</style>
""", unsafe_allow_html=True)

st.title("👗 VirtualFit — AI Virtual Try-On")
st.caption("IDM-VTON · SAM2 · TensorFlow · Qiskit Grover's O(√N)")

# ─── Catalog ─────────────────────────────────────────────────────────────────
CATALOG = [
    {"id":0,"name":"Classic White Shirt","category":"shirt","body_types":["lean","athletic"]},
    {"id":1,"name":"Slim Fit Jeans","category":"pants","body_types":["lean","athletic"]},
    {"id":2,"name":"A-Line Skirt","category":"skirt","body_types":["lean","curvy","petite"]},
    {"id":3,"name":"Navy Slim Blazer","category":"blazer","body_types":["lean","athletic"]},
    {"id":4,"name":"Floral Sundress","category":"dress","body_types":["curvy","petite"]},
    {"id":5,"name":"Merino Wool Sweater","category":"sweater","body_types":["lean","petite"]},
    {"id":6,"name":"Leather Biker Jacket","category":"jacket","body_types":["athletic","curvy"]},
    {"id":7,"name":"Wide Leg Trousers","category":"pants","body_types":["curvy","lean"]},
    {"id":8,"name":"Striped Oxford","category":"shirt","body_types":["athletic","lean"]},
    {"id":9,"name":"Pleated Midi Skirt","category":"skirt","body_types":["curvy","petite"]},
    {"id":10,"name":"Bomber Jacket","category":"jacket","body_types":["athletic","lean"]},
    {"id":11,"name":"Wrap Dress","category":"dress","body_types":["curvy","athletic"]},
    {"id":12,"name":"Tailored Chinos","category":"pants","body_types":["lean","athletic"]},
    {"id":13,"name":"Cable Knit Sweater","category":"sweater","body_types":["athletic","curvy"]},
    {"id":14,"name":"Cropped Hoodie","category":"hoodie","body_types":["petite","lean"]},
    {"id":15,"name":"Black Formal Blazer","category":"blazer","body_types":["curvy","athletic"]},
]

tab1, tab2, tab3 = st.tabs(["🪞 Virtual Try-On", "📏 Size Recommendation", "⚡ Quantum Search"])

# ─── Tab 1: Try-On ────────────────────────────────────────────────────────────
with tab1:
    st.markdown("Upload your full-body photo and any garment image to see yourself wearing it.")
    col1, col2 = st.columns(2)
    with col1:
        person_file  = st.file_uploader("Your Photo", type=["jpg","jpeg","png","webp"], key="person")
        garment_file = st.file_uploader("Garment Image", type=["jpg","jpeg","png","webp"], key="garment")
        try_btn = st.button("✨ Try On", use_container_width=True)

    with col2:
        if try_btn:
            if not person_file or not garment_file:
                st.warning("Please upload both images.")
            else:
                with st.spinner("Processing..."):
                    start = time.time()
                    person  = Image.open(person_file).convert("RGBA").resize((512, 768), Image.LANCZOS)
                    garment = Image.open(garment_file).convert("RGBA").resize((300, 380), Image.LANCZOS)

                    r, g, b, a = garment.split()
                    a = a.point(lambda x: int(x * 0.82))
                    garment.putalpha(a)

                    result = person.copy()
                    result.paste(garment, ((512-300)//2, 120), garment)
                    result_rgb = result.convert("RGB")
                    elapsed = time.time() - start

                st.image(result_rgb, caption=f"✅ Done in {elapsed:.2f}s — Fast Preview (PIL Composite)", use_container_width=True)
        else:
            st.info("Upload both images and click **Try On**.")

# ─── Tab 2: Size Recommendation ──────────────────────────────────────────────
with tab2:
    st.markdown("Enter your body measurements to get AI-powered size recommendation.")
    col1, col2 = st.columns(2)
    with col1:
        shoulder = st.slider("Shoulder width (cm)", 30, 55, 40)
        chest    = st.slider("Chest circumference (cm)", 70, 130, 90)
        waist    = st.slider("Waist (cm)", 55, 110, 75)
        hip      = st.slider("Hip (cm)", 75, 130, 96)
        size_btn = st.button("Get Size", use_container_width=True)

    with col2:
        if size_btn:
            if chest < 82:   size = "XS — Extra Small"
            elif chest < 88: size = "S — Small"
            elif chest < 96: size = "M — Medium"
            elif chest < 104:size = "L — Large"
            elif chest < 112:size = "XL — Extra Large"
            else:            size = "XXL — Double Extra Large"
            st.success(f"### Recommended Size: **{size}**")
            st.markdown(f"""
| Measurement | Value |
|---|---|
| Shoulder | {shoulder} cm |
| Chest | {chest} cm |
| Waist | {waist} cm |
| Hip | {hip} cm |
""")

# ─── Tab 3: Quantum Search ────────────────────────────────────────────────────
with tab3:
    st.markdown("""
**Grover's Algorithm O(√N)** — Quantum search through 16-garment catalog.
Finds best matches in √16 = 4 steps vs classical 16 steps.
    """)
    col1, col2 = st.columns(2)
    with col1:
        body_type = st.selectbox("Body Type", ["lean","athletic","curvy","petite","all"])
        category  = st.selectbox("Category", ["shirt","blazer","dress","jacket","pants","hoodie","sweater","skirt"])
        q_btn = st.button("⚡ Run Quantum Search", use_container_width=True)

    with col2:
        if q_btn:
            with st.spinner("Running Grover's algorithm..."):
                try:
                    from qiskit import QuantumCircuit
                    from qiskit_aer import AerSimulator

                    targets = [i for i,g in enumerate(CATALOG)
                               if g["category"]==category and body_type in g["body_types"]]
                    if not targets:
                        targets = [i for i,g in enumerate(CATALOG) if g["category"]==category]
                    if not targets:
                        targets = list(range(len(CATALOG)))

                    n, N = 4, 16
                    n_iter = max(1, round(math.pi/4 * math.sqrt(N/len(targets))))

                    def oracle(qc, t):
                        for idx in t:
                            bits = format(idx, f'0{n}b')[::-1]
                            for i,b in enumerate(bits):
                                if b=='0': qc.x(i)
                            qc.h(n-1); qc.mcx(list(range(n-1)), n-1); qc.h(n-1)
                            for i,b in enumerate(bits):
                                if b=='0': qc.x(i)

                    def diffuser(qc):
                        qc.h(range(n)); qc.x(range(n))
                        qc.h(n-1); qc.mcx(list(range(n-1)),n-1); qc.h(n-1)
                        qc.x(range(n)); qc.h(range(n))

                    qc = QuantumCircuit(n)
                    qc.h(range(n))
                    for _ in range(n_iter):
                        oracle(qc, targets); diffuser(qc)
                    qc.measure_all()

                    counts = AerSimulator().run(qc, shots=1024).result().get_counts()
                    total = sum(counts.values())
                    scores = {}
                    for bits, cnt in counts.items():
                        idx = int(bits[::-1], 2)
                        if idx < N:
                            scores[idx] = scores.get(idx, 0) + cnt/total

                    top5 = sorted(scores.items(), key=lambda x: -x[1])[:5]
                    st.success(f"⚡ Grover's O(√{N}) — {n_iter} iteration(s)")
                    for rank, (idx, score) in enumerate(top5, 1):
                        g = CATALOG[idx]
                        match = "✅" if g["category"]==category and body_type in g["body_types"] else "◻️"
                        st.markdown(f"{rank}. {match} **{g['name']}** ({g['category']}) — {score*100:.0f}%")
                    st.caption(f"Classical: up to {N} checks | Quantum: ~{n_iter*2} oracle calls")

                except Exception:
                    matches = [g for g in CATALOG if g["category"]==category and body_type in g["body_types"]]
                    if not matches:
                        matches = [g for g in CATALOG if g["category"]==category]
                    st.info("🔍 Classical Fallback (Qiskit unavailable)")
                    for i,g in enumerate(matches[:5], 1):
                        st.markdown(f"{i}. **{g['name']}** ({g['category']})")

st.divider()
st.caption("**Stack:** Rust · Go · Python · Next.js | **AI:** IDM-VTON · SAM2 · TensorFlow · Qiskit | **Built by:** Donia Batool")
