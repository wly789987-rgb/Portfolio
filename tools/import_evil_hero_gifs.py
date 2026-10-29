from pathlib import Path
import hashlib, json, subprocess, sys
from PIL import Image
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
SRC = Path(r"D:\wly\unity\EvilHero\evilhero\Portfolio\MainScene\gifs_sm")
PREVIEWS = ROOT / "assets" / "previews"
WORK = ROOT / "_gif_work" / "evil-hero"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

ITEMS = [
    ("evil-swordman", "swordman_melee.gif", "无极剑圣 · 近战攻击"),
    ("evil-axeking", "axeking_melee.gif", "狂暴斧王 · 近战攻击"),
    ("evil-shooter", "shooter_throw.gif", "暗影游侠 · 投掷攻击"),
    ("evil-pastor", "pastor_throw.gif", "光明牧师 · 投掷攻击"),
    ("evil-basics", "basics_throw.gif", "基础角色 · 投掷攻击"),
    ("evil-goblin-entry", "goblin_entry.gif", "哥布林 · 入场"),
    ("evil-goblin-attack", "goblin_attack.gif", "哥布林 · 攻击"),
    ("evil-robber-entry", "robber_entry.gif", "强盗 · 入场"),
    ("evil-robber-attack", "robber_attack.gif", "强盗 · 攻击"),
    ("evil-vampire-entry", "vampire_entry.gif", "吸血鬼 · 入场"),
    ("evil-vampire-attack", "vampire_attack.gif", "吸血鬼 · 攻击"),
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
    return dest

def poster(src, dest):
    cmd = [FFMPEG, "-v", "error", "-y", "-ignore_loop", "1", "-i", str(src),
           "-frames:v", "1", "-update", "1", str(dest)]
    subprocess.run(cmd, check=True, timeout=60)
    return dest

def main():
    WORK.mkdir(parents=True, exist_ok=True)
    records = []
    for key, filename, title in ITEMS:
        src = SRC / filename
        if not src.exists():
            raise SystemExit(f"missing {src}")
        out = WORK / filename
        print(f"compress {filename} ...", flush=True)
        compress(src, out, fps=10, scale=480, colors=72)
        size = out.stat().st_size
        if size > 1_800_000:
            print(f"  retry smaller ({size} bytes)", flush=True)
            compress(src, out, fps=8, scale=400, colors=56)
            size = out.stat().st_size
        post = WORK / (filename.replace(".gif", ".webp"))
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
            "source": f"EvilHero / Portfolio/MainScene/gifs_sm/{filename}",
            "start": 0,
            "seconds": round(seconds, 2),
            "fps": 10 if bytes_ < 1_800_000 else 8,
            "width": wh[0],
            "height": wh[1],
        }
        records.append(rec)
        print(f"  {key}: {bytes_/1024:.0f} KB, {frames}f, {seconds:.2f}s {wh}", flush=True)
    (WORK / "records.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", WORK / "records.json")

if __name__ == "__main__":
    main()
