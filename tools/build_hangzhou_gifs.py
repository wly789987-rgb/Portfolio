from pathlib import Path
import hashlib, json, os, shutil, subprocess, sys, re
from PIL import Image, ImageDraw, ImageFont

ROOT = [p for p in Path(r"C:/Users/ailinker-intel/.codex/worktrees/portfolio-versioning").iterdir() if p.is_dir() and not p.name.startswith(".")][0]
GAME = Path(r"C:/Users/ailinker-intel/Downloads/monopoly-master/monopoly-master")
PREVIEWS = ROOT / "assets" / "previews"
WORK = ROOT / "_gif_work"
REVIEW = GAME / "Tools" / "NewFourCharacterAnimations" / "Review"
sys.path.insert(0, str(Path(os.environ["TEMP"]) / "portfolio-media-deps"))
import imageio_ffmpeg
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

CHARS = [
    ("Xixi", "西溪旅人", "xixi-motion"),
    ("Yunqi", "云栖创客", "yunqi-motion"),
    ("Hubin", "湖滨织锦师", "hubin-motion"),
    ("Qianjiang", "钱江灯匠", "qianjiang-motion"),
]
EXPR = {
    "neutral": "Idle_Neutral_0.00.png",
    "half": "Idle_Half_0.00.png",
    "closed": "Idle_Closed_0.00.png",
    "ah": "Idle_Ah_0.00.png",
    "oh": "Idle_O_0.00.png",
}

def parse_json_array(text, marker):
    i = text.find(marker)
    i = text.find("[", i)
    depth = 0
    in_str = False
    esc = False
    for k, ch in enumerate(text[i:], i):
        if in_str:
            if esc: esc = False
            elif ch == "\\": esc = True
            elif ch == '"': in_str = False
            continue
        if ch == '"':
            in_str = True
            continue
        if ch in "[{": depth += 1
        elif ch in "]}":
            depth -= 1
            if depth == 0:
                return i, k + 1, json.loads(text[i:k + 1])
    raise SystemExit("unterminated " + marker)

def parse_js_object(text, marker):
    i = text.find(marker)
    i = text.find("{", i)
    depth = 0
    in_str = False
    esc = False
    for k, ch in enumerate(text[i:], i):
        if in_str:
            if esc: esc = False
            elif ch == "\\": esc = True
            elif ch == '"': in_str = False
            continue
        if ch == '"':
            in_str = True
            continue
        if ch == "{": depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i, k + 1, json.loads(text[i:k + 1])
    raise SystemExit("unterminated object " + marker)

def extract_object(text, needle):
    i = text.find(needle)
    depth = 0
    in_str = False
    esc = False
    for k, ch in enumerate(text[i:], i):
        if in_str:
            if esc: esc = False
            elif ch == "\\": esc = True
            elif ch == '"': in_str = False
            continue
        if ch == '"':
            in_str = True
            continue
        if ch == "{": depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i, k + 1, json.loads(text[i:k + 1])
    raise SystemExit("missing " + needle)

def store_file(path, suffix):
    data = path.read_bytes()
    name = hashlib.sha256(data).hexdigest()[:20] + suffix
    dest = PREVIEWS / name
    if dest.resolve() != path.resolve():
        dest.write_bytes(data)
    return "assets/previews/" + name, len(data)

def ffmpeg_gif(frames_dir, count, fps, scale, colors=96):
    out = frames_dir / "out.gif"
    filt = f"scale={scale}:-2:flags=lanczos,split[a][b];[a]palettegen=max_colors={colors}:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4"
    cmd = [FFMPEG, "-v", "error", "-y", "-framerate", str(fps), "-i", str(frames_dir / "%03d.png"),
           "-frames:v", str(count), "-filter_complex", filt, "-loop", "0", str(out)]
    subprocess.run(cmd, check=True, timeout=180)
    if out.stat().st_size > 1_400_000 and scale > 480:
        filt = filt.replace(f"scale={scale}", "scale=480").replace(f"max_colors={colors}", "max_colors=64")
        cmd[cmd.index("-filter_complex") + 1] = filt
        subprocess.run(cmd, check=True, timeout=180)
    return out

def crop_characters():
    sheets = {key: Image.open(REVIEW / name).convert("RGB") for key, name in EXPR.items()}
    w, h = sheets["neutral"].size
    slice_w = w // 4
    crops = {}
    for i, (cid, _, _) in enumerate(CHARS):
        box = (i * slice_w, 0, (i + 1) * slice_w, h)
        crops[cid] = {key: im.crop(box) for key, im in sheets.items()}
        print("crop", cid, crops[cid]["neutral"].size)
    return crops

def build_character_gifs(crops):
    results = {}
    timeline = (
        ["neutral"] * 10 + ["half", "closed", "closed", "half"] +
        ["neutral"] * 6 + ["ah", "oh", "ah", "oh", "ah"] + ["neutral"] * 8
    )
    for cid, name, slot in CHARS:
        d = WORK / cid
        if d.exists(): shutil.rmtree(d)
        d.mkdir(parents=True)
        sample = None
        for i, expr in enumerate(timeline):
            im = crops[cid][expr].copy()
            im.thumbnail((360, 480), Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", (360, 480), (45, 56, 68))
            x = (360 - im.width) // 2
            y = (480 - im.height) // 2
            canvas.paste(im, (x, y))
            canvas.save(d / f"{i:03d}.png")
            if sample is None:
                sample = canvas
        gif = ffmpeg_gif(d, len(timeline), 12, 360, 80)
        src, nbytes = store_file(gif, ".gif")
        poster_tmp = d / "poster.webp"
        sample.save(poster_tmp, "WEBP", quality=82, method=6)
        poster, _ = store_file(poster_tmp, ".webp")
        with Image.open(PREVIEWS / Path(src).name) as animation:
            frames = animation.n_frames
            seconds = sum((animation.seek(i) or animation.info.get("duration", 80)) for i in range(frames)) / 1000
        results[cid] = {
            "slot": slot, "name": name, "src": src, "poster": poster,
            "bytes": nbytes, "frames": frames, "seconds": round(seconds, 2),
        }
        print("char gif", cid, src, nbytes, frames, seconds)
        shutil.rmtree(d, ignore_errors=True)
    return results

def fit_frame(im, size=(960, 540), bg=(13, 21, 30)):
    canvas = Image.new("RGB", size, bg)
    im = im.convert("RGB")
    fitted = im.copy()
    fitted.thumbnail(size, Image.Resampling.LANCZOS)
    canvas.paste(fitted, ((size[0] - fitted.width) // 2, (size[1] - fitted.height) // 2))
    return canvas

def caption_frame(im, text):
    draw = ImageDraw.Draw(im)
    font = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 28)
    bar_h = 56
    w, h = im.size
    draw.rectangle([0, h - bar_h, w, h], fill=(8, 14, 22))
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(((w - tw) // 2, h - 44), text, font=font, fill=(214, 232, 238))
    return im

def build_play_gif():
    steps = [
        (GAME / "Tools/EightCharacterGameplayIntegration/CharacterSelection.png", "① 选择角色 · 2–4 人，八角色不重复"),
        (GAME / "Tools/EightCharacterGameplayIntegration/NewFourInGame.png", "② 开局须知 · 12 轮围桌经营"),
        (GAME / "Captures/PhaseOne/06-purchase-1280.png", "③ 购买地产 · 掷骰后买下经营点"),
        (GAME / "Captures/PhaseOne/12-property-details-panel.png", "④ 房产明细 · 收租与升级"),
        (GAME / "Captures/PhaseOne/05-full-game-results-1920.png", "⑤ 结算排名 · 净资产最高获胜"),
    ]
    d = WORK / "play"
    if d.exists(): shutil.rmtree(d)
    d.mkdir(parents=True)
    hold = 14
    n = 0
    poster = None
    for path, text in steps:
        frame = caption_frame(fit_frame(Image.open(path)), text)
        if poster is None:
            poster = frame.copy()
        for _ in range(hold):
            frame.save(d / f"{n:03d}.png")
            n += 1
    gif = ffmpeg_gif(d, n, 10, 960, 96)
    src, nbytes = store_file(gif, ".gif")
    poster_tmp = d / "poster.webp"
    poster.thumbnail((960, 540))
    poster.save(poster_tmp, "WEBP", quality=80, method=6)
    poster_url, _ = store_file(poster_tmp, ".webp")
    with Image.open(PREVIEWS / Path(src).name) as animation:
        frames = animation.n_frames
        seconds = sum((animation.seek(i) or animation.info.get("duration", 100)) for i in range(frames)) / 1000
    print("play gif", src, nbytes, frames, seconds)
    shutil.rmtree(d, ignore_errors=True)
    return {
        "name": "hangzhou-play",
        "title": "游玩方式 · 选角到结算",
        "src": src,
        "poster": poster_url,
        "bytes": nbytes,
        "frames": frames,
        "source": "杭城大亨工程选角、围桌与阶段对局截图",
        "start": 0,
        "seconds": round(seconds, 2),
        "fps": 10,
    }

def patch_site(char_gifs, play):
    js_path = ROOT / "app.js"
    original = js_path.read_text(encoding="utf-8")

    g0, g1, previews = parse_js_object(original, "const GIF_PREVIEWS=")
    previews["hangzhou-play"] = play

    b0, b1, media = parse_json_array(original, "const BUILTIN_MEDIA=")
    for cid, rec in char_gifs.items():
        key = "hangzhou-monopoly:" + rec["slot"]
        media[:] = [m for m in media if m.get("key") != key]
        media.append({"key": key, "name": cid.lower() + "-motion.gif", "type": "image/gif", "data": rec["src"]})

    p0, p1, project = extract_object(original, '{"id":"hangzhou-monopoly"')
    project["previewKeys"] = ["hangzhou-play"]
    slots = project.get("slots") or []
    def upsert(key, label):
        for i, s in enumerate(slots):
            if s[0] == key:
                slots[i] = [key, label]
                return
        slots.append([key, label])
    upsert("play", "游玩方式 GIF")
    for rec in char_gifs.values():
        upsert(rec["slot"], rec["name"] + "表情动图")
    project["slots"] = slots

    dump = lambda obj: json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    edits = [(g0, g1, dump(previews)), (b0, b1, dump(media)), (p0, p1, dump(project))]
    edits.sort(key=lambda x: x[0], reverse=True)
    out = original
    for a, b, rep in edits:
        out = out[:a] + rep + out[b:]

    old_note = "八名角色均来自独立制作的杭城大亨：分层立绘、待机呼吸、眨眼与说话口型。"
    new_note = "前四名为网页分层预览；后四名西溪、云栖、湖滨、钱江使用工程表情序列 GIF，展示眨眼与说话。"
    if old_note in out:
        out = out.replace(old_note, new_note)
    else:
        print("WARN note missing")

    start = out.find("function openMonopoly(p){")
    end = out.find("function forestDeckHTML", start)
    if start < 0 or end < 0:
        raise SystemExit("openMonopoly missing")
    open_fn = """function openMonopoly(p){activeProject=p.id;$('#project-detail').innerHTML=`<div class="detail-content compact-project"><p class="project-category">${escapeHTML(p.category)}</p><h2>${escapeHTML(p.title)}</h2><p class="detail-summary">${escapeHTML(p.summary)}</p><div class="tags">${p.tags.map(t=>'<span>'+escapeHTML(t)+'</span>').join('')}</div><h3>游玩方式</h3><div class="turtle-gif-gallery">${(p.previewKeys||[]).map(key=>{const preview=GIF_PREVIEWS[key];return preview?'<figure><figcaption>'+escapeHTML(preview.title)+'</figcaption>'+gifPreviewHTML(preview,preview.title)+'</figure>':''}).join('')}</div>${characterCompareHTML()}${p.breakdown?`<div class="technical-breakdown">${p.breakdown.map(b=>`<article><h3>${escapeHTML(b.title)}</h3><p>${escapeHTML(b.text)}</p></article>`).join('')}</div>`:''}<h3 class="detail-gallery-heading">场景与界面</h3><div class="detail-gallery"><div class="gallery-slot"><div class="slot-visual">${visualHTML(p)}</div><p>棋盘全貌</p></div><div class="gallery-slot"><div class="slot-visual">${visualHTML(p,p.id+':cast')}</div><p>八角色选人</p></div><div class="gallery-slot"><div class="slot-visual">${visualHTML(p,p.id+':table')}</div><p>围桌对局</p></div><div class="gallery-slot"><div class="slot-visual">${visualHTML(p,p.id+':ui')}</div><p>房产明细 · 四向 UI</p></div></div><p class="source-note">${escapeHTML(p.sourceNote||'')}</p></div>`;if(!$('#project-dialog').open)$('#project-dialog').showModal();mountCharacterComparisons($('#project-dialog'))}

"""
    out = out[:start] + open_fn + out[end:]
    js_path.write_text(out, encoding="utf-8")
    print("app.js patched")

    catalog_file = PREVIEWS / "catalog.json"
    catalog = json.loads(catalog_file.read_text(encoding="utf-8"))
    catalog = [r for r in catalog if not str(r.get("name","")).startswith("hangzhou-")]
    catalog.append(play)
    for cid, rec in char_gifs.items():
        catalog.append({
            "name": "hangzhou-" + cid.lower(),
            "title": rec["name"] + " · 眨眼说话",
            "src": rec["src"],
            "poster": rec["poster"],
            "bytes": rec["bytes"],
            "frames": rec["frames"],
            "source": "NewFourCharacterAnimations/Review",
            "start": 0,
            "seconds": rec["seconds"],
            "fps": 12,
        })
    catalog_file.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")

def changelog():
    log = ROOT / "更新记录.md"
    text = log.read_text(encoding="utf-8")
    entry = """## 2026-10-27 — 杭城大亨游玩 GIF 与四名新角色表情（本地待发布）

- 后四名角色改用工程表情序列 GIF，展示眨眼与说话，替换不准的网页口型/眼睛叠加。
- 新增游玩方式动图：选角、开局须知、购买地产、房产明细、结算排名。
- 按本人此前要求：未同步 GitHub、未发布云端。

"""
    if "杭城大亨游玩 GIF 与四名新角色表情" not in text:
        lines = text.splitlines(True)
        text = lines[0] + "\n" + entry + "".join(lines[1:]) if lines and lines[0].startswith("#") else entry + text
        log.write_text(text, encoding="utf-8")

def bump():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    html = re.sub(r"\?v=[^\"']+", "?v=20261027-hangzhou-gif", html, count=6)
    (ROOT / "index.html").write_text(html, encoding="utf-8")

def main():
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    if WORK.exists(): shutil.rmtree(WORK)
    WORK.mkdir()
    crops = crop_characters()
    char_gifs = build_character_gifs(crops)
    play = build_play_gif()
    patch_site(char_gifs, play)
    changelog()
    bump()
    shutil.rmtree(WORK, ignore_errors=True)
    print("ALL DONE")

if __name__ == "__main__":
    main()
