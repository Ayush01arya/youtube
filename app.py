# app.py

from flask import Flask, render_template, request, jsonify, make_response
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
import os
import csv
import io
from datetime import datetime

app = Flask(__name__)


# Function to extract video ID from URL
def extract_video_id(url):
    parsed_url = urlparse(url)

    # Handle both youtube.com and youtu.be URLs
    if parsed_url.netloc == 'youtu.be':
        return parsed_url.path.lstrip('/')

    if parsed_url.netloc in ('www.youtube.com', 'youtube.com'):
        query_params = parse_qs(parsed_url.query)
        return query_params.get("v", [None])[0]

    return None


def process_video_url(url):
    video_id = extract_video_id(url)
    result = {
        "url": url,
        "video_id": video_id,
        "success": False,
        "message": "",
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
            formatted_transcript.append({
                "timestamp": timestamp,
                "raw_time": start,
                "text": entry['text']
            })

        result["success"] = True
        result["message"] = f"Successfully processed transcript for {video_id}"
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


@app.route('/download', methods=['POST'])
def download():
    data = request.json
    transcript_data = data.get('transcript', [])
    video_id = data.get('video_id', 'unknown')
    file_format = data.get('format', 'txt')

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{video_id}_{timestamp}"

    if file_format == 'txt':
        output = io.StringIO()
        for entry in transcript_data:
            output.write(f"{entry['timestamp']} {entry['text']}\n")

        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = f"attachment; filename={filename}.txt"
        response.headers["Content-type"] = "text/plain"

    elif file_format == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Timestamp', 'Raw Time', 'Text'])

        for entry in transcript_data:
            writer.writerow([entry['timestamp'], entry['raw_time'], entry['text']])

        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = f"attachment; filename={filename}.csv"
        response.headers["Content-type"] = "text/csv"

    else:
        return jsonify({"success": False, "message": "Invalid format specified"})

    return response


if __name__ == '__main__':
    app.run(debug=True)