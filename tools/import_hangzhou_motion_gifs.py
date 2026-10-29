from pathlib import Path
import hashlib, json, subprocess
from PIL import Image
import imageio_ffmpeg

ROOT = Path('.').resolve()
SRC = Path(r"C:\Users\ailinker-intel\Downloads\monopoly-master\monopoly-master\output\作品集\杭城大亨\gifs")
PREVIEWS = ROOT / "assets" / "previews"
WORK = ROOT / "_gif_work" / "hangzhou-motion"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

ITEMS = [
    ("hangzhou-expression", "02-speech-and-expression.gif", "说话与表情"),
    ("hangzhou-cloth", "03-cloth-and-ambient.gif", "服饰与环境"),
]

def store(path, suffix):
    data = path.read_bytes()
    name = hashlib.sha256(data).hexdigest()[:20] + suffix
    dest = PREVIEWS / name
    dest.write_bytes(data)
    return f"assets/previews/{name}", len(data)

def gif_meta(path):
    im = Image.open(path)
    n = 0
    dur = 0
    try:
        while True:
            dur += im.info.get("duration") or 100
            n += 1
            im.seek(n)
    except EOFError:
        pass
    return n, dur / 1000, im.size

def compress(src, dest, fps, scale, colors):
    filt = (
        f"fps={fps},scale={scale}:-2:flags=lanczos,split[a][b];"
        f"[a]palettegen=max_colors={colors}:stats_mode=diff[p];"
        f"[b][p]paletteuse=dither=bayer:bayer_scale=4"
    )
    cmd = [FFMPEG, "-v", "error", "-y", "-ignore_loop", "1", "-i", str(src),
           "-filter_complex", filt, "-loop", "0", str(dest)]
    subprocess.run(cmd, check=True, timeout=240)

def poster(src, dest):
    cmd = [FFMPEG, "-v", "error", "-y", "-ignore_loop", "1", "-i", str(src),
           "-frames:v", "1", "-update", "1", str(dest)]
    subprocess.run(cmd, check=True, timeout=60)

def main():
    WORK.mkdir(parents=True, exist_ok=True)
    records = []
    for key, filename, title in ITEMS:
        src = SRC / filename
        out = WORK / f"{key}.gif"
        print("compress", filename, flush=True)
        compress(src, out, fps=10, scale=640, colors=72)
        size = out.stat().st_size
        if size > 1_600_000:
            print("  retry", size, flush=True)
            compress(src, out, fps=8, scale=540, colors=56)
        post = WORK / f"{key}.webp"
        poster(src, post)
        src_path, bytes_ = store(out, ".gif")
        poster_path, _ = store(post, ".webp")
        frames, seconds, wh = gif_meta(out)
        rec = {
            "name": key,
            "title": title,
            "src": src_path,
            "poster": poster_path,
            "bytes": bytes_,
            "frames": frames,
            "source": f"杭城大亨 / output/作品集/杭城大亨/gifs/{filename}",
            "start": 0,
            "seconds": round(seconds, 2),
            "fps": round(frames / seconds, 2) if seconds else 10,
        }
        records.append(rec)
        print(f"  {key}: {bytes_/1024:.0f}KB {frames}f {seconds:.2f}s {wh}", flush=True)
    (WORK / "records.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
