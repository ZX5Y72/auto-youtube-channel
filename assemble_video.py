import json
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip
import os

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
    clip = ImageClip(img_path).set_duration(duration_per_image)

    # Ken Burns effect: slow zoom-in, gives the "animated" feel instead of a static slideshow
    clip = clip.resize(lambda t: 1 + 0.04 * t)
    clip = clip.set_position(("center", "center"))

    clips.append(clip)

video = concatenate_videoclips(clips, method="compose")
video = video.set_audio(audio)

# Resize/crop to vertical 9:16 for Shorts
video = video.resize(height=1920)
video = video.crop(x_center=video.w / 2, width=1080)

import subprocess

video.write_videofile("output/temp_video.mp4", fps=30, codec="libx264", audio_codec="aac")

# Burn captions in with FFmpeg, styled for Shorts (bold, centered, readable on mobile)
subprocess.run([
    "ffmpeg", "-y", "-i", "output/temp_video.mp4",
    "-vf", "subtitles=output/captions.srt:force_style='FontName=Arial,FontSize=16,Bold=1,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,BorderStyle=3,Alignment=2,MarginV=100'",
    "-c:a", "copy", "output/final_video.mp4"
])

os.remove("output/temp_video.mp4")
print("Video assembled: output/final_video.mp4")
