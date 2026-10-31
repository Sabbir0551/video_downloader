from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AnyStream API Gateway</title>
    <style>
        :root {
            --bg: #090d16;
            --card: #131c2e;
            --border: #1e293b;
            --primary: #3b82f6;
            --primary-hover: #2563eb;
            --text: #f8fafc;
            --muted: #94a3b8;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
        body { background: var(--bg); color: var(--text); min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 24px; }
        .card { background: var(--card); border: 1px solid var(--border); border-radius: 20px; padding: 40px; max-width: 540px; width: 100%; text-align: center; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5); }
        h1 { font-size: 2rem; font-weight: 800; background: linear-gradient(135deg, #60a5fa, #a855f7); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 12px; }
        p { color: var(--muted); font-size: 1rem; line-height: 1.6; margin-bottom: 28px; }
        .actions { display: flex; flex-direction: column; gap: 12px; }
        .btn { display: inline-flex; align-items: center; justify-content: center; padding: 14px 24px; border-radius: 12px; font-size: 1rem; font-weight: 600; text-decoration: none; transition: all 0.2s; }
        .btn-primary { background: var(--primary); color: #fff; }
        .btn-primary:hover { background: var(--primary-hover); }
        .btn-outline { background: transparent; border: 1px solid var(--border); color: var(--text); }
        .btn-outline:hover { background: #1e293b; border-color: var(--muted); }
        .footer-note { font-size: 0.8rem; color: #64748b; margin-top: 24px; }
    </style>
</head>
<body>
    <div class="card">
        <h1>AnyStream Video Platform</h1>
        <p>You have connected to the AnyStream FastAPI Backend Gateway. The modern user interface is powered by our Next.js web application.</p>
        <div class="actions">
            <a href="http://localhost:3000" class="btn btn-primary" id="open-web-app">Open Web Application</a>
            <a href="/docs" class="btn btn-outline" id="open-api-docs">Interactive API Documentation (Swagger)</a>
        </div>
        <div class="footer-note">
            Production API Gateway &bull; Fully compliant with OpenAPI 3.1
        </div>
    </div>
</body>
</html>
"""


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_web_gateway():
    """Serves the root gateway landing page directing users to the Next.js app or API docs."""
    return HTMLResponse(content=HTML_PAGE)
