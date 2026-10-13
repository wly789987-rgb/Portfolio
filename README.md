# Portfolio
# 王立焱 · Unity 技术美术个人站

包含美术作品展示与技术工具目录。美术区提供角色动态对比、卡牌浏览、视频播放与项目图片；技术区支持 Blender、ComfyUI、Unity 工具以及 GitHub 仓库链接。

## 文件

- `index.html`：网站入口。
- `style.css`：页面样式。
- `app.js`：交互、内置素材和本地内容管理。
- `assets/`：优化后的图片、视频与简历源文件。
- `使用说明.md`：内容管理、备份与素材来源说明。

这是无构建步骤的静态网站。将这些文件放在仓库根目录即可保留网站源码；若之后需要公开访问，可以使用支持静态文件的网站托管服务，以 `index.html` 为入口。

## 本地预览

在当前目录运行 `python -m http.server 8765`，再打开 `http://127.0.0.1:8765/`。

页面中的修改保存在当前浏览器。需要将编辑结果交付或换设备时，使用页脚“管理内容与素材”导出完整网页或备份。浏览器编辑不会自动提交到 GitHub。

仓库版保留素材源文件，省去重复的单文件网页、打包 ZIP 与预览截图。完整离线单文件仍保留在原交付文件夹。
## Software / Programming / Skills 展示

站尾“工具与能力”采用 Software 与 Programming 两块图标面板，以及 Skills 技能矩阵。提供悬停、键盘聚焦和相关作品入口。Programming 默认包含 C# 与材质节点工具，没有添加未经提供的语言或经验等级。

页脚管理入口中的“Software / Programming / Skills”支持每行一个名称，自行新增或删减；点击保存后保存在本地，内容备份与离线导出也会保留。软件与语言图标可按已知名称匹配，其他名称使用通用图形。

布局参考 https://maciejsojka.dev/ 的同名分组，结合本站深色配色重新实现。部分软件标志来自 Devicon（https://github.com/devicons/devicon），许可证在 assets/icons/DEVICON-LICENSE.txt；其余为本站 SVG 图形。
