import type { Express, Request, Response, NextFunction } from "express";
import { type Server } from "http";
import multer from "multer";

const FASTAPI_BASE = "http://localhost:8000";
const upload = multer({ storage: multer.memoryStorage(), limits: { fileSize: 10 * 1024 * 1024 } });

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {
  // PDF upload proxy — must be registered before the generic JSON proxy
  app.post("/api/parse-resume-pdf", upload.single("file"), async (req: Request, res: Response) => {
    try {
      if (!req.file) {
        res.status(400).json({ error: "No file uploaded" });
        return;
      }
      const formData = new FormData();
      const blob = new Blob([req.file.buffer], { type: req.file.mimetype });
      formData.append("file", blob, req.file.originalname);

      const response = await fetch(`${FASTAPI_BASE}/api/parse-resume-pdf`, {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      res.status(response.status).json(data);
    } catch (error: any) {
      console.error("PDF proxy error:", error.message);
      res.status(502).json({ error: "Backend unavailable", detail: error.message });
    }
  });

  // Proxy all other /api/* requests to the FastAPI backend on port 8000
  app.use("/api", async (req: Request, res: Response, next: NextFunction) => {
    try {
      const url = `${FASTAPI_BASE}/api${req.url}`;
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      
      const fetchOptions: RequestInit = {
        method: req.method,
        headers,
      };
      
      if (req.method !== "GET" && req.method !== "HEAD") {
        fetchOptions.body = JSON.stringify(req.body);
      }
      
      const response = await fetch(url, fetchOptions);
      const data = await response.json();
      res.status(response.status).json(data);
    } catch (error: any) {
      console.error("Proxy error:", error.message);
      res.status(502).json({ error: "Backend unavailable", detail: error.message });
    }
  });

  return httpServer;
}
