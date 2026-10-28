"""Curate the supplied TA PDF into readable process notes and source-labelled comparisons."""
from pathlib import Path
import json,re,hashlib,io,shutil
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
UNITY=Path('D:/wly/unity/Turtle Soup')
PDF=UNITY/'output/portfolio-ta/汤之馆-AI赋能技术美术-作品集.pdf'
code=(ROOT/'app.js').read_text(encoding='utf-8')
m=re.search(r'^  (\{"id":"turtle-soup".*\}),$',code,re.M);p=json.loads(m[1])
catalog_path=ROOT/'assets/media/catalog.json';catalog=json.loads(catalog_path.read_text(encoding='utf-8'))
media=json.loads(re.search(r'^const BUILTIN_MEDIA=(.*);$',code,re.M)[1]);records=[]
def encode(im,q):
 b=io.BytesIO();im.save(b,'WEBP',quality=q,method=4);data=b.getvalue();path='assets/media/'+hashlib.sha256(data).hexdigest()[:20]+'.webp';(ROOT/path).write_bytes(data);return path,len(data)
for key,path,label in [
 ('ta-concept-opening','Docs/Art/Concepts/souphouse-opening-first-shot-v01.png','AI 开场概念 · 视觉探索，非实机'),
 ('ta-concept-selection','Docs/Art/Concepts/souphouse-mystery-selection-v01.png','AI 选案概念 · 多故事探索，非实机'),
 ('ta-concept-reading','Docs/Art/Concepts/汤之馆后续场景-v01/03-story-introduction.png','AI 汤面概念 · 单视角视觉探索，非实机'),
 ('ta-reveal-illustration','Captures/RevealIllustrations-v1/RevealIllustration-02.png','五幕回放第二幕 · 已有运行验收截图')]:
  src=UNITY/path;im=Image.open(src).convert('RGB');im.thumbnail((1920,1920));url,size=encode(im,86)
  if not any(i['path']==url for i in catalog['media']):catalog['media'].append(dict(path=url,type='image/webp',bytes=size,original=path,width=im.width,height=im.height))
  im.thumbnail((720,720));thumb,n=encode(im,77);catalog['thumbnails'][url]=dict(src=thumb,bytes=n,width=im.width,height=im.height)
  asset='turtle-soup:'+key;media=[i for i in media if i['key']!=asset];media.append(dict(key=asset,name=key+'.webp',type='image/webp',data=url));records.append(dict(key=key,source=path,caption=label,sha256=hashlib.sha256(src.read_bytes()).hexdigest()))
pdf_path='assets/media/'+hashlib.sha256(PDF.read_bytes()).hexdigest()[:20]+'.pdf';shutil.copyfile(PDF,ROOT/pdf_path)
p['role']=['视觉与技术拆解：确定石屋、迷雾、烛光的风格约束，划分贴图、Shader、文字与交互层。','AI 素材落地：筛选概念方向，将生成图转成独立素材、材质参数与可编辑界面。','实时实现与工具：编排开场和交互反馈，制作 ArtPass、Builder 与预览采集工具。']
p['taProcess']={
 'intro':'以 AI 扩展视觉探索，再把确认的方向拆成引擎原生资产、可调参数与交互状态。技术美术负责在氛围、可读性和运行约束之间做取舍。',
 'workflow':[
 ['视觉约束','明确俯视投影、八席围桌、中央留白与风格锚点。'],['AI 概念探索','生成构图与氛围变体，筛选可落地的视觉方向。'],['技术拆解','拆分纹理、透明层、可编辑文字、Shader 与输入区域。'],['实时重建','用 UV 扰动、状态参数与 C# 时序重建动态表现。'],['工具化接入','以 ArtPass 统一导入、材质和布局，保留 Builder 重建路径。'],['验证与迭代','通过阶段截图、重复安装与隔离计数检查修改结果。']],
 'decisions':[['氛围服从阅读','动态变化主要留在边缘烟雾、灯光和烛焰，中央信息保持稳定；四向文字使用引擎文字系统重建。'],['反馈服从状态','停留、取消、确认分别驱动显现、进度与溶解参数；把规整进度圈演进为融入木桌的烟缕残印。'],['资产保持可编辑','插画、装饰、标题编号与命中区域分层，生成图不承担整张交互界面；修改素材时可重新安装与检查。']],
 'evidence':[['稳态面板刷新','200 → 0 次','100 轮单面板 Controller / ProjectedStyle 刷新的几何脏标记。'],['空闲悬停图形','100 → 0 次','100 次空闲透明 Hold.Update 的几何脏标记。'],['重复美术安装','1242 → 1242','连续执行两次安装的 Transform 数量，检查是否重复堆积对象。']],
 'scope':'依据 2026-10-27 修复记录与历史美术安装记录。以上为特定条件下的隔离检查，不代表 FPS、Draw Call 或 GPU 耗时改善；目标设备的帧率、Overdraw 与投影亮度仍待实测。本轮网页整理未重新运行 Unity。',
 'pdf':pdf_path}
newgroups=[
 dict(title='从概念到实时 · 开场氛围',text='保留雾中石屋与中央留白的方向，将雾的轮廓、流动和散开拆成参数；两图分别是 AI 概念与 Unity 运行画面。',items=[dict(key='ta-concept-opening',title='AI 开场概念 · 非实机'),dict(key='screen-01-opening',title='Unity 开场 · 2026-10-27 运行截图')]),
 dict(title='从生成图到可编辑界面 · 选案',text='从多故事概念探索收敛到当前原型；插画、文字与交互区域分层，当前运行版本仅开放 SH001。',items=[dict(key='ta-concept-selection',title='AI 选案概念 · 多故事探索，非实机'),dict(key='screen-04-story-selection',title='Unity 选案 · 当前原型，仅开放 SH001')]),
 dict(title='从单视角到四向叙事 · 汤面与回放',text='概念图提供氛围参考，运行界面重新组织可编辑四向文字；五幕回放图来自后续已有验收记录，版本分别标注。',items=[dict(key='ta-concept-reading',title='AI 汤面概念 · 非实机'),dict(key='screen-06-story-surface',title='Unity 四向汤面 · 2026-10-27 采集'),dict(key='ta-reveal-illustration',title='五幕回放第二幕 · 后续运行验收截图')])]
p['artGroups']=[g for g in p.get('artGroups',[]) if not g['title'].startswith(('从概念','从生成','从单视角'))]+newgroups
code=code[:m.start(1)]+json.dumps(p,ensure_ascii=False,separators=(',',':'))+code[m.end(1):]
for name,value in [('BUILTIN_MEDIA',media),('MEDIA_THUMBS',catalog['thumbnails'])]:code=re.sub(r'^const '+name+r'=.*$',lambda _,n=name,v=value:'const '+n+'='+json.dumps(v,ensure_ascii=False,separators=(',',':'))+';',code,flags=re.M)
(ROOT/'app.js').write_text(code,encoding='utf-8');catalog_path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'reports/turtle-ta-pdf-import.json').write_text(json.dumps(dict(pdf=str(PDF),pdfSHA256=hashlib.sha256(PDF.read_bytes()).hexdigest(),assets=records,evidenceDocs=['Docs/Reviews/2026-10-27-selected-fixes.md','Docs/Art/汤之馆-场景素材与优化-v01.md']),ensure_ascii=False,indent=2),encoding='utf-8')
print('Imported 4 source-labelled images, 3 comparison groups, process notes, evidence and PDF download.')
