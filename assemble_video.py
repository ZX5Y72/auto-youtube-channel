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
num_images = num_scenes
duration_per_image = duration_per_scene
from moviepy import VideoFileClip

clips = []

# Load any B-roll clips we fetched
broll_dir = "output/broll"
broll_files = sorted(os.listdir(broll_dir)) if os.path.exists(broll_dir) else []

scene_sources = list(image_files) + list(broll_files)
random.shuffle(scene_sources)  # mix broll and AI images unpredictably

num_scenes = len(scene_sources)
duration_per_scene = total_duration / num_scenes

for i, filename in enumerate(scene_sources):
    style = i % 4

    if filename in broll_files:
        clip_path = os.path.join(broll_dir, filename)
        clip = VideoFileClip(clip_path).with_duration(duration_per_scene)
        clip = clip.resized(height=1920)
        clip = clip.cropped(x_center=clip.w / 2, width=1080)
    else:
        clip_path = os.path.join("output/images", filename)
        clip = ImageClip(clip_path).with_duration(duration_per_scene)
        if style == 0:
            clip = clip.resized(lambda t: 1 + 0.15 * t)
            clip = clip.with_position(lambda t: (-35 * t, "center"))
        elif style == 1:
            clip = clip.resized(lambda t: 1.25 - 0.15 * t)
            clip = clip.with_position(lambda t: (35 * t, "center"))
        elif style == 2:
            clip = clip.resized(lambda t: 1 + 0.15 * t)
            clip = clip.with_position(lambda t: ("center", -30 * t))
        else:
            clip = clip.resized(lambda t: 1 + 0.10 * t)

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
    "[2:v]scale=1080:1920,format=rgba,lumakey=threshold=0.15:tolerance=0.05:softness=0.1,colorchannelmixer=aa=0.5[overlay];"
    "[0:v][overlay]overlay[blended];"
    "[blended]ass=output/captions.ass[vout];"
    "[1:a]volume=0.12[music];[0:a][music]amix=inputs=2:duration=first[aout]",
    "-map", "[vout]", "-map", "[aout]",
    "-t", str(total_duration),
    "-c:v", "libx264", "-c:a", "aac",
    "output/final_video.mp4"
])

os.remove("output/temp_video.mp4")

print("Video assembled: output/final_video.mp4")
