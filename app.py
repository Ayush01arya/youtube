from googleapiclient.discovery import build
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI



# Set your API keys
# YOUTUBE_API_KEY = 'AIzaSyAuO1En3zp1WIhUeEp5WcHu5nyRUb8ooWU'
# OPENAI_API_KEY = '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'
from flask import Flask, request, jsonify, render_template, Response
from googleapiclient.discovery import build
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI
import isodate
import csv
import io
import os
from flask_cors import CORS

# Load environment variables


app = Flask(__name__)
CORS(app)
YOUTUBE_API_KEY = 'AIzaSyAuO1En3zp1WIhUeEp5WcHu5nyRUb8ooWU'
OPENAI_API_KEY = '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'


# Initialize clients
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)


# Extract video ID from URL
def get_video_id(url):
    return parse_qs(urlparse(url).query).get('v', [None])[0]


# Get YouTube video metadata
def get_video_metadata(video_id):
    try:
        request = youtube.videos().list(
            part='snippet,statistics,contentDetails,status,topicDetails',
            id=video_id
        )
        response = request.execute()

        if not response.get('items'):
            return None

        item = response['items'][0]

        metadata = {
            'video_id': video_id,
            'title': item['snippet']['title'],
            'description': item['snippet']['description'],
            'channel': item['snippet']['channelTitle'],
            'published_at': item['snippet']['publishedAt'],
            'tags': item['snippet'].get('tags', []),
            'category_id': item['snippet']['categoryId'],
            'views': item['statistics'].get('viewCount', 0),
            'likes': item['statistics'].get('likeCount', 0),
            'comments': item['statistics'].get('commentCount', 0),
            'duration': item['contentDetails']['duration'],
            'duration_readable': human_readable_duration(item['contentDetails']['duration']),
            'definition': item['contentDetails']['definition'],
            'caption_status': item['contentDetails']['caption'],
            'privacy_status': item['status']['privacyStatus'],
            'embeddable': item['status']['embeddable'],
            'license': item['status']['license'],
            'topics': item.get('topicDetails', {}).get('topicCategories', []),
            'thumbnail': item['snippet']['thumbnails']['high']['url']
        }

        return metadata
    except Exception as e:
        print(f"Error fetching metadata: {str(e)}")
        return None


# Convert duration to human-readable format
def human_readable_duration(iso_duration):
    duration = isodate.parse_duration(iso_duration)
    minutes, seconds = divmod(duration.total_seconds(), 60)
    hours, minutes = divmod(minutes, 60)

    result = []
    if hours:
        result.append(f"{int(hours)} hour{'s' if hours > 1 else ''}")
    if minutes:
        result.append(f"{int(minutes)} minute{'s' if minutes > 1 else ''}")
    if seconds:
        result.append(f"{int(seconds)} second{'s' if seconds > 1 else ''}")

    return ', '.join(result)


# Get transcript
def get_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([entry['text'] for entry in transcript])
    except Exception as e:
        print(f"Error fetching transcript: {str(e)}")
        return "Transcript not available for this video."


# Summarize transcript using OpenAI
def summarize_with_openai(text, model="gpt-3.5-turbo"):
    try:
        if text == "Transcript not available for this video.":
            return "Summary not available as transcript could not be fetched."

        prompt = f"Summarize the following YouTube transcript in about 3-4 paragraphs highlighting the main points:\n\n{text[:3000]}"
        response = openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error summarizing with OpenAI: {str(e)}")
        return "Error generating summary."


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/analyze', methods=['POST'])
def analyze_video():
    data = request.json
    urls = data.get('urls', [])

    if not urls:
        return jsonify({"error": "No URLs provided"}), 400

    results = []

    for url in urls:
        video_id = get_video_id(url)
        if not video_id:
            results.append({"error": f"Invalid YouTube URL: {url}"})
            continue

        metadata = get_video_metadata(video_id)
        if not metadata:
            results.append({"error": f"Could not fetch metadata for video: {url}"})
            continue

        transcript = get_transcript(video_id)
        summary = summarize_with_openai(transcript)

        result = {
            "metadata": metadata,
            "transcript": transcript[:500] + "..." if len(transcript) > 500 else transcript,
            "transcript_full": transcript,
            "summary": summary
        }

        results.append(result)

    return jsonify(results)


@app.route('/api/download-csv', methods=['POST'])
def download_csv():
    data = request.json
    results = data.get('results', [])

    if not results:
        return jsonify({"error": "No data to download"}), 400

    # Create CSV file in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header row
    writer.writerow([
        'Video ID', 'Title', 'Channel', 'Published Date',
        'Views', 'Likes', 'Comments', 'Duration',
        'Definition', 'Caption Status', 'License', 'Summary'
    ])

    # Write data rows
    for result in results:
        if 'error' in result:
            continue

        metadata = result['metadata']
        writer.writerow([
            metadata['video_id'],
            metadata['title'],
            metadata['channel'],
            metadata['published_at'],
            metadata['views'],
            metadata['likes'],
            metadata['comments'],
            metadata['duration_readable'],
            metadata['definition'],
            metadata['caption_status'],
            metadata['license'],
            result['summary'].replace('\n', ' ')
        ])

    # Prepare response
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=youtube_analysis.csv"}
    )


if __name__ == '__main__':
    app.run(debug=True)
