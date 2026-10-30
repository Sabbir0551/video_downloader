from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

HTML_PAGE = """<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AnyStream - ভিডিও ডাউনলোডার</title>
    <style>
        :root {
            --bg: #0f172a;
            --card: #1e293b;
            --border: #334155;
            --primary: #3b82f6;
            --primary-hover: #2563eb;
            --success: #10b981;
            --text: #f8fafc;
            --muted: #94a3b8;
            --danger: #ef4444;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
        body { background: var(--bg); color: var(--text); min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: flex-start; padding: 40px 16px; }
        .container { width: 100%; max-width: 720px; }
        .header { text-align: center; margin-bottom: 32px; }
        .header h1 { font-size: 2.2rem; font-weight: 800; background: linear-gradient(135deg, #60a5fa, #a855f7); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .header p { color: var(--muted); margin-top: 8px; font-size: 1rem; }
        .card { background: var(--card); border: 1px solid var(--border); border-radius: 16px; padding: 24px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3); margin-bottom: 24px; }
        .input-group { display: flex; gap: 12px; }
        .input-group input { flex: 1; background: #0f172a; border: 1px solid var(--border); border-radius: 10px; padding: 14px 18px; color: var(--text); font-size: 1rem; outline: none; transition: border-color 0.2s; }
        .input-group input:focus { border-color: var(--primary); }
        .btn { background: var(--primary); color: #fff; border: none; border-radius: 10px; padding: 14px 24px; font-size: 1rem; font-weight: 600; cursor: pointer; transition: background 0.2s; display: inline-flex; align-items: center; justify-content: center; gap: 8px; text-decoration: none; }
        .btn:hover { background: var(--primary-hover); }
        .btn:disabled { opacity: 0.6; cursor: not-allowed; }
        .btn-success { background: var(--success); }
        .btn-success:hover { background: #059669; }
        .btn-danger { background: var(--danger); padding: 8px 16px; font-size: 0.85rem; }
        .btn-danger:hover { background: #dc2626; }
        .error-box { background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 10px; padding: 14px 18px; color: #fca5a5; margin-top: 16px; display: none; }
        .video-card { display: none; margin-top: 24px; border-top: 1px solid var(--border); padding-top: 24px; }
        .video-meta { display: flex; gap: 18px; align-items: flex-start; margin-bottom: 20px; }
        .video-thumb { width: 140px; aspect-ratio: 16/9; object-fit: cover; border-radius: 8px; background: #000; flex-shrink: 0; }
        .video-details h3 { font-size: 1.1rem; line-height: 1.4; margin-bottom: 6px; }
        .video-details p { color: var(--muted); font-size: 0.9rem; }
        .formats-title { font-size: 0.95rem; font-weight: 600; margin-bottom: 12px; color: var(--muted); }
        .format-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 10px; }
        .format-btn { background: #0f172a; border: 1px solid var(--border); border-radius: 8px; padding: 10px; text-align: center; color: var(--text); cursor: pointer; transition: all 0.2s; font-size: 0.9rem; }
        .format-btn:hover { border-color: var(--primary); background: #1e3a8a; }
        .format-btn .label { font-weight: 700; display: block; font-size: 1rem; color: #60a5fa; }
        .format-btn .ext { font-size: 0.75rem; color: var(--muted); margin-top: 2px; }
        .progress-box { display: none; margin-top: 24px; background: #0f172a; border-radius: 12px; padding: 20px; border: 1px solid var(--border); }
        .progress-bar-bg { width: 100%; height: 10px; background: #334155; border-radius: 5px; overflow: hidden; margin: 12px 0; }
        .progress-bar-fill { height: 100%; width: 0%; background: linear-gradient(90deg, #3b82f6, #10b981); transition: width 0.3s; }
        .progress-meta { display: flex; justify-content: space-between; font-size: 0.85rem; color: var(--muted); }
        .download-action { display: none; margin-top: 20px; text-align: center; }
        .footer { text-align: center; margin-top: 32px; font-size: 0.85rem; color: var(--muted); }
        .footer a { color: var(--primary); text-decoration: none; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AnyStream Video Downloader</h1>
            <p>যেকোনো পাবলিক ভিডিওর লিংক দিন এবং এক ক্লিকে ডাউনলোড করুন</p>
        </div>

        <div class="card">
            <div class="input-group">
                <input type="text" id="urlInput" placeholder="ভিডিও লিংক পেস্ট করুন (যেমন: https://www.youtube.com/watch?v=...)" />
                <button class="btn" id="inspectBtn" onclick="fetchMediaInfo()">
                    <span id="btnText">সার্চ করুন</span>
                </button>
            </div>

            <div class="error-box" id="errorBox"></div>

            <div class="video-card" id="videoCard">
                <div class="video-meta">
                    <img id="videoThumb" class="video-thumb" src="" alt="Thumbnail" />
                    <div class="video-details">
                        <h3 id="videoTitle"></h3>
                        <p id="videoAuthor"></p>
                    </div>
                </div>

                <div class="formats-title">ডাউনলোড কোয়ালিটি নির্বাচন করুন:</div>
                <div class="format-grid" id="formatGrid"></div>
            </div>

            <div class="progress-box" id="progressBox">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span id="statusLabel" style="font-weight: 600; color: #60a5fa;">ডাউনলোড হচ্ছে...</span>
                    <button class="btn btn-danger" id="cancelBtn" onclick="cancelCurrentJob()">বাতিল করুন</button>
                </div>
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill" id="progressBar"></div>
                </div>
                <div class="progress-meta">
                    <span id="progressText">0%</span>
                    <span id="speedText">স্পিড: --</span>
                    <span id="etaText">বাকি সময়: --</span>
                </div>
                <div class="download-action" id="downloadAction">
                    <a id="downloadLink" class="btn btn-success" style="width: 100%; font-size: 1.1rem; padding: 16px;" href="#" download>
                        📥 ভিডিও ফাইল সেভ করুন (.mp4)
                    </a>
                </div>
            </div>
        </div>

        <div class="footer">
            AnyStream Platform API v1.0 • <a href="/docs" target="_blank">Swagger API Docs</a>
        </div>
    </div>

    <script>
        let currentJobId = null;
        let pollTimer = null;
        let activeVideoUrl = '';

        function showError(msg) {
            const box = document.getElementById('errorBox');
            box.innerText = msg;
            box.style.display = 'block';
        }

        function clearError() {
            const box = document.getElementById('errorBox');
            box.style.display = 'none';
            box.innerText = '';
        }

        async function fetchMediaInfo() {
            const url = document.getElementById('urlInput').value.trim();
            if (!url) {
                showError('অনুগ্রহ করে একটি বৈধ ভিডিও লিংক দিন।');
                return;
            }

            clearError();
            document.getElementById('videoCard').style.display = 'none';
            document.getElementById('progressBox').style.display = 'none';
            document.getElementById('downloadAction').style.display = 'none';
            
            const btn = document.getElementById('inspectBtn');
            const btnText = document.getElementById('btnText');
            btn.disabled = true;
            btnText.innerText = 'লোড হচ্ছে...';

            try {
                const res = await fetch('/api/v1/info', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: url })
                });

                const data = await res.json();
                if (!res.ok) {
                    throw new Error(data.message || 'ভিডিওর তথ্য আনা সম্ভব হয়নি।');
                }

                activeVideoUrl = url;
                displayVideoInfo(data);
            } catch (err) {
                showError(err.message);
            } finally {
                btn.disabled = false;
                btnText.innerText = 'সার্চ করুন';
            }
        }

        function displayVideoInfo(info) {
            clearError();
            document.getElementById('videoThumb').src = info.thumbnail_url || '';
            document.getElementById('videoTitle').innerText = info.title;
            const dur = info.duration ? Math.floor(info.duration / 60) + ' মিনিট ' + (info.duration % 60) + ' সেকেন্ড' : '';
            document.getElementById('videoAuthor').innerText = (info.uploader ? info.uploader + ' • ' : '') + dur;

            const grid = document.getElementById('formatGrid');
            grid.innerHTML = '';

            // Default 'Best Quality' option
            const bestBtn = document.createElement('div');
            bestBtn.className = 'format-btn';
            bestBtn.innerHTML = '<span class="label">Best Video</span><span class="ext">HD MP4 (অটো)</span>';
            bestBtn.onclick = () => startDownload(activeVideoUrl, 'best', false, 'Best HD');
            grid.appendChild(bestBtn);

            // Filter up to 5 formats
            if (info.formats && info.formats.length > 0) {
                info.formats.slice(0, 5).forEach(fmt => {
                    const btn = document.createElement('div');
                    btn.className = 'format-btn';
                    const lbl = fmt.resolution || fmt.ext.toUpperCase();
                    btn.innerHTML = `<span class="label">${lbl}</span><span class="ext">${fmt.ext.toUpperCase()}</span>`;
                    btn.onclick = () => startDownload(activeVideoUrl, fmt.format_id, fmt.is_audio_only, lbl);
                    grid.appendChild(btn);
                });
            }

            document.getElementById('videoCard').style.display = 'block';
        }

        async function startDownload(url, formatId, isAudio, label) {
            clearError();
            document.getElementById('videoCard').style.display = 'none';
            document.getElementById('progressBox').style.display = 'block';
            document.getElementById('downloadAction').style.display = 'none';
            document.getElementById('progressBar').style.width = '0%';
            document.getElementById('progressText').innerText = '0%';
            document.getElementById('statusLabel').innerText = 'রিকোয়েস্ট গ্রহণ করা হচ্ছে...';

            try {
                const res = await fetch('/api/v1/downloads', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        url: url,
                        format_id: formatId,
                        audio_only: isAudio,
                        quality_label: label
                    })
                });

                const data = await res.json();
                if (!res.ok) {
                    throw new Error(data.message || 'ডাউনলোড শুরু করা সম্ভব হয়নি।');
                }

                currentJobId = data.job_id;
                document.getElementById('statusLabel').innerText = 'ডাউনলোড শুরু হচ্ছে (ওয়ার্কার সংযুক্ত)...';
                startPolling(currentJobId);
            } catch (err) {
                showError(err.message);
                document.getElementById('progressBox').style.display = 'none';
                document.getElementById('videoCard').style.display = 'block';
            }
        }

        function startPolling(jobId) {
            if (pollTimer) clearInterval(pollTimer);
            let consecutiveErrors = 0;
            pollTimer = setInterval(async () => {
                try {
                    const res = await fetch(`/api/v1/downloads/${jobId}`);
                    if (!res.ok) {
                        consecutiveErrors++;
                        if (consecutiveErrors > 15) {
                            clearInterval(pollTimer);
                            showError('সার্ভারের সাথে সংযোগ বিচ্ছিন্ন হয়েছে। অনুগ্রহ করে আবার চেষ্টা করুন।');
                            document.getElementById('progressBox').style.display = 'none';
                            document.getElementById('videoCard').style.display = 'block';
                        }
                        return;
                    }
                    consecutiveErrors = 0;

                    const job = await res.json();
                    updateProgressUI(job);

                    if (job.status === 'COMPLETED') {
                        clearInterval(pollTimer);
                        onDownloadComplete(job);
                    } else if (job.status === 'FAILED' || job.status === 'CANCELLED') {
                        clearInterval(pollTimer);
                        showError(job.error_message || 'ডাউনলোড ব্যর্থ হয়েছে।');
                        document.getElementById('progressBox').style.display = 'none';
                        document.getElementById('videoCard').style.display = 'block';
                    }
                } catch (e) {
                    consecutiveErrors++;
                    if (consecutiveErrors > 15) {
                        clearInterval(pollTimer);
                        showError('সার্ভারের সাথে সংযোগ পাওয়া যাচ্ছে না।');
                    }
                }
            }, 1000);
        }

        function updateProgressUI(job) {
            const pct = Math.round(job.progress || 0);
            document.getElementById('progressBar').style.width = pct + '%';
            document.getElementById('progressText').innerText = pct + '%';
            document.getElementById('statusLabel').innerText = job.status === 'PROCESSING' ? 'ভিডিও ডাউনলোড ও মার্জ হচ্ছে...' : job.status;

            if (job.speed) {
                document.getElementById('speedText').innerText = 'স্পিড: ' + job.speed;
            }
            if (job.eta) {
                document.getElementById('etaText').innerText = 'বাকি সময়: ' + job.eta + 's';
            }
        }

        function onDownloadComplete(job) {
            document.getElementById('progressBar').style.width = '100%';
            document.getElementById('progressText').innerText = '100%';
            document.getElementById('statusLabel').innerText = 'ডাউনলোড প্রস্তুত! 🎉';
            document.getElementById('cancelBtn').style.display = 'none';

            const dlLink = document.getElementById('downloadLink');
            dlLink.href = job.download_url;
            document.getElementById('downloadAction').style.display = 'block';
        }

        async function cancelCurrentJob() {
            if (!currentJobId) return;
            if (pollTimer) clearInterval(pollTimer);

            try {
                await fetch(`/api/v1/downloads/${currentJobId}`, { method: 'DELETE' });
                showError('ডাউনলোড বাতিল করা হয়েছে।');
            } catch (e) {}

            document.getElementById('progressBox').style.display = 'none';
            document.getElementById('videoCard').style.display = 'block';
        }
    </script>
</body>
</html>
"""

@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def home_page():
    """Serves an intuitive, single-page web UI for instant video downloads."""
    return HTMLResponse(content=HTML_PAGE)
