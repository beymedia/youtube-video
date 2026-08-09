import os
import re
import glob
import uuid
import shutil
from flask import Flask, render_template, request, send_file

import yt_dlp


app = Flask(__name__)

DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def clean_old_files():
    """
    Render-in müvəqqəti diskini doldurmamaq üçün
    köhnə faylları təmizləyir.
    """
    for file in glob.glob(os.path.join(DOWNLOAD_DIR, "*")):
        try:
            if os.path.isfile(file):
                os.remove(file)
        except Exception:
            pass


def valid_youtube_url(url):
    patterns = [
        r"^https?://(www\.)?youtube\.com/watch\?v=",
        r"^https?://youtu\.be/",
        r"^https?://(www\.)?youtube\.com/shorts/",
        r"^https?://(www\.)?youtube\.com/embed/"
    ]

    return any(re.match(pattern, url) for pattern in patterns)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/download", methods=["POST"])
def download():

    url = request.form.get("url", "").strip()

    if not url:
        return render_template(
            "index.html",
            error="YouTube linkini daxil edin."
        )

    if not valid_youtube_url(url):
        return render_template(
            "index.html",
            error="Düzgün YouTube linki daxil edin."
        )

    clean_old_files()

    job_id = uuid.uuid4().hex

    output_template = os.path.join(
        DOWNLOAD_DIR,
        f"{job_id}.%(ext)s"
    )

    ydl_opts = {
        # Video + audio, mümkün olan ən yaxşı MP4
        "format": (
            "bestvideo[ext=mp4]+bestaudio[ext=m4a]/"
            "best[ext=mp4]/best"
        ),

        "outtmpl": output_template,

        # FFmpeg ilə birləşdirmə
        "merge_output_format": "mp4",

        # Metadata
        "quiet": True,
        "no_warnings": True,

        # Playlist yox, yalnız verilmiş video
        "noplaylist": True,

        # Fayl adını təhlükəsiz saxla
        "restrictfilenames": True,

        # YouTube extractor üçün uyğun client seçimi
        "extractor_args": {
            "youtube": {
                "player_client": ["web", "android"]
            }
        }
    }

    try:

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(
                url,
                download=True
            )

            title = info.get(
                "title",
                "youtube-video"
            )

        files = glob.glob(
            os.path.join(
                DOWNLOAD_DIR,
                f"{job_id}.*"
            )
        )

        if not files:
            return render_template(
                "index.html",
                error="Video faylı yaradılmadı."
            )

        filepath = files[0]

        safe_title = re.sub(
            r'[\\/*?:"<>|]',
            "",
            title
        ).strip()

        if not safe_title:
            safe_title = "youtube-video"

        download_name = safe_title[:100] + ".mp4"

        response = send_file(
            filepath,
            as_attachment=True,
            download_name=download_name,
            mimetype="video/mp4"
        )

        return response

    except yt_dlp.utils.DownloadError as e:

        error_text = str(e)

        return render_template(
            "index.html",
            error=(
                "YouTube videonu əldə etmək mümkün olmadı. "
                "Video ictimai və endirməyə icazəli olmalıdır."
            )
        )

    except Exception as e:

        print("ERROR:", repr(e))

        return render_template(
            "index.html",
            error="Server tərəfində xəta baş verdi."
        )


@app.route("/health")
def health():
    return {
        "status": "ok",
        "service": "youtube-video"
    }


if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
