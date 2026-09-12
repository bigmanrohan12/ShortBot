from flask import Flask, request, jsonify, send_from_directory, send_file
from agent import find_shorts
import os
import subprocess
import uuid
import glob
import shutil


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_DIR = os.path.join(BASE_DIR, "ui")
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

app = Flask(__name__)


FFMPEG_PATH = shutil.which("ffmpeg")


if FFMPEG_PATH:
    print()
    print("FFmpeg found:")
    print(FFMPEG_PATH)
    print()
else:
    print()
    print("WARNING: FFmpeg was not found in PATH.")
    print("Run: ffmpeg -version")
    print()


# ============================================================
# SEARCH
# ============================================================

@app.route("/search", methods=["POST"])
def search():

    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "success": False,
            "error": "Invalid request."
        }), 400

    user_request = str(
        data.get("request", "")
    ).strip()

    quantity = data.get("quantity")

    if not user_request:
        return jsonify({
            "success": False,
            "error": "Please enter what Shorts you are looking for."
        }), 400

    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "error": "Quantity must be a number."
        }), 400

    if quantity < 1:
        return jsonify({
            "success": False,
            "error": "Quantity must be greater than 0."
        }), 400

    try:

        results = find_shorts(
            user_request,
            quantity
        )

        return jsonify({
            "success": True,
            "results": results
        })

    except Exception as e:

        print()
        print("=" * 60)
        print("SEARCH ERROR")
        print("=" * 60)
        print(e)
        print()

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# CREATE WATERMARKED VIDEO
# ============================================================

def apply_watermark(
    input_file,
    output_file,
    watermark
):

    if not watermark:
        return False

    watermark_file = os.path.join(
        DOWNLOAD_DIR,
        f"watermark_{uuid.uuid4().hex[:8]}.txt"
    )

    try:

        with open(
            watermark_file,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(watermark)

        watermark_path = watermark_file.replace(
            "\\",
            "/"
        )

        if (
            len(watermark_path) >= 2
            and watermark_path[1] == ":"
        ):

            watermark_path = (
                watermark_path[0]
                + "\\:"
                + watermark_path[2:]
            )

        filter_complex = (
            "drawtext="
            "textfile='"
            + watermark_path
            + "':"
            "fontfile='C\\:/Windows/Fonts/arial.ttf':"
            "fontsize=48:"
            "fontcolor=white:"
            "box=1:"
            "boxcolor=black@0.55:"
            "boxborderw=12:"
            "x=w-tw-30:"
            "y=h-th-30"
        )

        command = [

            FFMPEG_PATH,

            "-y",

            "-i",
            input_file,

            "-vf",
            filter_complex,

            "-c:v",
            "libx264",

            "-preset",
            "veryfast",

            "-crf",
            "23",

            "-c:a",
            "aac",

            "-b:a",
            "128k",

            "-movflags",
            "+faststart",

            output_file
        ]

        print()
        print("Applying watermark:")
        print(watermark)
        print()

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=1200
        )

        print(result.stdout)

        if result.stderr:
            print(result.stderr)

        if result.returncode != 0:

            raise RuntimeError(
                "FFmpeg could not apply the watermark.\n"
                + result.stderr[-3000:]
            )

        if not os.path.exists(output_file):

            raise RuntimeError(
                "Watermarked video was not created."
            )

        return True

    finally:

        if os.path.exists(watermark_file):

            try:
                os.remove(watermark_file)
            except OSError:
                pass


# ============================================================
# DOWNLOAD ONE SHORT
# ============================================================

@app.route("/download", methods=["POST"])
def download():

    data = request.get_json(silent=True)

    if not data:

        return jsonify({
            "success": False,
            "error": "Invalid request."
        }), 400

    video_url = str(
        data.get("url", "")
    ).strip()

    watermark = str(
        data.get("watermark", "")
    ).strip()

    if not video_url:

        return jsonify({
            "success": False,
            "error": "No video URL provided."
        }), 400

    if len(watermark) > 50:

        return jsonify({
            "success": False,
            "error": "Watermark is too long."
        }), 400

    print()
    print("=" * 60)
    print("DOWNLOADING SHORT")
    print("=" * 60)
    print("URL:", video_url)

    if watermark:
        print("Watermark:", watermark)
    else:
        print("Watermark: NONE")

    print()

    if not FFMPEG_PATH:

        return jsonify({
            "success": False,
            "error": "FFmpeg was not found."
        }), 500

    file_id = uuid.uuid4().hex[:8]

    output_template = os.path.join(
        DOWNLOAD_DIR,
        f"short_{file_id}.%(ext)s"
    )

    command = [

        "python",
        "-m",
        "yt_dlp",

        "-f",
        "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]",

        "--merge-output-format",
        "mp4",

        "--ffmpeg-location",
        FFMPEG_PATH,

        "--no-playlist",

        "-o",
        output_template,

        video_url
    ]

    print("Running yt-dlp...")
    print()

    try:

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=600
        )

        print(result.stdout)

        if result.stderr:
            print(result.stderr)

        if result.returncode != 0:

            return jsonify({
                "success": False,
                "error": "Download failed.",
                "details": result.stderr[-2000:]
            }), 500

        original_file = os.path.join(
            DOWNLOAD_DIR,
            f"short_{file_id}.mp4"
        )

        print()
        print("Looking for final MP4:")
        print(original_file)
        print()

        if not os.path.exists(original_file):

            possible_files = glob.glob(
                os.path.join(
                    DOWNLOAD_DIR,
                    f"short_{file_id}.*"
                )
            )

            print("Files produced:")

            for file in possible_files:
                print(file)

            return jsonify({
                "success": False,
                "error": "Download completed, but the final MP4 was not found.",
                "files": possible_files
            }), 500

        # ----------------------------------------------------
        # NO WATERMARK
        # ----------------------------------------------------

        if not watermark:

            final_file = original_file

        # ----------------------------------------------------
        # WATERMARK ENABLED
        # ----------------------------------------------------

        else:

            watermarked_file = os.path.join(
                DOWNLOAD_DIR,
                f"short_{file_id}_watermarked.mp4"
            )

            apply_watermark(
                original_file,
                watermarked_file,
                watermark
            )

            # Replace the original downloaded file with
            # the watermarked version so the file tracked
            # by the frontend is the final version.

            os.remove(original_file)

            os.replace(
                watermarked_file,
                original_file
            )

            final_file = original_file

        print()
        print("=" * 60)
        print("DOWNLOAD SUCCESSFUL")
        print("=" * 60)
        print()

        print("Final MP4:")
        print(final_file)
        print()

        return send_file(
            final_file,
            as_attachment=True,
            download_name=f"short_{file_id}.mp4",
            mimetype="video/mp4"
        )

    except subprocess.TimeoutExpired:

        return jsonify({
            "success": False,
            "error": "Download timed out."
        }), 500

    except Exception as e:

        print()
        print("=" * 60)
        print("DOWNLOAD ERROR")
        print("=" * 60)
        print(e)
        print()

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# LIST DOWNLOADED SHORTS
# ============================================================

@app.route("/downloads", methods=["GET"])
def list_downloads():

    files = []

    try:

        for filename in os.listdir(
            DOWNLOAD_DIR
        ):

            if not filename.lower().endswith(".mp4"):
                continue

            if not filename.lower().startswith("short_"):
                continue

            files.append(filename)

        files.sort()

        return jsonify({
            "success": True,
            "files": files
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# COMPILE SELECTED SHORTS
# ============================================================

@app.route("/compile", methods=["POST"])
def compile_shorts():

    print()
    print("=" * 60)
    print("COMPILING SHORTS")
    print("=" * 60)
    print()

    if not FFMPEG_PATH:

        return jsonify({
            "success": False,
            "error": "FFmpeg was not found."
        }), 500

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({
            "success": False,
            "error": "Invalid request."
        }), 400

    files = data.get(
        "files",
        []
    )

    watermark = str(
        data.get(
            "watermark",
            ""
        )
    ).strip()

    if not isinstance(
        files,
        list
    ):

        return jsonify({
            "success": False,
            "error": "Files must be a list."
        }), 400

    if len(watermark) > 50:

        return jsonify({
            "success": False,
            "error": "Watermark is too long."
        }), 400

    valid_files = []

    for filename in files:

        filename = str(
            filename
        ).strip()

        if not filename:
            continue

        safe_name = os.path.basename(
            filename
        )

        if safe_name != filename:
            continue

        if not safe_name.lower().endswith(
            ".mp4"
        ):
            continue

        if not safe_name.lower().startswith(
            "short_"
        ):
            continue

        full_path = os.path.join(
            DOWNLOAD_DIR,
            safe_name
        )

        if os.path.isfile(
            full_path
        ):

            valid_files.append(
                full_path
            )

    if len(valid_files) < 2:

        return jsonify({
            "success": False,
            "error": "Download at least 2 Shorts before compiling."
        }), 400

    print("Files to compile:")

    for file in valid_files:
        print(file)

    print()

    if watermark:
        print("Watermark:", watermark)
    else:
        print("Watermark: NONE")

    print()

    compile_id = uuid.uuid4().hex[:8]

    concat_file = os.path.join(
        DOWNLOAD_DIR,
        f"concat_{compile_id}.txt"
    )

    watermark_file = os.path.join(
        DOWNLOAD_DIR,
        f"watermark_{compile_id}.txt"
    )

    output_file = os.path.join(
        DOWNLOAD_DIR,
        f"compilation_{compile_id}.mp4"
    )

    try:

        # ----------------------------------------------------
        # CREATE CONCAT FILE
        # ----------------------------------------------------

        with open(
            concat_file,
            "w",
            encoding="utf-8"
        ) as f:

            for file in valid_files:

                ffmpeg_path = file.replace(
                    "\\",
                    "/"
                )

                f.write(
                    "file '" +
                    ffmpeg_path +
                    "'\n"
                )

        # ----------------------------------------------------
        # NO WATERMARK
        # ----------------------------------------------------

        if not watermark:

            command = [

                FFMPEG_PATH,

                "-y",

                "-f",
                "concat",

                "-safe",
                "0",

                "-i",
                concat_file,

                "-c",
                "copy",

                "-movflags",
                "+faststart",

                output_file
            ]

        # ----------------------------------------------------
        # WATERMARK ENABLED
        # ----------------------------------------------------

        else:

            with open(
                watermark_file,
                "w",
                encoding="utf-8"
            ) as f:

                f.write(watermark)

            watermark_path = watermark_file.replace(
                "\\",
                "/"
            )

            if (
                len(watermark_path) >= 2
                and watermark_path[1] == ":"
            ):

                watermark_path = (
                    watermark_path[0]
                    + "\\:"
                    + watermark_path[2:]
                )

            filter_complex = (
                "drawtext="
                "textfile='"
                + watermark_path
                + "':"
                "fontfile='C\\:/Windows/Fonts/arial.ttf':"
                "fontsize=48:"
                "fontcolor=white:"
                "box=1:"
                "boxcolor=black@0.55:"
                "boxborderw=12:"
                "x=w-tw-30:"
                "y=h-th-30"
            )

            command = [

                FFMPEG_PATH,

                "-y",

                "-f",
                "concat",

                "-safe",
                "0",

                "-i",
                concat_file,

                "-vf",
                filter_complex,

                "-c:v",
                "libx264",

                "-preset",
                "veryfast",

                "-crf",
                "23",

                "-c:a",
                "aac",

                "-b:a",
                "128k",

                "-movflags",
                "+faststart",

                output_file
            ]

        # ----------------------------------------------------
        # RUN FFMPEG
        # ----------------------------------------------------

        print("Running FFmpeg...")
        print()

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=1200
        )

        print(result.stdout)

        if result.stderr:
            print(result.stderr)

        if result.returncode != 0:

            return jsonify({
                "success": False,
                "error": "FFmpeg could not compile the Shorts.",
                "details": result.stderr[-3000:]
            }), 500

        if not os.path.exists(
            output_file
        ):

            return jsonify({
                "success": False,
                "error": "Compilation finished, but the output MP4 was not found."
            }), 500

        print()
        print("=" * 60)

        if watermark:
            print("COMPILATION + WATERMARK SUCCESSFUL")
        else:
            print("COMPILATION SUCCESSFUL")

        print("=" * 60)
        print()

        print("Final compilation:")
        print(output_file)
        print()

        return send_file(
            output_file,
            as_attachment=True,
            download_name="shortbot_compilation.mp4",
            mimetype="video/mp4"
        )

    except subprocess.TimeoutExpired:

        return jsonify({
            "success": False,
            "error": "Compilation timed out."
        }), 500

    except Exception as e:

        print()
        print("=" * 60)
        print("COMPILATION ERROR")
        print("=" * 60)
        print(e)
        print()

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

    finally:

        if os.path.exists(
            concat_file
        ):

            try:
                os.remove(
                    concat_file
                )
            except OSError:
                pass

        if os.path.exists(
            watermark_file
        ):

            try:
                os.remove(
                    watermark_file
                )
            except OSError:
                pass


# ============================================================
# WEBSITE
# ============================================================

@app.route("/")
def index():

    return send_from_directory(
        UI_DIR,
        "index.html"
    )


@app.route("/<path:path>")
def static_files(path):

    return send_from_directory(
        UI_DIR,
        path
    )


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("SHORTBOT")
    print("=" * 60)
    print()

    print("Website:")
    print(
        "http://127.0.0.1:5000"
    )

    print()

    print("Downloads:")
    print(
        DOWNLOAD_DIR
    )

    print()

    print("Press CTRL+C to stop.")
    print()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )