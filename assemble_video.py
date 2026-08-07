import json
from moviepy import ImageClip, VideoFileClip, AudioFileClip, CompositeVideoClip, TextClip, concatenate_videoclips
import os
import subprocess
import random

os.makedirs("output", exist_ok=True)

with open("output/content.json", "r") as f:
    data = json.load(f)

audio = AudioFileClip("output/voiceover_trimmed.mp3")
total_duration = audio.duration

hook_clip = TextClip(
    text=data.get("hook_text", "").upper(),
    font_size=100,
    color="yellow",
    stroke_color="black",
    stroke_width=6,
    size=(1000, None),
    method="caption",
).with_duration(0.6).with_position("center")

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
        base = os.path.splitext(filename)[0]
        fg_path = os.path.join("output/images_parallax", f"{base}_fg.png")
        bg_path = os.path.join("output/images_parallax", f"{base}_bg.png")

        if os.path.exists(fg_path) and os.path.exists(bg_path):
            bg_clip = ImageClip(bg_path).with_duration(duration_per_scene)
            bg_clip = bg_clip.resized(height=1920)
            bg_clip = bg_clip.cropped(x_center=bg_clip.w / 2, width=1080)
            bg_clip = bg_clip.resized(lambda t: 1 + 0.08 * t)

            fg_clip = ImageClip(fg_path).with_duration(duration_per_scene)
            fg_clip = fg_clip.resized(height=1920)
            fg_clip = fg_clip.cropped(x_center=fg_clip.w / 2, width=1080)
            fg_clip = fg_clip.resized(lambda t: 1 + 0.20 * t)

            if style == 0:
                fg_clip = fg_clip.with_position(lambda t: (-40 * t, "center"))
            elif style == 1:
                fg_clip = fg_clip.with_position(lambda t: (40 * t, "center"))
            elif style == 2:
                fg_clip = fg_clip.with_position(lambda t: ("center", -35 * t))
            else:
                fg_clip = fg_clip.with_position("center")

            clip = CompositeVideoClip([bg_clip, fg_clip], size=(1080, 1920))
        else:
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

main_video = concatenate_videoclips(clips, method="compose")
video = CompositeVideoClip([main_video, hook_clip])
video = video.with_audio(audio)
video = video.resized(height=1920)
video = video.cropped(x_center=video.w / 2, width=1080)

video.write_videofile("output/temp_video.mp4", fps=30, codec="libx264", audio_codec="aac")

music_files = [f for f in os.listdir("music") if f.endswith(".mp3")]
chosen_music = os.path.join("music", random.choice(music_files))

has_overlay = False

sfx_dir = "output/sfx"
sfx_files = [f for f in os.listdir(sfx_dir) if f.endswith((".mp3", ".wav"))] if os.path.exists(sfx_dir) else []

cut_times = [duration_per_scene * i for i in range(1, num_scenes)]

inputs = ["-i", "output/temp_video.mp4", "-stream_loop", "-1", "-i", chosen_music, "-i", "branding/watermark.png"]
next_input_index = 3

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

video_filter = (
    "[0:v]ass=output/captions.ass[captioned];"
    "[captioned][3:v]overlay=x=main_w-overlay_w-30:y=40[vout];"
)

audio_filter = (
    "[0:a]volume=2.5[voice];"
    "[1:a]volume=0.35[music];"
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
