from fastapi import FastAPI

app = FastAPI(title="X Investor Copilot API")

@app.get("/health")
def health():
    return {"ok": True}
