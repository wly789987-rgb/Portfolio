// Keep real project text in the initial HTML, even when JavaScript/media is unavailable.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const code = fs.readFileSync(path.join(root, 'app.js'), 'utf8');
const start = code.indexOf('const BASE_PROJECTS = ');
const end = code.indexOf('const BUILTIN_MEDIA=', start);
const projects = vm.runInNewContext(code.slice(start, end) + '\nBASE_PROJECTS');
const escape = value => String(value).replace(/[&<>"']/g, x => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[x]));
const cards = projects.map((p, i) => `<article class="project-card static-project" data-project="${p.id}">
  <a class="project-open" data-open="${p.id}" href="#static-${p.id}" aria-label="查看${escape(p.title)}项目详情"><div class="project-art"><svg viewBox="0 0 900 560" aria-hidden="true"><path d="M60 440 300 160 450 330 620 100 840 440Z" fill="#142b38" stroke="#527887"/><circle cx="690" cy="145" r="64" fill="none" stroke="#7ba6b3"/><path d="M60 470h780M450 60v430" stroke="#284956"/><text x="80" y="120" fill="#9bcbd7" font-size="48" font-family="sans-serif">${String(i + 1).padStart(2, '0')}</text></svg></div><span class="project-open-arrow" aria-hidden="true">↗</span></a>
  <div class="project-info"><p class="project-category">${escape(p.category)}</p><h3 id="static-${p.id}"><a data-open="${p.id}" href="#static-${p.id}">${escape(p.title)}</a></h3><p class="project-summary">${escape(p.summary)}</p><div class="tags">${p.tags.map(t => `<span>${escape(t)}</span>`).join('')}</div><details class="static-project-details"><summary>项目内容</summary><ul>${p.role.map(t => `<li>${escape(t)}</li>`).join('')}</ul></details></div>
</article>`).join('\n');
const filename = path.join(root, 'index.html');
let html = fs.readFileSync(filename, 'utf8');
const block = '<!-- static-projects:start -->\n' + cards + '\n<!-- static-projects:end -->';
if (html.includes('<!-- static-projects:start -->')) html = html.replace(/<!-- static-projects:start -->[\s\S]*?<!-- static-projects:end -->/, () => block);
else html = html.replace('<div id="project-grid" class="project-grid"></div>', () => '<div id="project-grid" class="project-grid">' + block + '</div>');
fs.writeFileSync(filename, html);
console.log(`Built ${projects.length} static project cards`);
