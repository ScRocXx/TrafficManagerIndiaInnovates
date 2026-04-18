"""
Northern Blades — Step 2: Extract Frames from YouTube Traffic Videos
Extracts 1 frame every N seconds from YouTube videos for training data.

Usage:
  pip install yt-dlp opencv-python
  python 02_youtube_extractor.py
"""

import cv2
import os
import sys

try:
    import yt_dlp
except ImportError:
    print("Install yt-dlp first: pip install yt-dlp")
    sys.exit(1)

# ─── CONFIG ───────────────────────────────────────────────────────────────────
# Curated Delhi/Indian traffic videos with HIGH-ANGLE CCTV perspectives
VIDEOS = [
    {
        "url": "https://www.youtube.com/watch?v=_vAQ_ZYyUAI",
        "name": "ashram_chowk",
        "desc": "Delhi Ring Road / Ashram Chowk - high angle overhead"
    },
    {
        "url": "https://www.youtube.com/watch?v=HTP5t5t7pkA",
        "name": "ito_intersection",
        "desc": "ITO intersection Delhi - multi-lane high angle"
    },
    {
        "url": "https://www.youtube.com/watch?v=PmFd0K0CEeQ",
        "name": "bengaluru_drone",
        "desc": "Bengaluru drone AI traffic footage - true BEV"
    },
]

OUTPUT_DIR = "northern_blades_dataset/images/all_raw"
INTERVAL_SECONDS = 3  # 1 frame every 3 seconds (diverse, not redundant)
# ─────────────────────────────────────────────────────────────────────────────


def extract_frames(url, video_name, output_dir, interval_sec):
    """Download video and extract frames at regular intervals."""
    os.makedirs(output_dir, exist_ok=True)
    temp_video = f"_temp_{video_name}.mp4"

    # Download video
    print(f"  Downloading: {video_name}...")
    ydl_opts = {
        'format': 'bestvideo[ext=mp4][height<=1080]/best[ext=mp4]',
        'outtmpl': temp_video,
        'noplaylist': True,
        'quiet': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        print(f"  ERROR downloading {video_name}: {e}")
        return 0

    # Extract frames
    cap = cv2.VideoCapture(temp_video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if fps == 0:
        print(f"  ERROR: Could not read video FPS for {video_name}")
        cap.release()
        return 0

    frames_to_skip = int(fps * interval_sec)
    expected_count = total_frames // frames_to_skip
    print(f"  FPS: {fps:.0f}, Total frames: {total_frames}, Extracting ~{expected_count} frames...")

    count = 0
    saved = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if count % frames_to_skip == 0:
            timestamp_sec = int(count / fps)
            minutes = timestamp_sec // 60
            seconds = timestamp_sec % 60
            fname = f"yt_{video_name}_T{minutes:02d}m{seconds:02d}s.jpg"
            filepath = os.path.join(output_dir, fname)

            cv2.imwrite(filepath, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            saved += 1

        count += 1

    cap.release()

    # Clean up temp video
    if os.path.exists(temp_video):
        os.remove(temp_video)

    return saved


def main():
    print("=" * 50)
    print("Northern Blades — YouTube Frame Extractor")
    print(f"Extracting 1 frame every {INTERVAL_SECONDS}s")
    print("=" * 50)

    total_saved = 0

    for video in VIDEOS:
        print(f"\n[{video['name']}] {video['desc']}")
        saved = extract_frames(
            url=video['url'],
            video_name=video['name'],
            output_dir=OUTPUT_DIR,
            interval_sec=INTERVAL_SECONDS
        )
        print(f"  Saved {saved} frames.")
        total_saved += saved

    print(f"\n{'=' * 50}")
    print(f"DONE! Total: {total_saved} YouTube frames saved to {OUTPUT_DIR}")
    print(f"{'=' * 50}")
    print("\nNext step: Run 03_sam_mask_generator.py on Colab (needs GPU)")


if __name__ == "__main__":
    main()
