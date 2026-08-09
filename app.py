from flask import Flask, render_template, request, send_file
from pytubefix import YouTube
from pytubefix.exceptions import PytubeFixError
import os
import uuid

app = Flask(__name__)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


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

    try:
        yt = YouTube(url)

        # Ən yüksək keyfiyyətli progressive stream
        stream = (
            yt.streams
            .filter(progressive=True, file_extension="mp4")
            .order_by("resolution")
            .desc()
            .first()
        )

        if not stream:
            return render_template(
                "index.html",
                error="Uyğun MP4 formatı tapılmadı."
            )

        filename = f"{uuid.uuid4().hex}.mp4"

        filepath = stream.download(
            output_path=DOWNLOAD_DIR,
            filename=filename
        )

        return send_file(
            filepath,
            as_attachment=True,
            download_name=f"{yt.title[:80]}.mp4",
            mimetype="video/mp4"
        )

    except Exception as e:
        return render_template(
            "index.html",
            error=f"Xəta baş verdi: {str(e)}"
        )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
