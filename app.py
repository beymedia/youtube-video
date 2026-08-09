```python
import os
import re
import glob
import uuid
import logging

from flask import Flask, render_template, request, send_file
import yt_dlp


# =========================================================
# Flask
# =========================================================

app = Flask(__name__)

DOWNLOAD_DIR = os.path.join(
    os.getcwd(),
    "downloads"
)

os.makedirs(
    DOWNLOAD_DIR,
    exist_ok=True
)


# =========================================================
# Logging
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger(__name__)


# =========================================================
# YouTube URL yoxlaması
# =========================================================

def valid_youtube_url(url):

    patterns = [
        r"^https?://(www\.)?youtube\.com/watch\?v=",
        r"^https?://youtube\.com/watch\?v=",
        r"^https?://youtu\.be/",
        r"^https?://(www\.)?youtube\.com/shorts/",
        r"^https?://(www\.)?youtube\.com/embed/",
        r"^https?://m\.youtube\.com/watch\?v="
    ]

    return any(
        re.match(pattern, url)
        for pattern in patterns
    )


# =========================================================
# Köhnə faylları təmizlə
# =========================================================

def clean_download_folder():

    for file in glob.glob(
        os.path.join(
            DOWNLOAD_DIR,
            "*"
        )
    ):

        try:

            if os.path.isfile(file):
                os.remove(file)

        except Exception as e:

            logger.warning(
                "Fayl silinmədi: %s",
                e
            )


# =========================================================
# Fayl adını təmizlə
# =========================================================

def safe_filename(filename):

    filename = re.sub(
        r'[\\/*?:"<>|]',
        "",
        filename
    )

    filename = filename.strip()

    if not filename:
        filename = "youtube-video"

    return filename[:100]


# =========================================================
# Ana səhifə
# =========================================================

@app.route("/")
def index():

    return render_template(
        "index.html"
    )


# =========================================================
# Download
# =========================================================

@app.route(
    "/download",
    methods=["POST"]
)
def download():

    url = request.form.get(
        "url",
        ""
    ).strip()


    # -----------------------------------------------------
    # URL boşdursa
    # -----------------------------------------------------

    if not url:

        return render_template(
            "index.html",
            error="YouTube linkini daxil edin."
        )


    # -----------------------------------------------------
    # YouTube URL yoxlaması
    # -----------------------------------------------------

    if not valid_youtube_url(url):

        return render_template(
            "index.html",
            error="Düzgün YouTube linki daxil edin."
        )


    # -----------------------------------------------------
    # Köhnə faylları sil
    # -----------------------------------------------------

    clean_download_folder()


    # -----------------------------------------------------
    # Unikal ID
    # -----------------------------------------------------

    job_id = uuid.uuid4().hex


    output_template = os.path.join(
        DOWNLOAD_DIR,
        f"{job_id}.%(ext)s"
    )


    # =====================================================
    # yt-dlp OPTIONS
    # =====================================================

    ydl_opts = {

        # Ən yaxşı MP4 video + M4A audio
        #
        # Əgər ayrıca video/audio mümkün deyilsə,
        # mövcud ən yaxşı MP4 seçilir.
        #
        "format": (
            "bestvideo[ext=mp4]+"
            "bestaudio[ext=m4a]/"
            "best[ext=mp4]/"
            "best"
        ),


        # Output
        "outtmpl": output_template,


        # FFmpeg ilə MP4 birləşdirmə
        "merge_output_format": "mp4",


        # Playlist yükləmə
        "noplaylist": True,


        # Fayl adını təhlükəsiz et
        "restrictfilenames": True,


        # Console
        "quiet": False,
        "no_warnings": False,


        # Progress
        "progress": True,


        # YouTube extractor
        #
        # Burada anti-bot bypass edilmir.
        # yt-dlp-nin normal extractor mexanizmi istifadə olunur.
        "extractor_args": {
            "youtube": {
                "player_client": [
                    "web"
                ]
            }
        }
    }


    # =====================================================
    # DOWNLOAD
    # =====================================================

    try:

        logger.info(
            "YouTube download başladı: %s",
            url
        )


        with yt_dlp.YoutubeDL(
            ydl_opts
        ) as ydl:


            # -------------------------------------------------
            # Video məlumatlarını əldə et
            # -------------------------------------------------

            info = ydl.extract_info(
                url,
                download=True
            )


            if not info:

                raise Exception(
                    "YouTube video məlumatı alınmadı."
                )


            title = info.get(
                "title",
                "youtube-video"
            )


            logger.info(
                "Video adı: %s",
                title
            )


        # =====================================================
        # Yaradılmış faylı tap
        # =====================================================

        files = glob.glob(
            os.path.join(
                DOWNLOAD_DIR,
                f"{job_id}.*"
            )
        )


        # .part fayllarını nəzərə alma
        files = [
            f
            for f in files
            if not f.endswith(".part")
        ]


        if not files:

            logger.error(
                "Download tamamlandı, amma fayl tapılmadı."
            )

            return render_template(
                "index.html",
                error=(
                    "Video endirildi, lakin fayl "
                    "serverdə tapılmadı."
                )
            )


        filepath = files[0]


        logger.info(
            "Fayl hazırdır: %s",
            filepath
        )


        # =====================================================
        # Download filename
        # =====================================================

        safe_title = safe_filename(
            title
        )


        download_name = (
            safe_title +
            ".mp4"
        )


        # =====================================================
        # Faylı istifadəçiyə göndər
        # =====================================================

        return send_file(

            filepath,

            as_attachment=True,

            download_name=download_name,

            mimetype="video/mp4"
        )


    # =====================================================
    # yt-dlp xətası
    # =====================================================

    except yt_dlp.utils.DownloadError as e:


        error_text = str(e)


        logger.error(
            "=" * 80
        )

        logger.error(
            "YT-DLP DOWNLOAD ERROR:"
        )

        logger.error(
            error_text
        )

        logger.error(
            "=" * 80
        )


        return render_template(

            "index.html",

            error=(
                "YouTube xətası: "
                + error_text[:700]
            )
        )


    # =====================================================
    # Digər xəta
    # =====================================================

    except Exception as e:


        logger.exception(
            "Ümumi server xətası:"
        )


        return render_template(

            "index.html",

            error=(
                "Server xətası: "
                + str(e)[:700]
            )
        )


# =========================================================
# Health Check
# =========================================================

@app.route("/health")
def health():

    return {

        "status": "ok",

        "service": "youtube-video",

        "yt_dlp_version": yt_dlp.version.__version__

    }


# =========================================================
# Run
# =========================================================

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
```
