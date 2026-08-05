import json
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
import os
import subprocess
import random

os.makedirs("output", exist_ok=True)

with open("output/content.json", "r") as f:
    data = json.load(f)

audio = AudioFileClip("output/voiceover.mp3")
total_duration = audio.duration

image_files = sorted(os.listdir("output/images"))
num_images = len(image_files)
duration_per_image = total_duration / num_images

clips = []
for i, img_file in enumerate(image_files):
    img_path = os.path.join("output/images", img_file)
    clip = ImageClip(img_path).with_duration(duration_per_image)

    style = i % 4

    if style == 0:
        clip = clip.resized(lambda t: 1 + 0.05 * t)
        clip = clip.with_position(lambda t: (-20 * t, "center"))
    elif style == 1:
        clip = clip.resized(lambda t: 1.15 - 0.05 * t)
        clip = clip.with_position(lambda t: (20 * t, "center"))
    elif style == 2:
        clip = clip.resized(lambda t: 1 + 0.05 * t)
        clip = clip.with_position(lambda t: ("center", -15 * t))
    else:
        clip = clip.resized(lambda t: 1 + 0.03 * t)

    clips.append(clip)

video = concatenate_videoclips(clips, method="compose")
video = video.with_audio(audio)

video = video.resized(height=1920)
video = video.cropped(x_center=video.w / 2, width=1080)

video.write_videofile("output/temp_video.mp4", fps=30, codec="libx264", audio_codec="aac")

music_files = [f for f in os.listdir("music") if f.endswith(".mp3")]
chosen_music = os.path.join("music", random.choice(music_files))

overlay_files = [f for f in os.listdir("overlays") if f.endswith((".mp4", ".m4v"))]
chosen_overlay = os.path.join("overlays", random.choice(overlay_files))

subprocess.run([
    "ffmpeg", "-y",
    "-i", "output/temp_video.mp4",
    "-stream_loop", "-1", "-i", chosen_music,
    "-stream_loop", "-1", "-i", chosen_overlay,
    "-filter_complex",
    "[2:v]scale=1080:1920,format=rgba,colorchannelmixer=aa=0.35[overlay];"
    "[0:v][overlay]blend=all_mode='screen'[blended];"
    "[blended]subtitles=output/captions.srt:force_style='FontName=Arial Black,FontSize=16,Bold=1,PrimaryColour=&H00FFFF,OutlineColour=&H000000,Outline=3,Shadow=0,BorderStyle=1,Alignment=2,MarginV=120'[vout];"
    "[1:a]volume=0.12[music];[0:a][music]amix=inputs=2:duration=first[aout]",
    "-map", "[vout]", "-map", "[aout]",
    "-shortest",
    "-c:v", "libx264", "-c:a", "aac",
    "output/final_video.mp4"
])

os.remove("output/temp_video.mp4")

print("Video assembled: output/final_video.mp4")
