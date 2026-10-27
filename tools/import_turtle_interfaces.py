"""Import a fresh Unity screen capture into downloadable PNGs and lazy portfolio images."""
from pathlib import Path
import argparse
import hashlib
import io
import json
import re
import shutil
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def write_webp(image, quality):
    buffer = io.BytesIO()
    image.save(buffer, 'WEBP', quality=quality, method=0)
    data = buffer.getvalue()
    filename = 'assets/media/' + hashlib.sha256(data).hexdigest()[:20] + '.webp'
    (ROOT / filename).write_bytes(data)
    return filename, len(data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('capture', type=Path)
    args = parser.parse_args()
    report = json.loads((args.capture / 'capture.json').read_text(encoding='utf-8'))
    if not (args.capture / 'status.txt').exists():
        raise ValueError('Capture has not completed; do not publish a partial interface set.')
    catalog_path = ROOT / 'assets/media/catalog.json'
    catalog = json.loads(catalog_path.read_text(encoding='utf-8'))
    script_path = ROOT / 'app.js'
    code = script_path.read_text(encoding='utf-8')
    project_match = re.search(r'^  (\{"id":"turtle-soup".*\}),$', code, re.M)
    project = json.loads(project_match[1])
    media_match = re.search(r'^const BUILTIN_MEDIA=(.*);$', code, re.M)
    builtins = [item for item in json.loads(media_match[1]) if not item['key'].startswith('turtle-soup:')]
    slots, imported = [], []
    output = ROOT / 'output/turtle-soup/current-interfaces'
    output.mkdir(parents=True, exist_ok=True)
    for page in report['pages']:
        title = page['title']
        for english, chinese in [('Standard', '常规主题'), ('MildHorror', '微恐主题'), ('Horror', '恐怖主题'), ('Entertainment', '娱乐主题')]:
            if title.endswith(' · ' + english):
                title = title[:-len(english)] + chinese
        source = args.capture / page['file']
        shutil.copyfile(source, output / source.name)
        image = Image.open(source).convert('RGB')
        image.thumbnail((1920, 1920))
        url, size = write_webp(image, 84)
        if not any(item['path'] == url for item in catalog['media']):
            catalog['media'].append({'path': url, 'type': 'image/webp', 'bytes': size,
                'original': 'Turtle Soup / current-interfaces/' + source.name,
                'width': image.width, 'height': image.height})
        image.thumbnail((720, 720))
        thumbnail, thumbnail_size = write_webp(image, 75)
        catalog['thumbnails'][url] = {'src': thumbnail, 'bytes': thumbnail_size,
                                      'width': image.width, 'height': image.height}
        key = 'screen-' + source.stem
        slots.append([key, title])
        builtins.append({'key': 'turtle-soup:' + key, 'name': source.stem + '.webp', 'type': 'image/webp', 'data': url})
        imported.append({**page, 'title': title, 'source': source.name, 'web': url, 'thumbnail': thumbnail})
        if source.stem == '01-opening':
            builtins.append({'key': 'turtle-soup:cover', 'name': 'turtle-current-opening.webp', 'type': 'image/webp', 'data': url})
    project['slots'] = slots
    project['previewKeys'] = ['turtle-opening']
    project['sourceNote'] = '界面图为当前场景运行截图，包含通过控制器切换的界面演示状态；开场动图为运行实录剪辑。'
    code = code[:project_match.start(1)] + json.dumps(project, ensure_ascii=False, separators=(',', ':')) + code[project_match.end(1):]
    code = re.sub(r'^const BUILTIN_MEDIA=.*$', lambda _: 'const BUILTIN_MEDIA=' + json.dumps(builtins, ensure_ascii=False, separators=(',', ':')) + ';', code, flags=re.M)
    code = re.sub(r'^const MEDIA_THUMBS=.*$', lambda _: 'const MEDIA_THUMBS=' + json.dumps(catalog['thumbnails'], ensure_ascii=False, separators=(',', ':')) + ';', code, flags=re.M)
    script_path.write_text(code, encoding='utf-8', newline='\n')
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding='utf-8')
    (output / 'capture.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    (ROOT / 'reports/turtle-soup-interfaces.json').write_text(json.dumps({'scene': report['scene'], 'utc': report['utc'], 'method': report['method'], 'pages': imported}, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# 当前场景界面截图', '', '来源：当前 Unity 场景 Play 模式屏幕输出；通过公开控制器切换界面与演示状态，不保存场景资产。', '',
             '| 界面 | PNG | 原始分辨率 |', '| --- | --- | --- |']
    lines += [f'| {p["title"]} | [{p["file"]}]({p["file"]}) | {p["width"]} × {p["height"]} |' for p in report['pages']]
    (output / 'README.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'Imported {len(imported)} current interfaces; native PNGs: {output}')


if __name__ == '__main__':
    main()
