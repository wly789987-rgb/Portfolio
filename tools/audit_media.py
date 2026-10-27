"""Rebuild a media size/dimension report. Requires Pillow; does not alter sources."""
from pathlib import Path
import csv
import json
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def main():
    catalog = json.loads((ROOT / 'assets/media/catalog.json').read_text(encoding='utf-8'))
    previews = json.loads((ROOT / 'assets/previews/catalog.json').read_text(encoding='utf-8'))
    report_dir = ROOT / 'reports'
    report_dir.mkdir(exist_ok=True)
    rows = []
    for item in catalog['media']:
        if not item['type'].startswith('image/'):
            continue
        path = ROOT / item['path']
        with Image.open(path) as image:
            thumb = catalog['thumbnails'][item['path']]
            rows.append({'source': item['original'], 'file': item['path'],
                         'width': image.width, 'height': image.height,
                         'bytes': path.stat().st_size,
                         'thumbnail_bytes': (ROOT / thumb['src']).stat().st_size,
                         'thumbnail_width': thumb['width'], 'thumbnail_height': thumb['height']})
    rows.sort(key=lambda r: r['bytes'], reverse=True)
    with (report_dir / 'media-audit.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    script_bytes = (ROOT / 'app.js').stat().st_size
    lines = ['# 媒体体积检查', '',
             f'- 原主脚本：55,384,381 字节；当前主脚本：{script_bytes:,} 字节。',
             f'- 检查独立图片 {len(rows)} 张，原始体积合计 {sum(r["bytes"] for r in rows):,} 字节。',
             '- 原图保留。列表预览最长边不超过 720 px，详情点开放大时使用原图。',
             '- GIF 为短片段：原作品视频约 4 秒；汤之馆四套氛围约 6.4 秒，按原截图序列 5 fps 合成；开场展示剪辑约 33.3 秒，缩短单蜡烛等待，保留原始完整 62.72 秒版本。默认静态封面，点击才下载播放。',
             '- 首屏不下载视频、GIF 或简历 PDF；四人角色素材滚动到附近后才加载。',
             '- 浏览器 Cache Storage 按需缓存最多 128 个带内容摘要的图片/GIF URL；没有缓存权限时回退到普通请求。',
             '- 首页、脚本、样式仍由普通浏览器 HTTP 缓存处理，没有离线 Service Worker，不会锁住旧版首页。',
             '- 主脚本和样式使用新版本查询参数；媒体文件名随内容摘要变化。', '',
             '## 图片体积前十五项', '',
             '| 原文件 | 分辨率 | 原图 KB | 缩略图 KB |', '| --- | --- | ---: | ---: |']
    for r in rows[:15]:
        lines.append(f'| {r["source"]} | {r["width"]} × {r["height"]} | {r["bytes"]/1000:.1f} | {r["thumbnail_bytes"]/1000:.1f} |')
    lines += ['', '## GIF 预览', '', '| 项目 | 体积 KB | 帧数 | 原视频起点 |', '| --- | ---: | ---: | ---: |']
    for r in previews:
        lines.append(f'| {r["name"]} | {r["bytes"]/1000:.1f} | {r["frames"]} | {r["start"]} 秒 |')
    lines += ['', '## 完整视频对应', '',
              '- 太阳系漫游 → 简历「安吉天文场馆」（已由本人确认）。',
              '- 寻找外星人 → 简历「仙女座星系」（已由本人确认）；保留该项目的 AI 视频链接。',
              '- NBA 元宇宙 → 简历中的项目完整视频和投篮视频，分别标注。',
              '- 邪恶勇者使用原作品集已有完整视频链接。',
              '- 黑暗森林三段效果使用站内原视频文件作为完整视频链接。',
              '- 简历中的中国移动品牌视频暂无对应站内项目，本次未混入其他项目。', '',
              '完整图片清单：`reports/media-audit.csv`。运行 `python tools/audit_media.py` 可更新。', '']
    (ROOT / '媒体体积检查.md').write_text('\n'.join(lines), encoding='utf-8')
    print(f'Images: {len(rows)}, GIFs: {len(previews)}, script: {script_bytes:,} bytes')


if __name__ == '__main__':
    main()
