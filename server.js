import express from "express";
import fetch from "node-fetch";
import cors from "cors";

const app = express();
app.use(cors());
app.use(express.json({ limit: "15mb" }));

app.use((req, res, next) => {
  res.setTimeout(120000); // 120 秒
  next();
});

// Health check
app.get("/", (_req, res) => res.send("✅ GPT-5 Proxy running"));

// OpenAI-compatible Chat Completions proxy
app.post("/v1/chat/completions", async (req, res) => {
  try {
    const upstream = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${process.env.OPENAI_API_KEY}`
      },
      body: JSON.stringify(req.body)
    });

    res.status(upstream.status);
    upstream.headers.forEach((v, k) => res.setHeader(k, v));
    if (upstream.body) upstream.body.pipe(res);
    else res.end(await upstream.text());
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: String(err?.message || err) });
  }
});

// Generic passthrough for other OpenAI v1 endpoints (Assistants, files...)
app.all("/v1/*", async (req, res) => {
  try {
    const url = "https://api.openai.com" + req.originalUrl;
    const init = {
      method: req.method,
      headers: {
        "Authorization": `Bearer ${process.env.OPENAI_API_KEY}`,
        ...(req.headers["content-type"] ? {"Content-Type": req.headers["content-type"]} : {})
      }
    };
    if (!["GET","HEAD"].includes(req.method)) {
      init.body = JSON.stringify(req.body || {});
    }
    const upstream = await fetch(url, init);

    res.status(upstream.status);
    upstream.headers.forEach((v, k) => res.setHeader(k, v));
    if (upstream.body) upstream.body.pipe(res);
    else res.end(await upstream.text());
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: String(err?.message || err) });
  }
});

const PORT = process.env.PORT || 8080;
app.listen(PORT, () => console.log(`🚀 Proxy listening on :${PORT}`));
