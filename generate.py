# -*- coding: utf-8 -*-
"""根据 posts/data.json 为每篇文章生成带静态 OG 标签的页面 p/<文章id>/index.html"""
import json
import os
import shutil
import html as html_mod
import hashlib
from base64 import b64encode
from urllib.parse import quote

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(ROOT, 'posts', 'data.json')
PRIVATE_DIR = os.path.join(ROOT, 'posts', 'private')
KEY_PATH = os.path.join(ROOT, 'private.key')
OUT_DIR = os.path.join(ROOT, 'p')

PRIVATE_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">

<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" type="image/jpeg" href="../../static/logo.jpg">
    <meta name="robots" content="noindex, nofollow">
    <title>{esc_title} - 叹雪的小本本</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/remixicon@4.3.0/fonts/remixicon.css">
    <link rel="stylesheet" href="../../static/style.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/styles/atom-one-light.min.css" id="hljs-theme">
    <style>
        .private-lock {{ text-align: center; padding: 64px 0; }}
        .private-lock-icon {{ font-size: 40px; color: var(--text-muted); margin-bottom: 16px; }}
        .private-lock-text {{ font-size: 15px; color: var(--text-secondary); margin-bottom: 24px; }}
        .private-lock-input {{
            width: min(100%, 320px); padding: 12px 14px; font-size: 15px;
            border: 1px solid var(--border); border-radius: 8px;
            background: var(--bg-soft); color: var(--text);
            font-family: inherit; outline: none; text-align: center;
            transition: border-color 0.2s;
        }}
        .private-lock-input:focus {{ border-color: var(--accent); }}
        .private-lock-btn {{
            margin-top: 12px; padding: 10px 28px; border: none; border-radius: 8px;
            background: var(--accent); color: #fff; font-size: 14px; font-family: inherit;
            cursor: pointer; transition: opacity 0.2s;
        }}
        .private-lock-btn:hover {{ opacity: 0.85; }}
        .private-lock-error {{ margin-top: 12px; font-size: 13px; color: #dc2626; display: none; }}
        .private-lock-error.show {{ display: block; }}
    </style>
</head>

<body>
    <!-- 阅读进度条 -->
    <div class="progress-bar" id="progress-bar"></div>

    <!-- 主内容（无侧边栏） -->
    <div class="main-wrapper" style="margin-left:0">
        <header class="topbar">
            <div class="topbar-left"></div>
            <h1 class="topbar-title">{esc_title}</h1>
            <button class="theme-btn" id="theme-btn">
                <i class="ri-moon-line"></i>
            </button>
        </header>

        <main class="main">
            <div class="container">
                <article class="post-header">
                    <h1 class="post-title">{esc_title}</h1>
                    <div class="post-meta">
                        <time>{esc_date}</time>
                    </div>
                </article>

                <div class="private-lock" id="private-lock">
                    <div class="private-lock-icon"><i class="ri-lock-2-line"></i></div>
                    <p class="private-lock-text">这是一篇私密文章，请输入密码查看</p>
                    <input type="password" class="private-lock-input" id="private-input" placeholder="密码" autocomplete="off">
                    <div><button class="private-lock-btn" id="private-btn">解锁</button></div>
                    <p class="private-lock-error" id="private-error">密码错误，请重试</p>
                </div>

                <div class="post-content" id="post-content" hidden></div>
            </div>
        </main>

        <footer class="footer">
            <p>叹雪的小本本</p>
        </footer>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/highlight.min.js"></script>
    <script>
        (function() {{
            // 主题（精简版）
            var theme = localStorage.getItem('theme') ||
                (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
            function applyTheme(t) {{
                document.documentElement.setAttribute('data-theme', t);
                localStorage.setItem('theme', t);
                var btn = document.getElementById('theme-btn');
                if (btn) btn.querySelector('i').className = t === 'dark' ? 'ri-sun-line' : 'ri-moon-line';
                var hljsTheme = document.getElementById('hljs-theme');
                if (hljsTheme) {{
                    hljsTheme.href = t === 'dark'
                        ? 'https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/styles/atom-one-dark.min.css'
                        : 'https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/styles/atom-one-light.min.css';
                }}
            }}
            applyTheme(theme);
            document.getElementById('theme-btn').onclick = function() {{
                theme = theme === 'light' ? 'dark' : 'light';
                applyTheme(theme);
            }};

            // 阅读进度条
            var progressBar = document.getElementById('progress-bar');
            window.addEventListener('scroll', function() {{
                requestAnimationFrame(function() {{
                    var h = document.documentElement;
                    var max = h.scrollHeight - h.clientHeight;
                    progressBar.style.transform = 'scaleX(' + (max > 0 ? h.scrollTop / max : 0) + ')';
                }});
            }}, {{ passive: true }});

            // 解密
            var SALT = '{salt_b64}';
            var PAYLOAD = '{payload_b64}';

            function b64ToBuf(b64) {{
                var bin = atob(b64);
                var buf = new Uint8Array(bin.length);
                for (var i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
                return buf.buffer;
            }}

            function unlock() {{
                var pwd = document.getElementById('private-input').value;
                if (!pwd) return;
                var enc = new TextEncoder();
                crypto.subtle.importKey('raw', enc.encode(pwd), 'PBKDF2', false, ['deriveKey'])
                    .then(function(material) {{
                        return crypto.subtle.deriveKey(
                            {{ name: 'PBKDF2', salt: b64ToBuf(SALT), iterations: 210000, hash: 'SHA-256' }},
                            material,
                            {{ name: 'AES-GCM', length: 256 }},
                            false,
                            ['decrypt']
                        );
                    }})
                    .then(function(key) {{
                        var data = new Uint8Array(b64ToBuf(PAYLOAD));
                        var iv = data.slice(0, 12);
                        var ct = data.slice(12);
                        return crypto.subtle.decrypt({{ name: 'AES-GCM', iv: iv }}, key, ct);
                    }})
                    .then(function(plain) {{
                        var md = new TextDecoder().decode(plain);
                        var contentEl = document.getElementById('post-content');
                        contentEl.innerHTML = marked.parse(md);
                        var blocks = contentEl.querySelectorAll('pre code');
                        for (var i = 0; i < blocks.length; i++) hljs.highlightElement(blocks[i]);
                        var imgs = contentEl.querySelectorAll('img');
                        for (var j = 0; j < imgs.length; j++) imgs[j].setAttribute('loading', 'lazy');
                        document.getElementById('private-lock').hidden = true;
                        contentEl.hidden = false;
                    }})
                    .catch(function() {{
                        document.getElementById('private-error').classList.add('show');
                        document.getElementById('private-input').select();
                    }});
            }}

            document.getElementById('private-btn').onclick = unlock;
            document.getElementById('private-input').addEventListener('keydown', function(e) {{
                if (e.key === 'Enter') unlock();
            }});
            document.getElementById('private-input').focus();
        }})();
    </script>
</body>

</html>
'''

TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">

<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" type="image/jpeg" href="../../static/logo.jpg">
    <meta name="description" content="{esc_excerpt}">
    <title>{esc_title} - 叹雪的小本本</title>
    <meta property="og:site_name" content="叹雪的小本本">
    <meta property="og:type" content="article">
    <meta property="og:title" content="{esc_title}">
    <meta property="og:description" content="{esc_excerpt}">
    <meta property="og:image" content="https://tanxue0118.github.io/blog/static/logo.jpg">
    <meta property="article:published_time" content="{esc_date}">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/remixicon@4.3.0/fonts/remixicon.css">
    <link rel="stylesheet" href="../../static/style.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/styles/atom-one-light.min.css" id="hljs-theme">
</head>

<body>
    <!-- 阅读进度条 -->
    <div class="progress-bar" id="progress-bar"></div>

    <!-- 侧边栏 -->
    <aside class="sidebar" id="sidebar">
        <div class="sidebar-inner">
            <div class="sidebar-header">
                <div class="avatar">
                    <img src="../../static/logo.jpg" alt="头像">
                </div>
                <h2 class="sidebar-name">叹雪</h2>
                <p class="sidebar-bio">记录一切</p>
            </div>

            <nav class="sidebar-nav">
                <a href="../../index.html" class="sidebar-link">
                    <i class="ri-home-4-line"></i>
                    <span>首页</span>
                </a>
                <a href="../../archive.html" class="sidebar-link">
                    <i class="ri-archive-line"></i>
                    <span>归档</span>
                </a>
                <a href="https://github.com/tanxue0118" target="_blank" class="sidebar-link">
                    <i class="ri-github-line"></i>
                    <span>GitHub</span>
                </a>
                <a href="https://tanxue.qzz.io/" target="_blank" class="sidebar-link">
                    <i class="ri-links-line"></i>
                    <span>个人主页</span>
                </a>
            </nav>

            <div class="sidebar-tags">
                <h3 class="sidebar-section-title">标签</h3>
                <div class="tag-list" id="page-tag-list"></div>
            </div>

            <div class="sidebar-stats">
                <h3 class="sidebar-section-title">统计</h3>
                <img class="counter-image"
                     src="https://count.getloli.com/@{esc_id}?theme=moebooru&darkmode=auto"
                     alt="文章访问统计">
            </div>

            <div class="sidebar-footer">
                <button id="theme-toggle" class="theme-toggle">
                    <i class="ri-moon-line"></i>
                    <span>深色模式</span>
                </button>
            </div>
        </div>
    </aside>

    <!-- 遮罩层 -->
    <div class="overlay" id="overlay"></div>

    <!-- 主内容 -->
    <div class="main-wrapper">
        <header class="topbar">
            <div class="topbar-left">
                <button class="menu-btn" id="menu-btn">
                    <i class="ri-menu-line"></i>
                </button>
                <button class="sidebar-toggle" id="sidebar-toggle" title="收起侧边栏">
                    <i class="ri-side-bar-line"></i>
                </button>
            </div>
            <h1 class="topbar-title">{esc_title}</h1>
            <button class="theme-btn" id="theme-btn">
                <i class="ri-moon-line"></i>
            </button>
        </header>

        <main class="main">
            <div class="container">
                <a href="../../index.html" class="back-link">← 返回首页</a>

                <article class="post-header">
                    <h1 class="post-title">{esc_title}</h1>
                    <div class="post-meta">
                        <time>{esc_date}</time>
                        <span>{tags_html}</span>
                    </div>
                </article>

                <div class="post-content" id="post-content">
                    <p>加载中...</p>
                </div>

                <nav class="post-nav" id="post-nav"{nav_hidden}>
                    {prev_link}
                    {next_link}
                </nav>
            </div>
        </main>

        <footer class="footer">
            <p>叹雪的小本本</p>
        </footer>
    </div>

    <!-- 图片灯箱 -->
    <div class="lightbox" id="lightbox">
        <img id="lightbox-img" alt="">
    </div>

    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/highlight.min.js"></script>
    <script src="../../static/script.js"></script>
    <script>
        (function() {{
            var contentEl = document.getElementById('post-content');

            // 阅读进度条
            var progressBar = document.getElementById('progress-bar');
            if (progressBar) {{
                var ticking = false;
                window.addEventListener('scroll', function() {{
                    if (!ticking) {{
                        requestAnimationFrame(function() {{
                            var h = document.documentElement;
                            var max = h.scrollHeight - h.clientHeight;
                            progressBar.style.transform = 'scaleX(' + (max > 0 ? h.scrollTop / max : 0) + ')';
                            ticking = false;
                        }});
                        ticking = true;
                    }}
                }}, {{ passive: true }});
            }}

            // 图片灯箱
            var lightbox = document.getElementById('lightbox');
            var lightboxImg = document.getElementById('lightbox-img');

            function closeLightbox() {{
                lightbox.classList.remove('show');
                document.body.style.overflow = '';
            }}

            if (lightbox) {{
                lightbox.onclick = closeLightbox;
                document.addEventListener('keydown', function(e) {{
                    if (e.key === 'Escape' && lightbox.classList.contains('show')) closeLightbox();
                }});
            }}

            // 加载标签
            fetch('../../posts/data.json')
                .then(function(r) {{ return r.json(); }})
                .then(function(data) {{
                    var tagList = document.getElementById('page-tag-list');
                    if (tagList && data.tags) {{
                        var html = '';
                        for (var j = 0; j < data.tags.length; j++) {{
                            var t = data.tags[j];
                            var href = t === '全部' ? '../../index.html' : '../../index.html?tag=' + encodeURIComponent(t);
                            html += '<a href="' + href + '" class="tag-item">' + t + '</a>';
                        }}
                        tagList.innerHTML = html;
                    }}
                }})
                .catch(function() {{}});

            // 加载正文
            fetch('../../posts/{js_id}.md')
                .then(function(r) {{
                    if (!r.ok) throw new Error('MD HTTP ' + r.status);
                    return r.text();
                }})
                .then(function(md) {{
                    contentEl.innerHTML = marked.parse(md);
                    var blocks = contentEl.querySelectorAll('pre code');
                    for (var i = 0; i < blocks.length; i++) {{
                        hljs.highlightElement(blocks[i]);
                    }}

                    // 图片路径修正（md 里的相对路径基于 posts/ 目录）
                    var imgs = contentEl.querySelectorAll('img');
                    for (var j = 0; j < imgs.length; j++) {{
                        var src = imgs[j].getAttribute('src');
                        if (src && src.indexOf('http') !== 0 && src.indexOf('/') !== 0) {{
                            imgs[j].src = '../../posts/' + src;
                        }}
                        imgs[j].setAttribute('loading', 'lazy');
                        imgs[j].onclick = function() {{
                            if (!lightbox) return;
                            lightboxImg.src = this.src;
                            lightboxImg.alt = this.alt || '';
                            lightbox.classList.add('show');
                            document.body.style.overflow = 'hidden';
                        }};
                    }}
                }})
                .catch(function(err) {{
                    console.error('加载失败:', err);
                    contentEl.innerHTML = '<p>加载文章内容失败。</p>';
                }});
        }})();
    </script>
</body>

</html>
'''

TAG_COLORS = {
    '中文': 'tag-green',
    'English': 'tag-blue',
    'Android': 'tag-green',
    '技术': 'tag-blue',
}


def esc(s):
    return html_mod.escape(str(s or ''), quote=True)


def nav_link(cls, label, pid, title):
    return ('<a href="../{0}/" class="post-nav-link {1}">'
            '<span class="post-nav-label">{2}</span>'
            '<span class="post-nav-title">{3}</span></a>').format(
                quote(pid), cls, label, esc(title))


def main():
    with open(DATA_PATH, encoding='utf-8-sig') as f:
        data = json.load(f)

    posts = data.get('posts', [])
    private_ids = set(data.get('private_posts', []))
    public_posts = [p for p in posts if p['id'] not in private_ids]

    if os.path.isdir(OUT_DIR):
        shutil.rmtree(OUT_DIR)
    os.makedirs(OUT_DIR)

    for i, p in enumerate(public_posts):
        pid = p['id']

        tags_html = ''
        for t in p.get('tags', []):
            tc = TAG_COLORS.get(t, 'tag-blue')
            tags_html += '<span class="tag {0}">{1}</span>'.format(tc, esc(t))

        prev_link = ''
        next_link = ''
        if i > 0:
            prev_link = nav_link('prev', '← 上一篇', public_posts[i - 1]['id'], public_posts[i - 1]['title'])
        if i < len(public_posts) - 1:
            next_link = nav_link('next', '下一篇 →', public_posts[i + 1]['id'], public_posts[i + 1]['title'])

        page = TEMPLATE.format(
            esc_title=esc(p['title']),
            esc_excerpt=esc(p.get('excerpt', '')),
            esc_date=esc(p.get('date', '')),
            esc_id=esc(pid),
            js_id=pid.replace('\\', '\\\\').replace("'", "\\'"),
            tags_html=tags_html,
            prev_link=prev_link,
            next_link=next_link,
            nav_hidden='' if (prev_link or next_link) else ' hidden',
        )

        d = os.path.join(OUT_DIR, pid)
        os.makedirs(d)
        with open(os.path.join(d, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(page)

    print('generated {0} public pages into p/'.format(len(public_posts)))

    # 私密文章：AES-256-GCM 加密正文，密文嵌入静态页
    if private_ids:
        if not os.path.isfile(KEY_PATH):
            print('WARNING: private_posts configured but private.key missing, skipped.')
            return
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        with open(KEY_PATH, encoding='utf-8-sig') as f:
            password = f.read().strip()
        if not password:
            print('WARNING: private.key is empty, skipped private posts.')
            return

        salt = os.urandom(16)
        key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 210000, dklen=32)
        aes = AESGCM(key)

        count = 0
        for p in posts:
            pid = p['id']
            if pid not in private_ids:
                continue
            md_path = os.path.join(PRIVATE_DIR, pid + '.md')
            if not os.path.isfile(md_path):
                print('WARNING: missing private markdown: posts/private/{0}.md'.format(pid))
                continue
            with open(md_path, encoding='utf-8-sig') as f:
                md = f.read().encode('utf-8')

            iv = os.urandom(12)
            ct = aes.encrypt(iv, md, None)
            payload = b64encode(iv + ct).decode('ascii')

            page = PRIVATE_TEMPLATE.format(
                esc_title=esc(p['title']),
                esc_date=esc(p.get('date', '')),
                salt_b64=b64encode(salt).decode('ascii'),
                payload_b64=payload,
            )

            d = os.path.join(OUT_DIR, pid)
            os.makedirs(d)
            with open(os.path.join(d, 'index.html'), 'w', encoding='utf-8') as f:
                f.write(page)
            count += 1

        print('generated {0} private (encrypted) pages into p/'.format(count))


if __name__ == '__main__':
    main()
