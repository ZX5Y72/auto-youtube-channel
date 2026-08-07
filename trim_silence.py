import subprocess
import re

INPUT = "output/voiceover.mp3"
OUTPUT = "output/voiceover_trimmed.mp3"

# Detect silence: gaps quieter than -35dB lasting more than 0.3s
result = subprocess.run(
    ["ffmpeg", "-i", INPUT, "-af", "silencedetect=noise=-35dB:d=0.3", "-f", "null", "-"],
    stderr=subprocess.PIPE, text=True
)
log = result.stderr

starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]
ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]

if not starts or not ends:
    print("No significant silence detected, using original file.")
    import shutil
    shutil.copy(INPUT, OUTPUT)
else:
    # Build a filter that keeps everything EXCEPT the silence gaps
    # Trim each gap down to a short natural pause instead of removing it completely
    silence_pairs = list(zip(starts, ends))
    filter_parts = []
    prev_end = 0.0
    for i, (s_start, s_end) in enumerate(silence_pairs):
        # Keep audio up to the silence, then a short 0.15s pause instead of the full gap
        filter_parts.append(f"between(t,{prev_end},{s_start})")
        prev_end = s_end - min(s_end - s_start, s_end - s_start - 0.15)
    filter_parts.append(f"gte(t,{prev_end})")

    select_expr = "+".join(filter_parts)
    cmd = [
        "ffmpeg", "-y", "-i", INPUT,
        "-af", f"aselect='{select_expr}',asetpts=N/SR/TB",
        OUTPUT
    ]
    subprocess.run(cmd)
    print(f"Trimmed silence, saved to {OUTPUT}")
