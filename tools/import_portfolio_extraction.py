"""Import project-only original portfolio images, excluding biography and duplicate backgrounds."""
from pathlib import Path
import json, re, hashlib, io
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path('C:/Users/ailinker-intel/Documents/Codex/2026-10-12/x/outputs/作品集图片提取-2026')
manifest=json.loads((SOURCE/'图片清单.json').read_text(encoding='utf-8-sig'))
images={item['id']:item for item in manifest['images']}
projects=json.loads((ROOT/'output/projects-before-extract.json').read_text(encoding='utf-8'))
groups={
 'evil-hero': [('P04-01','线下围桌试玩'),('P05-01','主角与武器 · 多视图'),('P05-02','怪物与装备 · 多视图'),('P06-01','森林战场 · 多路线路径'),('P06-02','熔岩战场 · 首领区域'),('page-05','角色资产 · 原作品集制作标注'),('page-06','关卡场景 · 原作品集制作标注')],
 'dark-forest':[('page-08','卡牌体系 · 原作品集制作标注')],
 'nba': [('P09-02','元宇宙主场景'),('P10-06','活动与内容入口'),('P10-05','虚拟角色展示'),('P10-04','角色试装界面'),('P10-07','服饰选择界面'),('P11-04','投篮交互 · 主场景'),('P11-05','特效与装扮 · 移动端展示'),('P11-06','虚拟角色 · 移动端展示'),('P12-01','八款角色服饰 · 整体展示'),('P12-02','角色服饰 · 造型一'),('P12-03','角色服饰 · 造型二'),('P12-04','角色服饰 · 造型三'),('P12-05','角色服饰 · 造型四'),('P13-01','角色服饰 · 组合展示'),('P13-02','数字藏品 · 陈列场景'),('P13-03','藏品展示 · 材质与灯光'),('P14-01','蓝色能量特效 · 连续状态'),('P14-02','金色环形特效 · 连续状态'),('P14-03','金色环形特效 · 展示画面'),('P14-04','蓝色能量特效 · 展示画面'),('P15-01','道具与服饰 · 资源列表'),('P15-02','图标与内容资源'),('P15-03','场景资产 · 工程资源'),('P15-04','角色资源 · 资产列表'),('P15-05','项目视觉内容 · 汇总')],
 'solar-vr':[('P17-01','地球材质 · Unity 工程界面'),('P17-02','太阳系 · 天体与轨道'),('P18-01','太阳系场馆 · 空间布局'),('P18-02','太阳 · 表面与粒子效果'),('P18-03','黑洞 · 空间特效'),('P19-01','场馆通道 · 霓虹材质'),('P19-02','天体装置 · 环形结构'),('P19-03','知识展区 · 场景陈列')],
 'alien-vr':[('P20-01','地球与空间站 · 项目场景'),('P21-01','线下装置 · 阵列结构'),('P21-02','线下场馆 · 视觉环境'),('P21-03','线下场馆 · 建筑外景'),('P21-04','场馆内部 · 体验空间'),('P22-01','探索空间 · 场景全貌'),('P22-02','探索空间 · 能量装置'),('P22-03','座舱 · 交互视角'),('P23-01','空间设施 · 场景构图'),('P23-02','通道 · 空间关系'),('P23-03','能量区域 · 灯光与氛围')],
 'hologram':[('P24-01','数字人 · Unity 展示画面'),('P24-02','全息舱 · 线下设备展示'),('page-24','数字人展示 · 原作品集说明')],
 'water':[('P25-01','风格化水体 · Unity 场景画面'),('page-25','水体 Shader · 原作品集制作标注')],
}
code=(ROOT/'app.js').read_text(encoding='utf-8')
catalog_path=ROOT/'assets/media/catalog.json';catalog=json.loads(catalog_path.read_text(encoding='utf-8'))
m=re.search(r'^const BUILTIN_MEDIA=(.*);$',code,re.M);builtins=json.loads(m[1]);records=[]
def encode(image,quality):
 b=io.BytesIO();image.save(b,'WEBP',quality=quality,method=4);data=b.getvalue();name='assets/media/'+hashlib.sha256(data).hexdigest()[:20]+'.webp';(ROOT/name).write_bytes(data);return name,len(data)
for project in projects:
 if project['id'] not in groups:continue
 slots=[]
 for ident,title in groups[project['id']]:
  source=SOURCE/('页面预览/'+ident+'.jpg') if ident.startswith('page-') else SOURCE/images[ident]['file']
  image=Image.open(source).convert('RGBA');bg=Image.new('RGBA',image.size,'#0c1119');bg.alpha_composite(image);image=bg.convert('RGB');image.thumbnail((1920,1920))
  web,size=encode(image,86)
  if not any(item['path']==web for item in catalog['media']):catalog['media'].append(dict(path=web,type='image/webp',bytes=size,original='作品集图片提取-2026/'+str(source.relative_to(SOURCE)),width=image.width,height=image.height))
  image.thumbnail((720,720));thumb,thumbsize=encode(image,76);catalog['thumbnails'][web]=dict(src=thumb,bytes=thumbsize,width=image.width,height=image.height)
  key='extract-'+ident.lower();fullkey=project['id']+':'+key;builtins=[item for item in builtins if item['key']!=fullkey];builtins.append(dict(key=fullkey,name=ident+'.webp',type='image/webp',data=web));slots.append([key,title])
  records.append(dict(project=project['id'],id=ident,title=title,source=str(source.relative_to(SOURCE)),sourceSHA256=hashlib.sha256(source.read_bytes()).hexdigest(),web=web,bytes=size))
 # Preserve existing playable clips; replace older duplicate image boards with individual originals.
 project['slots']=slots+([slot for slot in project['slots'] if slot[0]=='gameplay'] if project['id']=='evil-hero' else [])
 note='项目图片补充自《王立焱作品集-2026》提取素材；标注页保留原作品集说明，线下照片与引擎画面分别标明。'
 project['sourceNote']=project.get('sourceNote','')+' '+note
a=code.index('const BASE_PROJECTS = ');b=code.index('const BUILTIN_MEDIA=',a);code=code[:a]+'const BASE_PROJECTS = '+'[\n  '+',\n  '.join(json.dumps(p,ensure_ascii=False,separators=(',',':')) for p in projects)+'\n];\n'+code[b:]
code=re.sub(r'^const BUILTIN_MEDIA=.*$',lambda _: 'const BUILTIN_MEDIA='+json.dumps(builtins,ensure_ascii=False,separators=(',',':'))+';',code,flags=re.M)
code=re.sub(r'^const MEDIA_THUMBS=.*$',lambda _: 'const MEDIA_THUMBS='+json.dumps(catalog['thumbnails'],ensure_ascii=False,separators=(',',':'))+';',code,flags=re.M)
code=code.replace('${forestShowcaseHTML(true,start)}</div>',"${forestShowcaseHTML(true,start)}${legacyGalleryHTML(projectData().find(p=>p.id==='dark-forest'))}</div>")
(ROOT/'app.js').write_text(code,encoding='utf-8');catalog_path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'reports/portfolio-extraction-import.json').write_text(json.dumps(dict(source=str(SOURCE),count=len(records),records=records),ensure_ascii=False,indent=2),encoding='utf-8')
print('Imported',len(records),'project images:',{k:len(v) for k,v in groups.items()})
