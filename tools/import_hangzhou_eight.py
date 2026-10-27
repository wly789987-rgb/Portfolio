from pathlib import Path
import hashlib, json, math, re, shutil
from PIL import Image

PORTFOLIO = [p for p in Path(r"C:/Users/ailinker-intel/.codex/worktrees/portfolio-versioning").iterdir() if p.is_dir() and not p.name.startswith(".")][0]
GAME = Path(r"C:/Users/ailinker-intel/Downloads/monopoly-master/monopoly-master")
MEDIA = PORTFOLIO / "assets" / "media"

NEW_CHARS = [
    {"id": "Xixi", "name": "西溪旅人", "skill": "另寻路径", "color": "#7ec9c4", "slot": "xixi-motion", "phase": 0.7, "interval": 5.1, "strength": 0.78},
    {"id": "Yunqi", "name": "云栖创客", "skill": "机关改装", "color": "#9bb0c0", "slot": "yunqi-motion", "phase": 1.4, "interval": 5.6, "strength": 0.72},
    {"id": "Hubin", "name": "湖滨织锦师", "skill": "巧手织备", "color": "#e5b08a", "slot": "hubin-motion", "phase": 2.1, "interval": 4.9, "strength": 0.8},
    {"id": "Qianjiang", "name": "钱江灯匠", "skill": "引灯绕行", "color": "#e0b56a", "slot": "qianjiang-motion", "phase": 2.8, "interval": 5.3, "strength": 0.76},
]
EXISTING_SKILLS = {
    "Longjing": "从容经营",
    "Hefang": "连锁筹备",
    "GrandCanal": "灵活航线",
    "Qiantang": "化险为夷",
}

def parse_json_array(text, marker):
    i = text.find(marker)
    if i < 0:
        raise SystemExit("missing " + marker)
    i = text.find("[", i)
    depth = 0
    in_str = False
    esc = False
    for k, ch in enumerate(text[i:], i):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
            continue
        if ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
            if depth == 0:
                return i, k + 1, json.loads(text[i:k + 1])
    raise SystemExit("unterminated " + marker)

def extract_object(text, needle):
    i = text.find(needle)
    if i < 0:
        raise SystemExit("missing object " + needle)
    depth = 0
    in_str = False
    esc = False
    for k, ch in enumerate(text[i:], i):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i, k + 1, json.loads(text[i:k + 1])
    raise SystemExit("unterminated object " + needle)

def save_webp(im, quality=82):
    im = im.convert("RGBA")
    tmp = PORTFOLIO / "_tmp_enc.webp"
    im.save(tmp, "WEBP", quality=quality, method=6, lossless=False)
    data = tmp.read_bytes()
    name = hashlib.sha256(data).hexdigest()[:20] + ".webp"
    dest = MEDIA / name
    if not dest.exists():
        dest.write_bytes(data)
    tmp.unlink(missing_ok=True)
    return "assets/media/" + name

def fit_portrait(im, max_h=960):
    im = im.convert("RGBA")
    w, h = im.size
    if h > max_h:
        scale = max_h / h
        im = im.resize((max(1, round(w * scale)), max_h), Image.Resampling.LANCZOS)
    return im

def resize_to(im, size):
    return im.convert("RGBA").resize(size, Image.Resampling.LANCZOS)

def bbox_uv(base, overlay, box):
    x0, y0, x1, y1 = box
    w, h = base.size
    px0, px1 = int(x0 * w), int(x1 * w)
    py0, py1 = int(y0 * h), int(y1 * h)
    b = base.crop((px0, py0, px1, py1))
    o = overlay.crop((px0, py0, px1, py1))
    bp, op = b.load(), o.load()
    xs, ys = [], []
    cw, ch = b.size
    for y in range(ch):
        for x in range(cw):
            br, bg, bb, ba = bp[x, y]
            r, g, bl, a = op[x, y]
            if a < 20 or ba < 20:
                continue
            if abs(r - br) + abs(g - bg) + abs(bl - bb) >= 30:
                xs.append(x)
                ys.append(y)
    if len(xs) < 40:
        return None
    pad = 8
    left = max(0, min(xs) - pad)
    top = max(0, min(ys) - pad)
    right = min(cw - 1, max(xs) + pad)
    bottom = min(ch - 1, max(ys) + pad)
    cx = (left + right) / 2 + px0
    cy = (top + bottom) / 2 + py0
    rx = (right - left) / 2 / w
    ry = (bottom - top) / 2 / h
    return [round(cx / w, 3), round(1 - cy / h, 3), round(max(rx, 0.02), 3), round(max(ry, 0.015), 3)]

def fallback_face():
    return {
        "LeftEye": [0.42, 0.70, 0.055, 0.03],
        "RightEye": [0.54, 0.70, 0.055, 0.03],
        "Lips": [0.48, 0.61, 0.05, 0.03],
    }

def make_idle(cx, cy):
    keys = []
    for i in range(17):
        t = round(i * 0.5, 3)
        dy = round(1.15 * math.sin(t / 8 * 2 * math.pi), 5)
        tang = round(1.15 * 2 * math.pi / 8 * math.cos(t / 8 * 2 * math.pi), 5)
        keys.append([t, cx, cy + dy, 0.0, 0.0, tang, 0.0, 0.0, tang, 0.0])
    return {"duration": 8.0, "curves": {"Bone_Chest": {"p": keys}}}

def build_character(spec):
    art = GAME / "Assets" / "Art" / "UI" / f"{spec['id']}PlayerPanel" / "ColorTheme"
    portrait = fit_portrait(Image.open(art / "Portrait.png"))
    anim = art / "Animation20261016"
    half = resize_to(Image.open(anim / "EyesHalf.png"), portrait.size)
    closed = resize_to(Image.open(anim / "EyesClosed.png"), portrait.size)
    ah = resize_to(Image.open(anim / "MouthAh.png"), portrait.size)
    oh = resize_to(Image.open(anim / "MouthO.png"), portrait.size)
    left = bbox_uv(portrait, closed, (0.12, 0.05, 0.55, 0.52))
    right = bbox_uv(portrait, closed, (0.45, 0.05, 0.88, 0.52))
    lips = bbox_uv(portrait, ah, (0.25, 0.28, 0.75, 0.72))
    face = fallback_face()
    if left:
        face["LeftEye"] = left
    if right:
        face["RightEye"] = right
    if lips:
        face["Lips"] = lips
    print(spec["id"], "size", portrait.size, "face", face)
    img = save_webp(portrait)
    face_paths = {
        "EyesHalf": save_webp(half),
        "EyesClosed": save_webp(closed),
        "MouthAh": save_webp(ah),
        "MouthO": save_webp(oh),
        **face,
    }
    w, h = portrait.size
    size_w, size_h = 422.0, round(422.0 * h / w, 1)
    bx, by = size_w / 2.0, -size_h * 0.70
    return {
        "faceTiming": {"interval": spec["interval"], "phase": spec["phase"], "strength": spec["strength"]},
        "role": spec["id"],
        "name": spec["name"],
        "skill": spec["skill"],
        "color": spec["color"],
        "slot": spec["slot"],
        "size": [size_w, size_h],
        "pivot": [0.0, 1.0],
        "bones": {"Bone_Chest": {"p": [bx, by], "r": 0.0, "s": [1.0, 1.0]}},
        "layers": [{
            "name": "Layer_Portrait",
            "image": img,
            "bones": ["Bone_Chest"],
            "bind": [[1.0, 0.0, 0.0, 1.0, -bx, -by]],
            "profile": 7,
            "source": {"serializedVersion": 2.0, "x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0},
            "paint": {"serializedVersion": 2.0, "x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0},
            "registered": False,
            "registration": {"x": 1.0, "y": 1.0, "z": 0.0, "w": 0.0},
            "slice": 0,
            "line": None,
            "face": face_paths,
        }],
        "actions": {"Idle": make_idle(bx, by)},
    }

def save_shot(path, max_w=1400, quality=78):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    if w > max_w:
        im = im.resize((max_w, round(h * max_w / w)), Image.Resampling.LANCZOS)
    return save_webp(im, quality=quality)

def dump(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))

def main():
    js_path = PORTFOLIO / "app.js"
    original = js_path.read_text(encoding="utf-8")

    c0, c1, chars = parse_json_array(original, "const CHARACTER_DATA=")
    existing_roles = {c["role"] for c in chars}
    for c in chars:
        if c["role"] in EXISTING_SKILLS:
            c["skill"] = EXISTING_SKILLS[c["role"]]
    built = []
    for spec in NEW_CHARS:
        if spec["id"] in existing_roles:
            chars = [c for c in chars if c["role"] != spec["id"]]
        built.append(build_character(spec))
    chars.extend(built)

    sel = GAME / "Tools" / "EightCharacterGameplayIntegration" / "CharacterSelection.png"
    ingame = GAME / "Tools" / "EightCharacterGameplayIntegration" / "NewFourInGame.png"
    sel_url = save_shot(sel) if sel.exists() else None
    game_url = save_shot(ingame) if ingame.exists() else None
    print("shots", sel_url, game_url)

    p0, p1, project = extract_object(original, '{"id":"hangzhou-monopoly"')
    project["category"] = "个人独立开发 / Unity 围桌桌游"
    project["summary"] = "独立完成策划、角色美术与 Unity 实现。杭州主题经营对局：八角色可选，2–4 人围桌，四向 UI、动态立绘与城市棋盘。"
    project["tags"] = ["个人独立开发", "Unity 6 / URP", "八角色立绘", "四向 UI", "Shader", "语音 / 手势"]
    project["sourceLabel"] = "个人独立制作 / 2026.10"
    project["sourceNote"] = "个人独立制作。依据本地杭城大亨工程、八角色策划与选角对局记录整理；技能为已完成设定，对局先跑通用规则。"
    project["role"] = [
        "独立策划：杭州棋盘经营、机会/公益卡、2–4 人对局。",
        "八角色立绘与表情：分层蒙皮、待机呼吸、眨眼与说话口型。",
        "四向围桌 UI：座位朝向、资产 HUD、开局选角与回合反馈。",
        "风格化水面 Shader、棋盘底座与卡牌视觉。",
    ]
    project["notes"] = [
        "掷骰环游杭州地标周边经营点，购买、收租、升级店铺。",
        "八位角色均可选择，每局 2–4 人，角色不重复。",
        "语音播报驱动口型；手势可代理掷骰等操作。",
    ]
    project["breakdown"] = [
        {"title": "玩法", "text": "2–4 人围桌经营。掷骰前进，买地收租，集齐色组后升级店铺；快速局按净资产结算。", "evidence": "本地规则与 12 轮对局验证"},
        {"title": "美术", "text": "八名杭州主题角色立绘，分层动态、眨眼说话；棋盘、卡牌与四向面板统一古风配色。", "evidence": "工程立绘、选角与围桌实机"},
        {"title": "技术", "text": "Unity 6 / URP。uGUI 四向布局、角色蒙皮动画、水面 Shader，语音与手势接入通用对局。", "evidence": "monopoly-master 源码与预制体"},
    ]
    slots = project.get("slots") or []
    def upsert(key, label):
        for i, s in enumerate(slots):
            if s[0] == key:
                slots[i] = [key, label]
                return
        slots.append([key, label])
    if sel_url:
        upsert("cast", "八角色选人")
    if game_url:
        upsert("table", "围桌对局")
    for spec in NEW_CHARS:
        upsert(spec["slot"], spec["name"] + "动态形象")
    project["slots"] = slots

    b0, b1, media = parse_json_array(original, "const BUILTIN_MEDIA=")
    def add_media(key, url, name):
        media[:] = [m for m in media if m.get("key") != key]
        media.append({"key": key, "name": name, "type": "image/webp", "data": url})
    if sel_url:
        add_media("hangzhou-monopoly:cast", sel_url, "hangzhou-cast.webp")
    if game_url:
        add_media("hangzhou-monopoly:table", game_url, "hangzhou-table.webp")

    edits = [(c0, c1, dump(chars)), (p0, p1, dump(project)), (b0, b1, dump(media))]
    edits.sort(key=lambda x: x[0], reverse=True)
    out = original
    for a, b, rep in edits:
        out = out[:a] + rep + out[b:]

    replacements = {
        "四个角色动态形象对比": "八个角色动态形象对比",
        "同一动作，四种性格": "八种性格，同台亮相",
        "根据工程分层素材与动作曲线制作的网页预览，支持眨眼与说话口型；可在素材管理中替换为四人的实机视频。": "八名角色均来自独立制作的杭城大亨：分层立绘、待机呼吸、眨眼与说话口型。",
    }
    for old, new in replacements.items():
        if old not in out:
            print("WARN missing string:", old)
        else:
            out = out.replace(old, new)

    old_card = '<article class="character-card" style="--role-color:${c.color}"><div class="character-stage" data-role="${c.role}"><canvas aria-label="${c.name}动态形象"></canvas></div><h4>${c.name}</h4></article>'
    new_card = '<article class="character-card" style="--role-color:${c.color}"><div class="character-stage" data-role="${c.role}"><canvas aria-label="${c.name}动态形象"></canvas></div><h4>${c.name}</h4>${c.skill?`<p class="character-skill">${c.skill}</p>`:``}</article>'
    if old_card not in out:
        raise SystemExit("character card template missing")
    out = out.replace(old_card, new_card, 1)

    start = out.find("function openMonopoly(p){")
    end = out.find("function forestDeckHTML", start)
    if start < 0 or end < 0:
        raise SystemExit("openMonopoly missing")
    open_fn = r'''function openMonopoly(p){activeProject=p.id;$('#project-detail').innerHTML=`<div class="detail-content compact-project"><p class="project-category">${escapeHTML(p.category)}</p><h2>${escapeHTML(p.title)}</h2><p class="detail-summary">${escapeHTML(p.summary)}</p><div class="tags">${p.tags.map(t=>'<span>'+escapeHTML(t)+'</span>').join('')}</div>${characterCompareHTML()}${p.breakdown?`<div class="technical-breakdown">${p.breakdown.map(b=>`<article><h3>${escapeHTML(b.title)}</h3><p>${escapeHTML(b.text)}</p></article>`).join('')}</div>`:''}<h3 class="detail-gallery-heading">场景与界面</h3><div class="detail-gallery"><div class="gallery-slot"><div class="slot-visual">${visualHTML(p)}</div><p>棋盘全貌</p></div><div class="gallery-slot"><div class="slot-visual">${visualHTML(p,p.id+':cast')}</div><p>八角色选人</p></div><div class="gallery-slot"><div class="slot-visual">${visualHTML(p,p.id+':table')}</div><p>围桌对局</p></div><div class="gallery-slot"><div class="slot-visual">${visualHTML(p,p.id+':ui')}</div><p>房产明细 · 四向 UI</p></div></div><p class="source-note">${escapeHTML(p.sourceNote||'')}</p></div>`;if(!$('#project-dialog').open)$('#project-dialog').showModal();mountCharacterComparisons($('#project-dialog'))}

'''
    out = out[:start] + open_fn + out[end:]
    js_path.write_text(out, encoding="utf-8")
    print("app.js written, chars", len(chars))

    css_path = PORTFOLIO / "style.css"
    css = css_path.read_text(encoding="utf-8")
    if ".character-skill" not in css:
        needle = ".character-card h4{text-align:center;font-size:13px;font-weight:500;margin:10px 0 0;color:var(--role-color)}"
        if needle not in css:
            raise SystemExit("css h4 missing")
        css = css.replace(
            needle,
            needle + ".character-skill{text-align:center;font-size:11px;color:var(--muted);margin:4px 0 0}",
            1,
        )
        css_path.write_text(css, encoding="utf-8")
        print("css skill added")

    log = PORTFOLIO / "更新记录.md"
    text = log.read_text(encoding="utf-8")
    entry = """## 2026-10-27 — 杭城大亨八角色与独立制作介绍（本地待发布）

- 角色动态对比由四名补全为八名：新增西溪旅人、云栖创客、湖滨织锦师、钱江灯匠，沿用待机、眨眼与说话口型。
- 项目改为个人独立制作介绍，补充玩法、美术、技术要点，并加入选角与围桌对局画面。
- 按本人此前要求：未同步 GitHub、未发布云端。

"""
    if "杭城大亨八角色与独立制作介绍" not in text:
        lines = text.splitlines(True)
        if lines and lines[0].startswith("#"):
            text = lines[0] + "\n" + entry + "".join(lines[1:])
        else:
            text = entry + text
        log.write_text(text, encoding="utf-8")

    print("done")

if __name__ == "__main__":
    main()
