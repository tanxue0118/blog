(function() {
    'use strict';

    // 侧边栏切换
    var sidebar = document.getElementById('sidebar');
    var overlay = document.getElementById('overlay');
    var menuBtn = document.getElementById('menu-btn');
    var sidebarToggle = document.getElementById('sidebar-toggle');
    var themeToggle = document.getElementById('theme-toggle');
    var themeBtn = document.getElementById('theme-btn');
    var currentTheme = localStorage.getItem('theme') || 'light';
    var sidebarCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';

    // 移动端打开侧边栏
    if (menuBtn) {
        menuBtn.onclick = function() {
            sidebar.classList.add('active');
            overlay.classList.add('active');
        };
    }

    // 点击遮罩关闭
    if (overlay) {
        overlay.onclick = function() {
            sidebar.classList.remove('active');
            overlay.classList.remove('active');
        };
    }

    // 桌面端收起侧边栏
    if (sidebarCollapsed) {
        sidebar.classList.add('collapsed');
        document.body.classList.add('sidebar-collapsed');
    }

    if (sidebarToggle) {
        sidebarToggle.onclick = function() {
            sidebarCollapsed = !sidebarCollapsed;
            sidebar.classList.toggle('collapsed', sidebarCollapsed);
            document.body.classList.toggle('sidebar-collapsed', sidebarCollapsed);
            localStorage.setItem('sidebarCollapsed', sidebarCollapsed);
        };
    }

    // 深色模式
    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        var icons = document.querySelectorAll('.theme-toggle i, .theme-btn i');
        for (var i = 0; i < icons.length; i++) {
            icons[i].className = theme === 'dark' ? 'ri-sun-line' : 'ri-moon-line';
        }
        var span = document.querySelector('.theme-toggle span');
        if (span) span.textContent = theme === 'dark' ? '浅色模式' : '深色模式';

        // 切换代码高亮主题
        var hljsTheme = document.getElementById('hljs-theme');
        if (hljsTheme) {
            hljsTheme.href = theme === 'dark'
                ? 'https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/styles/atom-one-dark.min.css'
                : 'https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/styles/atom-one-light.min.css';
        }
    }

    if (window.matchMedia('(prefers-color-scheme: dark)').matches && !localStorage.getItem('theme')) {
        currentTheme = 'dark';
    }
    applyTheme(currentTheme);

    if (themeToggle) themeToggle.onclick = function() { currentTheme = currentTheme === 'light' ? 'dark' : 'light'; applyTheme(currentTheme); };
    if (themeBtn) themeBtn.onclick = function() { currentTheme = currentTheme === 'light' ? 'dark' : 'light'; applyTheme(currentTheme); };

    // 加载文章数据
    var postsList = document.getElementById('posts-list');
    var tagList = document.getElementById('tag-list');
    var pageInfo = document.getElementById('page-info');

    if (!postsList && !tagList) return;

    var urlParams = new URLSearchParams(window.location.search);
    var currentTag = urlParams.get('tag') || '全部';
    var allPosts = [];

    fetch('posts/data.json')
        .then(function(r) {
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
        })
        .then(function(data) {
            allPosts = data.posts || [];

            // 渲染标签
            if (tagList && data.tags) {
                var html = '';
                for (var i = 0; i < data.tags.length; i++) {
                    var tag = data.tags[i];
                    var active = tag === currentTag ? ' active' : '';
                    var href = tag === '全部' ? 'index.html' : 'index.html?tag=' + encodeURIComponent(tag);
                    html += '<a href="' + href + '" class="tag-item' + active + '">' + tag + '</a>';
                }
                tagList.innerHTML = html;

                // 标签点击
                var items = tagList.querySelectorAll('.tag-item');
                for (var j = 0; j < items.length; j++) {
                    items[j].onclick = function(e) {
                        e.preventDefault();
                        currentTag = this.textContent;
                        var newUrl = currentTag === '全部' ? 'index.html' : 'index.html?tag=' + encodeURIComponent(currentTag);
                        history.pushState(null, '', newUrl);
                        for (var k = 0; k < items.length; k++) items[k].classList.remove('active');
                        this.classList.add('active');
                        renderPosts();
                    };
                }
            }

            // 渲染文章
            renderPosts();
        })
        .catch(function(err) {
            console.error('加载失败:', err);
            var errorMsg = '加载失败';
            if (window.location.protocol === 'file:') {
                errorMsg = '请使用本地服务器打开（如 VS Code Live Server），或部署到 GitHub Pages';
            } else {
                errorMsg = '加载失败: ' + err.message;
            }
            if (postsList) postsList.innerHTML = '<p style="text-align:center;color:#999;padding:40px;">' + errorMsg + '</p>';
        });

    function renderPosts() {
        if (!postsList) return;
        var filtered = currentTag === '全部' ? allPosts : allPosts.filter(function(p) {
            return p.tags && p.tags.indexOf(currentTag) !== -1;
        });

        if (filtered.length === 0) {
            postsList.innerHTML = '<p style="text-align:center;color:#999;padding:40px;">暂无文章</p>';
            if (pageInfo) pageInfo.textContent = '共 0 篇文章';
            return;
        }

        var tagColors = { '中文': 'tag-green', 'English': 'tag-blue', 'Android': 'tag-green', '技术': 'tag-blue' };
        var html = '';
        for (var i = 0; i < filtered.length; i++) {
            var p = filtered[i];
            html += '<article class="post">';
            html += '<div class="post-meta"><time>' + p.date + '</time>';
            if (p.tags) {
                for (var t = 0; t < p.tags.length; t++) {
                    var tc = tagColors[p.tags[t]] || 'tag-blue';
                    html += '<span class="tag ' + tc + '">' + p.tags[t] + '</span>';
                }
            }
            html += '</div>';
            html += '<h2 class="post-title"><a href="post.html?id=' + encodeURIComponent(p.id) + '">' + p.title + '</a></h2>';
            html += '<p class="post-excerpt">' + p.excerpt + '</p>';
            html += '</article>';
        }
        postsList.innerHTML = html;
        if (pageInfo) pageInfo.textContent = '共 ' + filtered.length + ' 篇文章';
    }
})();
