import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI
import isodate
import time
import base64

# Set page config
st.set_page_config(
    page_title="YouTube Metadata Analyzer",
    page_icon="🎥",
    layout="wide"
)

# Add title and description
st.title("🎬 YouTube Metadata & Summary Analyzer")
st.markdown("Enter YouTube URLs to extract metadata and generate summaries.")

# API key inputs (with password protection)
with st.sidebar:
    st.header("API Keys")
    youtube_api_key = st.text_input("YouTube API Key", type="password")
    openai_api_key = st.text_input("OpenAI API Key", type="password")

    st.header("Options")
    generate_summary = st.checkbox("Generate summary with OpenAI", value=True)
    openai_model = st.selectbox("OpenAI Model", ["gpt-3.5-turbo", "gpt-4"], index=0)


# Function to extract video ID from URL
def get_video_id(url):
    try:
        return parse_qs(urlparse(url).query).get('v', [None])[0]
    except:
        return None


# Function to get YouTube video metadata
def get_video_metadata(video_id, youtube):
    try:
        request = youtube.videos().list(
            part='snippet,statistics,contentDetails,status,topicDetails',
            id=video_id
        )
        response = request.execute()

        if not response['items']:
            return None

        item = response['items'][0]

        metadata = {
            'video_id': video_id,
            'title': item['snippet']['title'],
            'channel': item['snippet']['channelTitle'],
            'published_at': item['snippet']['publishedAt'],
            'tags': ', '.join(item['snippet'].get('tags', [])),
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
            'topics': ', '.join(item.get('topicDetails', {}).get('topicCategories', [])),
            'description': item['snippet']['description']
        }

        return metadata
    except Exception as e:
        st.error(f"Error fetching metadata for video {video_id}: {str(e)}")
        return None


# Convert duration to human-readable format
def human_readable_duration(iso_duration):
    try:
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
    except:
        return "Unknown duration"


# Get transcript
def get_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([entry['text'] for entry in transcript])
    except Exception as e:
        st.warning(f"Could not retrieve transcript for video {video_id}: {str(e)}")
        return ""


# Summarize transcript using OpenAI
def summarize_with_openai(text, openai_client, model="gpt-3.5-turbo"):
    try:
        # Trim text to avoid token limit issues
        trimmed_text = text[:3000]

        prompt = f"Summarize the following YouTube transcript concisely:\n\n{trimmed_text}"
        response = openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Error generating summary: {str(e)}")
        return "Summary generation failed."


# Function to create a download link for dataframe
def get_csv_download_link(df, filename="youtube_metadata.csv"):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">Download CSV File</a>'
    return href


# Main input area
urls_input = st.text_area("Enter YouTube URLs (one per line)", height=150)

if st.button("Analyze Videos"):
    if not youtube_api_key:
        st.error("Please enter your YouTube API Key in the sidebar")
    elif generate_summary and not openai_api_key:
        st.error("Please enter your OpenAI API Key in the sidebar to generate summaries")
    elif not urls_input.strip():
        st.error("Please enter at least one YouTube URL")
    else:
        # Initialize clients
        youtube = build('youtube', 'v3', developerKey=youtube_api_key)
        if generate_summary:
            openai_client = OpenAI(api_key=openai_api_key)

        # Process URLs
        urls = [url.strip() for url in urls_input.splitlines() if url.strip()]

        # Show progress
        progress_bar = st.progress(0)
        status_text = st.empty()

        all_data = []

        for i, url in enumerate(urls):
            status_text.text(f"Processing URL {i + 1}/{len(urls)}: {url}")

            video_id = get_video_id(url)
            if not video_id:
                st.warning(f"Could not extract video ID from URL: {url}")
                continue

            metadata = get_video_metadata(video_id, youtube)
            if not metadata:
                st.warning(f"Could not fetch metadata for URL: {url}")
                continue

            # Get transcript and summary if enabled
            if generate_summary:
                transcript = get_transcript(video_id)
                if transcript:
                    metadata['summary'] = summarize_with_openai(transcript, openai_client, openai_model)
                else:
                    metadata['summary'] = "Transcript not available"

            all_data.append(metadata)

            # Update progress
            progress_bar.progress((i + 1) / len(urls))
            time.sleep(0.1)  # Small delay to prevent API rate limiting

        status_text.empty()

        if all_data:
            # Create DataFrame
            df = pd.DataFrame(all_data)

            # Display data
            st.subheader("Results")
            st.dataframe(df)

            # Create download link
            st.markdown(get_csv_download_link(df), unsafe_allow_html=True)

            # Display individual video data in expandable sections
            st.subheader("Detailed Information")
            for i, data in enumerate(all_data):
                with st.expander(f"{i + 1}. {data['title']}"):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown(f"**Channel:** {data['channel']}")
                        st.markdown(f"**Published:** {data['published_at']}")
                        st.markdown(f"**Duration:** {data['duration_readable']}")
                        st.markdown(f"**Views:** {data['views']}")
                        st.markdown(f"**Likes:** {data['likes']}")
                        st.markdown(f"**Comments:** {data['comments']}")

                    with col2:
                        st.markdown(f"**Definition:** {data['definition']}")
                        st.markdown(f"**Captions:** {data['caption_status']}")
                        st.markdown(f"**License:** {data['license']}")
                        st.markdown(f"**Privacy:** {data['privacy_status']}")
                        st.markdown(f"**Embeddable:** {data['embeddable']}")

                    st.markdown("**Description:**")
                    st.text(data['description'][:500] + ("..." if len(data['description']) > 500 else ""))

                    if generate_summary and 'summary' in data:
                        st.markdown("**AI Summary:**")
                        st.info(data['summary'])
        else:
            st.error("No valid data could be extracted from the provided URLs")

st.sidebar.markdown("---")
st.sidebar.markdown("""
### Tips:
- You need valid API keys for both YouTube Data API and OpenAI
- For multiple videos, enter each URL on a new line
- Videos without transcripts will not have summaries
- Summaries are generated using AI and may not be perfect
""")
