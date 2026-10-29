"""Refresh the local case study from verified 2026-10-29 Unity captures."""
import json
import re
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
GAME = Path(r'D:\wly\unity\Turtle Soup')
script = ROOT / 'app.js'
code = script.read_text(encoding='utf-8')
match = re.search(r'^  (\{"id":"turtle-soup".*\}),$', code, re.M)
p = json.loads(match[1])
summary = '个人独立制作的 Unity 多人围桌推理体验。以木桌、烛光、流动烟雾与墨石铜边铭板统一场景，串联八席交互、AI 主持问答、四向真相揭晓与结算。'
p.update(summary=summary, previewKeys=[], sourceNote='画面更新于 2026-10-29：汤面与讨论图由当前 SoupHouseOpening 场景 Play 模式相机以 1920×1080 重新采集；开场、揭晓和结算图来自同日项目采集记录。讨论图为控制器切换的演示状态。AI 主持、语音与手势识别来自 WorkflowAgent / AiLinker SDK；场景、界面、Shader、流程和规则校验由个人实现。')
p['breakdown'] = [x for x in p.get('breakdown',[]) if '主题' not in x['title']]
p['artGroups'] = [x for x in p.get('artGroups',[]) if '主题' not in x['title']]
sources = {
 'current-opening': ('Captures/PortfolioInterfaces-20261027/20261029-184230/01-opening.png', '迷雾石屋 · 当前开场'),
 'current-surface': ('Captures/PortfolioCurrent-20261029/surface.png', '汤面 · 四向叙事与插画'),
 'current-discussion': ('Captures/PortfolioCurrent-20261029/discussion.png', '共同讨论 · 八席操作与四向线索'),
 'current-reveal': ('Captures/RevealUI-v2/reveal-v2-final.png', '真相揭晓 · 五幕插画与四向阅读'),
 'current-results': ('Captures/ResultsPlaque-v1/results-edge-layout.png', '结算 · 四向墨石铜边铭板'),
}
builtin_match = re.search(r'^const BUILTIN_MEDIA=(.*);$', code, re.M)
builtins = json.loads(builtin_match[1])
builtins = [x for x in builtins if not x['key'].startswith('turtle-soup:current-') and x['key']!='turtle-soup:cover']
report = []
for key,(source,title) in sources.items():
    image = Image.open(GAME/source).convert('RGB')
    image.thumbnail((1920,1080))
    url = 'assets/media/turtle-20261029-'+key+'.webp'
    image.save(ROOT/url, 'WEBP', quality=88, method=6)
    item = dict(key='turtle-soup:'+key,name=Path(url).name,type='image/webp',data=url)
    builtins.append(item)
    if key=='current-discussion': builtins.append(dict(item,key='turtle-soup:cover'))
    report.append(dict(key=key,source=str(GAME/source),url=url,title=title))
p['slots'] = [[key,title] for key,(_,title) in sources.items()]
p['taProcess']['pdf'] = ''
code = code[:match.start(1)] + json.dumps(p,ensure_ascii=False,separators=(',',':')) + code[match.end(1):]
code = re.sub(r'^const BUILTIN_MEDIA=.*;$',lambda _: 'const BUILTIN_MEDIA='+json.dumps(builtins,ensure_ascii=False,separators=(',',':'))+';',code,flags=re.M)
start = code.index('function openTurtleSoup(p)')
end = code.index('function openProject(id)',start)
renderer = '''function openTurtleSoup(p){activeProject=p.id;
const topic=(n,title,text,items)=>`<section class="turtle-topic" aria-labelledby="turtle-topic-${n}"><p class="eyebrow">TECHNICAL ART / ${n}</p><h3 id="turtle-topic-${n}">${title}</h3><p class="turtle-art-description">${text}</p>${turtleTopicMediaHTML(p,items)}</section>`;
$('#project-detail').innerHTML=`<div class="detail-hero">${visualHTML(p,'turtle-soup:current-discussion',true)}</div><div class="detail-content turtle-case-study"><p class="project-category">${escapeHTML(p.category)}</p><h2>${escapeHTML(p.title)}</h2><p class="detail-summary">${escapeHTML(p.summary)}</p><div class="tags">${p.tags.map(tag=>'<span>'+escapeHTML(tag)+'</span>').join('')}</div><p class="turtle-art-description">从雾中石屋进入围桌推理，再以插画揭晓和四向铭板完成复盘。个人负责视觉拆解、素材落地、实时效果、交互界面与 Unity 流程实现。</p>
${topic('01','统一场景 · 木桌、烛光与四向阅读','以深色木桌承载叙事，铜色刻线与烛光建立视觉层次，外围烟雾围合桌面。故事插画置于中央，正文面向四侧展开；讨论阶段将八席操作区、四向线索铭板和中央计时组织在同一桌面中。',[['current-surface','汤面 · 当前四向叙事画面'],['current-discussion','讨论 · 八席操作与墨石线索铭板']])}
${topic('02','迷雾开场 · 从石屋进入桌面','用石屋、流动雾层和暖光建立开场气氛。烟雾轮廓与 RG 流向输入分开控制，C# 编排镜头、显隐和点灯；进入桌面后，动态集中在外围烟雾与烛光，让中央文字保持可读。',[['current-opening','开场 · 2026-10-29 当前场景采集'],['ta-flow-map','制作输入 · RG 流向图']])}
${topic('03','推理交互 · 线索、语音与 AI 主持','每席提供提问、提示、真相与跳过入口，四向铭板同步呈现公共线索。项目接入 WorkflowAgent / AiLinker SDK 完成 AI 主持、语音与手势能力，Unity 负责请求状态、次数和规则校验；把识别结果接到可读的界面反馈与游戏流程。',[['current-discussion','推理桌面 · 线索与行动入口']])}
${topic('04','真相揭晓 · 五幕插画与四向字幕','揭晓阶段将叙事插画放回桌面中央，四侧独立排布标题、正文、幕序与继续入口。五幕内容按页切换插画与文字，烟雾柔化画面边缘，铜边面板延续讨论界面的材质语言。',[['current-reveal','当前揭晓界面 · 插画、幕序与四向文字']])}
${topic('05','结算复盘 · 墨石铭板与故事之门','结束后用四向墨石铜边铭板展示真相还原度与返回入口，中央保留故事之门。铭板、木桌和边缘烟雾保持统一，信息分别朝向四侧，便于围桌玩家阅读。',[['current-results','当前结算界面 · 四向还原度与返回入口']])}
<details class="turtle-extra"><summary>制作方法与个人职责</summary><div class="technical-breakdown"><article><h3>素材与材质</h3><p>拆分插画、装饰、可编辑文字和命中区域，以自定义 Shader 实现烟雾流动、木桌刻痕与烛火反馈。</p></article><article><h3>场景与交互</h3><p>以 C# 状态控制串联入席、选案、讨论、揭晓和结算；世界空间画布组织四向阅读与八席操作。</p></article><article><h3>迭代工具</h3><p>ArtPass 与 Builder 统一素材导入、材质引用和界面布局，通过场景采集核对实际效果。</p></article></div></details><p class="source-note">${escapeHTML(p.sourceNote)}</p></div>`;if(!$('#project-dialog').open)$('#project-dialog').showModal()}

'''
code=code[:start]+renderer+code[end:]
# Always resolve this curated case study from source, including browsers with an older saved summary.
code=code.replace("function projectData(){return BASE_PROJECTS.map(p=>({...p,...state.projects.find(x=>x.id===p.id)}))}","function projectData(){return BASE_PROJECTS.map(p=>p.id==='turtle-soup'?p:({...p,...state.projects.find(x=>x.id===p.id)}))}")
code=code.replace("function projectCoverHTML(p){", "function projectCoverHTML(p){\n  if(p.id==='turtle-soup')return visualHTML(p,p.id+':current-discussion')+'<span class=\"play-gif-badge\">当前场景 · 2026.10.29</span>';")
script.write_text(code,encoding='utf-8',newline='\n')
(ROOT/'reports/turtle-current-20261029.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
index=ROOT/'index.html'
html=index.read_text(encoding='utf-8').replace('src="app.js"','src="app.js?v=20261029-current-scene"')
index.write_text(html,encoding='utf-8',newline='\n')
print('Updated case study and',len(sources),'current scene images')
