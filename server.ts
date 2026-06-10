import express from "express";
import path from "path";
import { createServer as createViteServer } from "vite";
import dotenv from "dotenv";
import { GoogleGenAI } from "@google/genai";

dotenv.config();

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(express.json({ limit: '10mb' }));

  // API Route - Tylko Twoja własna sieć ConvNext
  app.post("/api/classify", async (req, res) => {
    const { image } = req.body;
    if (!image) return res.status(400).json({ error: "Nie przesłano zdjęcia" });

    try {
      const modelServerUrl = process.env.MODEL_SERVER_URL || "http://localhost:8000/predict";
      const fastApiResponse = await fetch(modelServerUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image })
      });

      if (fastApiResponse.ok) {
        const localResult = await fastApiResponse.json();
        
        // Zwracamy czyste dane z Twojego modelu
        return res.json({
          breed: localResult.breed,
          confidence: localResult.confidence,
          description: "Opis wyłączony (używasz tylko własnego modelu klasyfikacji).",
          characteristics: ["Własny model", "ConvNext Small"]
        });
      } else {
        const errorText = await fastApiResponse.text();
        res.status(502).json({ 
          error: "Błąd modelu lokalnego", 
          detail: "Twój serwer FastAPI zwrócił błąd. Upewnij się, że model .pth jest poprawnie wczytany." 
        });
      }
    } catch (e) {
      console.error("FastAPI unreachable:", e);
      res.status(503).json({ 
        error: "Model Offline", 
        detail: "Nie można połączyć się z serwerem FastAPI na porcie 8000. Uruchom 'python backend/main.py'." 
      });
    }
  });

  // API Route - Generowanie opisu rasy psa za pomocą Gemini API
  app.post("/api/description", async (req, res) => {
    const { breed, lang } = req.body;
    if (!breed) return res.status(400).json({ error: "Nie podano rasy psa" });

    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
      return res.status(400).json({
        error: "Brak klucza API Gemini",
        detail: "Skonfiguruj klucz GEMINI_API_KEY w panelu Settings > Secrets."
      });
    }

    try {
      const ai = new GoogleGenAI({
        apiKey: apiKey,
        httpOptions: {
          headers: {
            'User-Agent': 'aistudio-build',
          }
        }
      });

      const isEnglish = lang === 'en';
      const promptText = isEnglish
        ? `Write a few interesting, engaging sentences about the dog breed ${breed} in English. List its primary characteristics or fun facts. Use simple markdown formatting (like bold text or bullet points) to make it highly readable.`
        : `Napisz parę ciekawych, angażujących zdań o psie rasy ${breed} po polsku. Wymień jego główne cechy charakteru lub ciekawostki. Użyj prostego formatowania markdown (np. pogrubienia lub listy punktowej), aby tekst był bardzo czytelny.`;

      const response = await ai.models.generateContent({
        model: "gemini-3.1-flash-lite",
        contents: promptText,
      });

      const text = response.text;
      return res.json({ description: text });
    } catch (e: any) {
      console.error("Gemini API error:", e);
      return res.status(500).json({
        error: "Błąd podczas generowania opisu rasy",
        detail: e.message || String(e)
      });
    }
  });

  // Vite middleware
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Frontend & Proxy Server running on http://localhost:${PORT}`);
  });
}

startServer();
