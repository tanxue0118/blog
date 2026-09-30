# 叹雪的小本本

一个纯静态个人博客，记录玩机经历以及经验。

在线地址：https://tanxue0118.github.io/blog/

## 功能

- 文章列表（Markdown 驱动，改 `posts/data.json` 即发文章）
- 标签筛选
- 文章搜索（标题 / 摘要 / 标签，支持 `?q=` 参数分享）
- 归档页（按年月分组）
- 相册页（分组筛选 + 网格浏览 + 灯箱切换）
- 深色模式（跟随系统 + 手动切换，记忆选择）
- 代码高亮（highlight.js，明暗双主题）
- 阅读进度条
- 上一篇 / 下一篇导航
- 图片懒加载 + 点击放大（灯箱）
- 自定义 404 页
- 访问统计（count.getloli.com）

## 目录结构

```
├── index.html        # 首页（文章列表 + 搜索 + 分页）
├── post.html         # 旧文章链接入口（自动跳转到 p/ 下的静态页）
├── archive.html      # 归档页（按年月分组）
├── photos.html       # 相册页（分组 + 网格 + 灯箱）
├── 404.html          # GitHub Pages 自定义 404
├── generate.py       # 静态页生成器 + 相册缩略图生成（push.bat 会自动调用）
├── p/                # 自动生成的文章页（每篇一个目录，OG 标签静态写死）
│   └── <文章id>/
│       └── index.html
├── posts/
│   ├── data.json     # 文章索引（站点信息、标签、文章列表）
│   ├── *.md          # 文章正文
│   └── assets/       # 文章图片等资源
├── photos/
│   ├── data.json     # 相册索引（分组、照片列表）
│   ├── images/       # 照片原图（git 忽略，不进仓库）
│   └── thumbs/       # 自动生成的 web 缩略图（small 600px / large 1600px）
└── static/
    ├── style.css     # 全站样式（明暗双主题）
    ├── script.js     # 首页逻辑（主题、标签、搜索、分页）
    └── logo.jpg      # 头像 / favicon
```

## 发文章

1. 在 `posts/` 下新建 `文章标题.md`
2. 在 `posts/data.json` 的 `posts` 数组开头加一条：

```json
{
  "id": "文章标题",
  "title": "显示的文章标题",
  "date": "2026-07-10",
  "tags": ["Android", "技术"],
  "excerpt": "一句话摘要"
}
```

注意 `id` 必须和 md 文件名一致（不含 `.md` 后缀）。

3. 如果是新标签，顺便加进 `tags` 数组。

## 发照片

1. 把原图丢进 `photos/images/`（此目录已被 git 忽略，原图不会上传）
2. 在 `photos/data.json` 的 `entries` 数组里加条目。相册按日期分组展示（每天的条目归在一个日期分区下），支持三种条目：

**一组照片**（同一个地方 / 同一次出行拍的几张图，作为一个整体展示，内含小图网格）：

```json
{
  "type": "group",
  "title": "去xx地方打卡",
  "date": "2026-09-28",
  "album": "出行",
  "location": "杭州·西湖",
  "weather": "晴",
  "text": "可选：这组照片想说的话，支持 \\n 换行",
  "files": ["IMG_001.jpg", "IMG_002.jpg", "IMG_003.jpg"]
}
```

**单张照片**（完整展示不裁切）：

```json
{ "type": "photo", "file": "IMG_004.jpg", "title": "可选标题", "date": "2026-09-26", "album": "日常", "location": "家里阳台", "weather": "多云" }
```

**纯文字随笔**（占满整行，不参与灯箱）：

```json
{ "type": "text", "text": "想说的话，支持 \\n 换行", "date": "2026-09-27", "album": "日常" }
```

通用字段说明：
- `date`：必填，格式 `YYYY-MM-DD`，相册按它分组和倒序排列
- `location`、`weather`：可选，会显示在日期分区头和条目卡片上
- `title`、`text`：可选，标题加粗显示，文字内容显示在照片上方
- `album`：可选，用于顶部分组筛选

3. 如果是新相册分组，把名字加进 `albums` 数组（`"全部"` 保持在第一位）。

`push.bat` 时会自动为所有条目引用的图片生成两档缩略图：`small/`（600px，网格用）和 `large/`（1600px，灯箱用）。PNG/WEBP 会统一转成 JPG 以减小体积，GIF 保留原格式。

## 本地预览

```powershell
cd blog
py -m http.server 8000
```

打开 http://localhost:8000 （直接双击 html 文件打不开，fetch 会被浏览器拦截）。

## 一键推送

双击 `push.bat`，或：

```cmd
push.bat "更新了xx文章"
```

不带参数则使用日期时间作为提交信息。脚本流程：运行 generate.py 重新生成 `p/` 静态文章页 → add → commit → pull（冲突时以本地为准）→ push。

> 文章页地址为 `p/<文章id>/`，OG 标签已静态写入，QQ/微信/Twitter 分享链接可直接解析出标题和摘要卡片。旧的 `post.html?id=xxx` 链接会自动跳转，不会失效。

## 技术栈

- 纯 HTML / CSS / JS，零构建
- [marked](https://github.com/markedjs/marked) Markdown 渲染
- [highlight.js](https://highlightjs.org/) 代码高亮
- [Remix Icon](https://remixicon.com/) 图标
- Google Fonts：Noto Serif SC + Inter
