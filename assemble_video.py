import json
from moviepy import ImageClip, VideoFileClip, AudioFileClip, concatenate_videoclips
import os
import subprocess
import random

os.makedirs("output", exist_ok=True)

with open("output/content.json", "r") as f:
    data = json.load(f)

audio = AudioFileClip("output/voiceover.mp3")
total_duration = audio.duration

image_files = sorted(os.listdir("output/images"))

broll_dir = "output/broll"
broll_files = sorted(os.listdir(broll_dir)) if os.path.exists(broll_dir) else []

scene_sources = list(image_files) + list(broll_files)
random.shuffle(scene_sources)

num_scenes = len(scene_sources)
duration_per_scene = total_duration / num_scenes

clips = []
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

overlay_dir = "output/overlays_fetched"
overlay_files = [f for f in os.listdir(overlay_dir) if f.endswith((".mp4", ".m4v"))] if os.path.exists(overlay_dir) else []
has_overlay = len(overlay_files) > 0
if has_overlay:
    chosen_overlay = os.path.join(overlay_dir, random.choice(overlay_files))

sfx_dir = "output/sfx"
sfx_files = [f for f in os.listdir(sfx_dir) if f.endswith((".mp3", ".wav"))] if os.path.exists(sfx_dir) else []

cut_times = [duration_per_scene * i for i in range(1, num_scenes)]

inputs = ["-i", "output/temp_video.mp4", "-stream_loop", "-1", "-i", chosen_music]
next_input_index = 2

if has_overlay:
    inputs += ["-stream_loop", "-1", "-i", chosen_overlay]
    overlay_input_index = next_input_index
    next_input_index += 1

sfx_labels = []
sfx_filter_chain = ""
if sfx_files:
    for idx, cut_time in enumerate(cut_times):
        chosen_sfx = os.path.join(sfx_dir, random.choice(sfx_files))
        inputs += ["-i", chosen_sfx]
        input_index = next_input_index
        next_input_index += 1
        delay_ms = int(cut_time * 1000)
        label = f"sfx{idx}"
        sfx_labels.append(f"[{label}]")
        sfx_filter_chain += f"[{input_index}:a]adelay={delay_ms}|{delay_ms},volume=0.5[{label}];"

sfx_mix_inputs = "".join(sfx_labels)
sfx_count = len(sfx_labels)

if has_overlay:
    video_filter = (
        f"[{overlay_input_index}:v]scale=1080:1920,format=rgba,lumakey=threshold=0.15:tolerance=0.05:softness=0.1,colorchannelmixer=aa=0.5[overlay];"
        "[0:v][overlay]overlay[blended];"
        "[blended]ass=output/captions.ass[vout];"
    )
else:
    video_filter = "[0:v]ass=output/captions.ass[vout];"

audio_filter = (
    "[0:a]volume=2.5[voice];"
    "[1:a]volume=0.12[music];"
    f"{sfx_filter_chain}"
    f"[voice][music]{sfx_mix_inputs}amix=inputs={2 + sfx_count}:duration=first:normalize=0[aout]"
)

filter_complex = video_filter + audio_filter

cmd = ["ffmpeg", "-y"] + inputs + [
    "-filter_complex", filter_complex,
    "-map", "[vout]", "-map", "[aout]",
    "-t", str(total_duration),
    "-c:v", "libx264", "-c:a", "aac",
    "output/final_video.mp4"
]

subprocess.run(cmd)

os.remove("output/temp_video.mp4")

print("Video assembled: output/final_video.mp4")
