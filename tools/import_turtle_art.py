"""Add traceable source textures and actual scene crops to the Turtle Soup case study."""
from pathlib import Path
import hashlib
import json
import re
import shutil
from PIL import Image
from import_turtle_interfaces import ROOT, write_webp

UNITY = Path('D:/wly/unity/Turtle Soup')
output = ROOT / 'output/turtle-soup/art-breakdown'
output.mkdir(parents=True, exist_ok=True)
catalog_path = ROOT / 'assets/media/catalog.json'
catalog = json.loads(catalog_path.read_text(encoding='utf-8'))
code = (ROOT / 'app.js').read_text(encoding='utf-8')
match = re.search(r'^  (\{"id":"turtle-soup".*\}),$', code, re.M)
project = json.loads(match[1])
media_match = re.search(r'^const BUILTIN_MEDIA=(.*);$', code, re.M)
builtins = json.loads(media_match[1])
records = []

def add(key, title, source, crop=None):
    image = Image.open(source).convert('RGBA')
    original_size = image.size
    if crop:
        image = image.crop(tuple(round(value * size) for value, size in zip(crop, original_size * 2)))
    local = output / (key + '.png')
    image.save(local)
    # Transparent production textures are shown against the website's dark surface.
    bg = Image.new('RGBA', image.size, '#101923')
    bg.alpha_composite(image)
    image = bg.convert('RGB')
    image.thumbnail((1920, 1920))
    web, size = write_webp(image, 87)
    if not any(item['path'] == web for item in catalog['media']):
        catalog['media'].append(dict(path=web, type='image/webp', bytes=size, original='Turtle Soup / art-breakdown/' + local.name, width=image.width, height=image.height))
    image.thumbnail((720, 720))
    thumb, size = write_webp(image, 79)
    catalog['thumbnails'][web] = dict(src=thumb, bytes=size, width=image.width, height=image.height)
    asset_key = 'turtle-soup:' + key
    builtins[:] = [item for item in builtins if item['key'] != asset_key]
    builtins.append(dict(key=asset_key, name=key+'.webp', type='image/webp', data=web))
    records.append(dict(key=key, title=title, source=str(source), sourceSHA256=hashlib.sha256(source.read_bytes()).hexdigest(), originalSize=original_size, crop=crop, web=web, exported=str(local)))

add('ta-smoke-texture', '烟雾贴图 · 透明通道控制轮廓', UNITY/'Assets/SoupHouse/Opening/Smoke-v16/OriginalRimRetouched.png')
add('ta-flow-map', 'Flow Map · RG 通道驱动局部流向', UNITY/'Assets/SoupHouse/Opening/Textures/CurlFlowRG.png')
add('ta-ring-mask', '环形图案 · 刻痕与嵌线的输入', UNITY/'Assets/SoupHouse/Art/UI/Rings-v01/CenterRing-v01.png')
capture = json.loads((ROOT/'reports/turtle-soup-interfaces.json').read_text(encoding='utf-8'))
source_folder = Path((UNITY/'Captures/PortfolioInterfaces-20261027/latest.txt').read_text(encoding='utf-8').strip())
# Crops preserve actual Game View pixels; no visual effect is recreated here.
add('ta-engraving-detail', '木桌刻痕与环形铜线 · 实机局部', source_folder/'04-story-selection.png', (.32,.20,.68,.80))

def shot(key, title):
    return dict(key=key, title=title)
project['artGroups'] = [
    dict(title='场景与投影布局', text='当前场景运行画面：木桌、烛光、外围烟雾与四向阅读布局。', items=[shot('screen-03-registration','八席注册 · 围桌布局'),shot('screen-06-story-surface','汤面 · 场景化叙事界面')]),
    dict(title='烟雾 · 输入与最终效果', text='实际材质输入与开场画面对照。烟雾 Alpha 控制轮廓，RG 流向图驱动扰动与双相位流动。', items=[shot('ta-smoke-texture','烟雾贴图 · 透明轮廓'),shot('ta-flow-map','Flow Map · RG 流向'),shot('screen-01-opening','开场实机 · 烟雾与石屋')]),
    dict(title='材质化界面 · 图案与实机局部', text='环形图案经过刻痕 Shader 着色，与木桌合成凹槽、磨损亮边和铜色线条。右图为运行截图局部裁切。', items=[shot('ta-ring-mask','环形图案 · 输入素材'),shot('ta-engraving-detail','凹槽与铜线 · 实机放大')]),
    dict(title='四主题 · 同一视角对比', text='保持同一讨论界面与镜头，切换主题预设；对照烟雾、灯光、桌面与强调色。', items=[shot('screen-10-theme-Standard','标准'),shot('screen-10-theme-MildHorror','微恐'),shot('screen-10-theme-Horror','恐怖'),shot('screen-10-theme-Entertainment','娱乐')]),
]
# Keep the long interface archive downloadable; show selected milestones on the page.
selected = {'screen-04-story-selection','screen-05-mode-selection','screen-07-cooperation-rules','screen-08-cooperation-turn','screen-09-competition-turn','screen-12-success','screen-13-replay-01','screen-14-results'}
project['slots'] = [slot for slot in project['slots'] if slot[0] in selected]
project['sourceNote'] = '场景图采集于 2026-10-27，为当前场景运行截图；通过控制器切换界面、主题与结案演示状态。贴图来自工程实际材质，局部图由实机原图裁切。开场动图保留此前运行实录剪辑。'
code = code[:match.start(1)] + json.dumps(project,ensure_ascii=False,separators=(',',':')) + code[match.end(1):]
code = re.sub(r'^const BUILTIN_MEDIA=.*$',lambda _: 'const BUILTIN_MEDIA='+json.dumps(builtins,ensure_ascii=False,separators=(',',':'))+';',code,flags=re.M)
code = re.sub(r'^const MEDIA_THUMBS=.*$',lambda _: 'const MEDIA_THUMBS='+json.dumps(catalog['thumbnails'],ensure_ascii=False,separators=(',',':'))+';',code,flags=re.M)
(ROOT/'app.js').write_text(code,encoding='utf-8')
catalog_path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
scenes = [UNITY/'Assets/SoupHouse/Scenes/SoupHouseOpening.unity',UNITY/'Assets/SoupHouse/Scenes/SoupHouse.unity']
report = dict(captureUTC=capture['utc'], scenes=[dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in scenes], assets=records)
(ROOT/'reports/turtle-soup-art.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('Imported source textures and actual scene crop; provenance: reports/turtle-soup-art.json')
