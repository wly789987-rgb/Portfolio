import json, re, subprocess
from pathlib import Path
from PIL import Image
import imageio_ffmpeg

root=Path(__file__).resolve().parents[1]
source=Path(r'D:\wly\unity\Turtle Soup\Captures\OpeningGif-20261029')
assert (source/'complete.txt').exists(), 'Recording is incomplete'
frames=sorted(source.glob('*.png'))
fps=len(frames)/34
out=root/'assets/previews/turtle-opening-20261029.gif'
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-y','-framerate',str(fps),'-i',str(source/'%04d.png'),'-filter_complex','scale=720:-2:flags=lanczos,split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4','-loop','0',str(out)],check=True)
poster=root/'assets/previews/turtle-opening-20261029.webp'
Image.open(frames[min(len(frames)-1,int(fps*9))]).convert('RGB').save(poster,'WEBP',quality=88)
with Image.open(out) as im:
    record=dict(name='turtle-opening-current',title='汤之馆 · 当前开场实录',src=out.relative_to(root).as_posix(),poster=poster.relative_to(root).as_posix(),frames=im.n_frames,seconds=34,fps=round(fps,2),bytes=out.stat().st_size,source=str(source))
path=root/'app.js';s=path.read_text('utf8')
m=re.search(r'^const GIF_PREVIEWS=(.*);$',s,re.M);data=json.loads(m[1]);data['turtle-opening-current']=record
s=s[:m.start(1)]+json.dumps(data,ensure_ascii=False,separators=(',',':'))+s[m.end(1):]
s=s.replace("if(p.id==='turtle-soup')return visualHTML(p,p.id+':current-discussion')+'<span class=\"play-gif-badge\">当前场景 · 2026.10.29</span>';", "if(p.id==='turtle-soup')return gifAutoplayHTML(GIF_PREVIEWS['turtle-opening-current'],p.title)+'<span class=\"play-gif-badge\">开场实录 · GIF</span>';")
s=s.replace("<div class=\"detail-hero\">${visualHTML(p,'turtle-soup:current-discussion',true)}</div>","<div class=\"detail-hero\">${gifPreviewHTML(GIF_PREVIEWS['turtle-opening-current'],p.title)}</div>")
needle="${topic('02','迷雾开场"
i=s.index(needle);j=s.index("${topic('03'",i)
section=s[i:j]
section=section.replace("${topic('02'", "<figure class=\"turtle-motion\"><figcaption>当前场景开场实录 · 34 秒 · 2026-10-29</figcaption>${gifPreviewHTML(GIF_PREVIEWS['turtle-opening-current'],'汤之馆 · 迷雾、石屋与烛光开场')}</figure>\n${topic('02'",1)
s=s[:i]+section+s[j:]
path.write_text(s,encoding='utf8')
path=root/'index.html';s=path.read_text('utf8').replace('app.js?v=20261029-current-scene','app.js?v=20261029-opening-gif');path.write_text(s,encoding='utf8')
path=root/'assets/previews/catalog.json';data=json.loads(path.read_text('utf8'));data=[x for x in data if x.get('name')!=record['name']]+[record];path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(record,ensure_ascii=False))
