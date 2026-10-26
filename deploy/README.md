# 一键发布到阿里云

完成下面的一次性连接后，日常更新只需在 GitHub 点击：

**Actions → 发布个人站 → Run workflow → deploy → Run workflow**。

默认发布 main 中选定运行时的提交，不会因为普通 push 自动上线。需要发布指定历史版本时填写完整 40 位提交号；该提交必须在 main 历史中。

## 一次性连接（在阿里云远程终端执行）

当前网站必须已通过 HTTPS 正常运行，Nginx 配置文件是 `/etc/nginx/conf.d/wangliyan.conf`，其中网站根目录为 `/usr/share/nginx/wangliyan`。初始化会备份配置，复制当前网站作为初始回退版本，然后将 Nginx 根目录切换到 `/srv/portfolio/current`。证书和续期任务保持现有配置。

下面命令需要 root，仅首次运行。会创建专用账号 `portfolio-deploy` 和一对部署密钥；该密钥只能发布、回退此站点，没有 root 或 sudo 权限。初始化失败后先保留输出排查，不要反复重跑。

```bash
mkdir -p /root/portfolio-publish-setup
curl -fL https://raw.githubusercontent.com/wly789987-rgb/Portfolio/main/deploy/setup-server.sh -o /root/portfolio-publish-setup/setup-server.sh
curl -fL https://raw.githubusercontent.com/wly789987-rgb/Portfolio/main/deploy/release.py -o /root/portfolio-publish-setup/release.py
ssh-keygen -t ed25519 -N '' -C 'Portfolio GitHub Actions' -f /root/portfolio-actions-key
bash /root/portfolio-publish-setup/setup-server.sh /root/portfolio-actions-key.pub
```

逐条执行，上一条成功后再继续。如果 key 文件已存在，不要确认覆盖，先核对之前的配置。

看到 `Setup complete` 后，最后一行 `47.111.109.82 ssh-ed25519 ...` 是服务器公钥，下一步使用。

## GitHub 添加两个 Secrets

打开本仓库 **Settings → Secrets and variables → Actions → New repository secret**。

| 名称 | 内容 |
| --- | --- |
| `DEPLOY_KNOWN_HOSTS` | 初始化输出最后一行完整的 `47.111.109.82 ssh-ed25519 ...` |
| `DEPLOY_SSH_KEY` | 在阿里云终端运行 `cat /root/portfolio-actions-key` 后显示的全部私钥，包括 BEGIN / END 行 |

私钥只粘贴到 GitHub 的 Secret 输入框，不发聊天、不发截图、不提交仓库。GitHub 运行器通过该受限密钥连接专用发布账号，不使用 root 密钥。

服务器的 SSH 端口 22 必须允许 GitHub 运行器访问；若目前只允许阿里云 Workbench 连接，先调整为适合部署的来源规则或使用受控运行器。不要关闭防火墙。网站的 80 和 443 保持现有访问配置。

## 日常发布

1. 修改源码，预览并提交到 GitHub main。
2. 打开 [发布工作流](https://github.com/wly789987-rgb/Portfolio/actions/workflows/publish.yml)。
3. 点击 **Run workflow**，分支选 **main**，操作选 **deploy**，提交号留空，再点击运行。
4. 等待绿色成功。运行摘要会显示实际提交号、发布时间和发布编号。
5. 打开 https://wangliyan.wang/ 检查修改；https://wangliyan.wang/release.json 可以查看实际在线版本。

首个自动发布将使用 GitHub 仓库代码，它与此前上传的桌面交付包有差异。请先确认仓库内容符合预期，再点击首次发布。

## 一键回退

同一个按钮将操作改成 **rollback**，提交号留空，即恢复上一版；也可以填写服务器曾成功发布过的完整提交号。

首次初始化时保留的是原网站的 `manual-import` 版本，首个自动发布后也可以回退到它。每次成功切换后，`previous` 指向切换前的版本，连续点击回退可能在两版之间切换。

## 实际执行的过程

- GitHub 只打包该提交中的 `index.html`、`app.js`、`style.css` 和 `assets/`，不会上传 `.git`、密钥或部署工具到网站。
- 服务器解压到独立版本目录，拒绝越界路径、软链接和异常文件，保留已有版本。
- 使用软链接替换切换版本，无需重新申请证书或重启服务器。
- 在服务器本机验证 HTTPS、首页、脚本、样式与发布编号。失败时恢复切换前版本。
- GitHub 再验证公网版本；失败时尝试恢复上一版，并将任务标为失败。
- 全部版本保存在 `/srv/portfolio/releases/`，暂不自动删除。定期检查磁盘空间，清理前确认当前版本与回退版本；这里只包含网站文件，不包含证书备份。

`setup-server.sh` 安装的是当时版本的服务器端发布程序，后续修改 `release.py` 不会仅靠网站发布自动升级它，需要单独安排更新。

## 本地验证

```bash
python -m unittest discover -s deploy -p 'test_*.py' -v
bash -n deploy/setup-server.sh
```

工作流和脚本纳入 Git 历史。是否完成服务器初始化、Secrets 配置、首次真实发布，以实际执行结果为准；仅提交这些文件并不代表已经接通服务器。
