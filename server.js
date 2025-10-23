import express from "express";
import fetch from "node-fetch";
import cors from "cors";

const app = express();
app.use(cors());
app.use(express.json({ limit: "10mb" }));

// 健康檢查
app.get("/", (_req, res) => res.send("✅ GPT-5 Proxy running"));

/**
 * 與 OpenAI 介面相同的端點
 * Chatbot-UI 只要把 Base URL 指到這個服務即可
 */
app.post("/v1/chat/completions", async (req, res) => {
  try {
    const r = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${process.env.OPENAI_API_KEY}`
      },
      body: JSON.stringify(req.body)
    });

    // 直接把 OpenAI 的回應串流/轉發回去，避免前端等待超時
    res.status(r.status);
    for (const [k, v] of r.headers) res.setHeader(k, v);
    r.body.pipe(res);
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: String(e?.message || e) });
  }
});

const PORT = process.env.PORT || 8080;
app.listen(PORT, () => {
  console.log(`🚀 Proxy listening on :${PORT}`);
});