from fastapi import FastAPI, Form
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
import yt_dlp
import os

app = FastAPI()
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ---------------- UI ----------------
@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html>
    <head>
        <title>Any Link Downloader</title>
        <script>
            async function previewVideo() {
                const url = document.getElementById("url").value;
                if (!url) { alert("Paste link first"); return; }

                document.getElementById("preview").innerHTML = "Loading preview...";
                document.getElementById("downloadSection").style.display = "none";

                const res = await fetch("/preview", {
                    method: "POST",
                    headers: {"Content-Type": "application/x-www-form-urlencoded"},
                    body: "url=" + encodeURIComponent(url)
                });

                const data = await res.json();

                if (data.error) {
                    document.getElementById("preview").innerHTML = data.error;
                } else {
                    document.getElementById("preview").innerHTML = `
                        <h3>${data.title}</h3>
                        <img src="${data.thumbnail}" width="300"><br>
                        <p>Duration: ${data.duration} sec</p>
                        <p>Platform: ${data.extractor}</p>
                    `;
                    document.getElementById("hiddenUrl").value = url;
                    document.getElementById("downloadSection").style.display = "block";
                }
            }

            function toggleOptions(type) {
                document.getElementById("videoOptions").style.display =
                    type === "mp4" ? "block" : "none";
                document.getElementById("audioOptions").style.display =
                    type === "mp3" ? "block" : "none";
            }
        </script>
    </head>

    <body style="font-family: Arial; text-align: center; margin-top: 50px;">
        <h2>Any Website Video Downloader</h2>

        <input type="text" id="url" placeholder="Paste ANY video link"
               style="width: 380px; height: 32px;" required>
        <br><br>

        <button onclick="previewVideo()">Preview</button>

        <form action="/download" method="post">
            <input type="hidden" name="url" id="hiddenUrl">

            <div id="downloadSection" style="display:none;">
                <br>

                <b>Select Type</b><br>
                <input type="radio" name="type" value="mp4" checked onclick="toggleOptions('mp4')"> MP4
                <input type="radio" name="type" value="mp3" onclick="toggleOptions('mp3')"> MP3

                <br><br>

                <div id="videoOptions">
                    <label>Video Quality</label><br>
                    <select name="video_quality">
                        <option value="2160">2160p (4K)</option>
                        <option value="1440">1440p</option>
                        <option value="1080">1080p</option>
                        <option value="720">720p</option>
                        <option value="480">480p</option>
                    </select>
                </div>

                <div id="audioOptions" style="display:none;">
                    <label>Audio Quality</label><br>
                    <select name="audio_quality">
                        <option value="320">320 kbps</option>
                        <option value="192">192 kbps</option>
                        <option value="128">128 kbps</option>
                    </select>
                </div>

                <br>
                <button type="submit">Download</button>
            </div>
        </form>

        <div id="preview" style="margin-top:20px;"></div>
    </body>
    </html>
    """

# ---------------- PREVIEW ----------------
@app.post("/preview")
async def preview(url: str = Form(...)):
    try:
        ydl_opts = {
            "quiet": True,
            "noplaylist": True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        return {
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration"),
            "extractor": info.get("extractor_key")
        }
    except Exception as e:
        return {"error": str(e)}

# ---------------- DOWNLOAD ----------------
@app.post("/download")
async def download(
    url: str = Form(...),
    type: str = Form(...),
    video_quality: str = Form(None),
    audio_quality: str = Form(None)
):
    try:
        # -------- MP4 --------
        if type == "mp4":
            height = int(video_quality)

            ydl_opts = {
                "format": f"bestvideo[height<={height}]+bestaudio/best/best",
                "merge_output_format": "mp4",
                "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
                "noplaylist": True
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url)
                filename = ydl.prepare_filename(info)

            media_type = "video/mp4"

        # -------- MP3 --------
        else:
            ydl_opts = {
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": audio_quality
                }],
                "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
                "noplaylist": True
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url)
                temp = ydl.prepare_filename(info)

            filename = os.path.splitext(temp)[0] + ".mp3"
            media_type = "audio/mpeg"

        return FileResponse(
            filename,
            filename=os.path.basename(filename),
            media_type=media_type
        )

    except Exception as e:
        return JSONResponse({"error": str(e)})
