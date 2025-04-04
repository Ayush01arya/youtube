# app.py

from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from urllib.parse import urlparse, parse_qs
import os
import time
import uuid
import json
from datetime import datetime

app = Flask(__name__)

# Create output directory
OUTPUT_DIR = "transcripts"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# Function to extract video ID from URL
def extract_video_id(url):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    return query_params.get("v", [None])[0]


def process_video_url(url):
    video_id = extract_video_id(url)
    result = {
        "url": url,
        "video_id": video_id,
        "success": False,
        "message": "",
        "filename": "",
        "transcript": []
    }

    if not video_id:
        result["message"] = f"Invalid URL: {url}"
        return result

    try:
        transcript_raw = YouTubeTranscriptApi.get_transcript(video_id)

        # Process transcript with timestamps
        formatted_transcript = []
        for entry in transcript_raw:
            start = entry['start']
            minutes = int(start // 60)
            seconds = int(start % 60)
            timestamp = f"[{minutes:02}:{seconds:02}]"
            text_entry = f"{timestamp} {entry['text']}"
            formatted_transcript.append({
                "timestamp": timestamp,
                "raw_time": start,
                "text": entry['text']
            })

        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{video_id}_{timestamp}.txt"
        filepath = os.path.join(OUTPUT_DIR, filename)

        # Save transcript to file
        with open(filepath, "w", encoding="utf-8") as f:
            for entry in formatted_transcript:
                f.write(f"{entry['timestamp']} {entry['text']}\n")

        result["success"] = True
        result["message"] = f"Successfully processed transcript for {video_id}"
        result["filename"] = filename
        result["transcript"] = formatted_transcript

    except Exception as e:
        result["message"] = f"Error processing {video_id}: {str(e)}"

    return result


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/process', methods=['POST'])
def process():
    data = request.json
    urls = data.get('urls', [])

    if not urls:
        return jsonify({"success": False, "message": "No URLs provided"})

    results = []
    for url in urls:
        result = process_video_url(url)
        results.append(result)

    return jsonify({
        "success": True,
        "results": results,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })


@app.route('/download/<filename>')
def download(filename):
    return send_file(os.path.join(OUTPUT_DIR, filename), as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True)