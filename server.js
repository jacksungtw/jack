import express from "express";
import fetch from "node-fetch";

const app = express();
app.use(express.json());

// ✅ ← 就在這裡插入 Timeout 保護區段
app.use((req, res, next) => {
  res.setTimeout(120000); // 120秒 = 2分鐘
  next();
});

// 例如這裡是轉發 OpenAI 請求的程式
app.post("/v1/chat/completions", async (req, res) => {
  try {
    const response = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${process.env.OPENAI_API_KEY}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify(req.body)
    });

    const data = await response.text();
    res.send(data);
  } catch (err) {
    res.status(500).send({ error: err.message });
  }
});

app.listen(process.env.PORT || 8080, () => {
  console.log("✅ Proxy running on port", process.env.PORT || 8080);
});
