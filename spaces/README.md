# VirtualFit — AI Virtual Try-On

**Polyglot AI system:** IDM-VTON · SAM2 · MediaPipe · TensorFlow · Qiskit Grover's O(√N)

Upload your photo + any garment → see yourself wearing it instantly.

## Deploy on Streamlit Cloud (Free)

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect GitHub → select this repo → set `app_file: spaces/app.py`
4. Click **Deploy** — live in ~2 minutes!

## Stack

- **Frontend:** Streamlit
- **Try-On:** PIL Composite (Fast Preview) — IDM-VTON ready when weights downloaded
- **Size:** Rule-based + TensorFlow Dense Network
- **Search:** Qiskit Grover's O(√N) — 4-qubit, 16-garment catalog

## Local Run

```bash
pip install -r spaces/requirements.txt
streamlit run spaces/app.py
```
