/* ============== 主题切换器组件 ============== */

const ThemeSwitcher = (function() {
    // 可用主题列表
    const themes = [
        { id: 'default', name: '默认 Zinc', file: '../variables.css', preview: 'dark' },
        { id: 'morning', name: '晨曦白', file: 'themes/morning.css', preview: 'light' },
        { id: 'cyberpunk', name: '赛博朋克', file: 'themes/cyberpunk.css', preview: 'cyberpunk' },
        { id: 'forest', name: '森林绿', file: 'themes/forest.css', preview: 'forest' },
        { id: 'dream', name: '紫罗兰', file: 'themes/dream.css', preview: 'dream' },
        { id: 'ocean', name: '深海蓝', file: 'themes/ocean.css', preview: 'ocean' },
        { id: 'terminal', name: '极简终端', file: 'themes/terminal.css', preview: 'terminal' },
    ];

    // 主题缓存链接元素
    let themeLink = null;
    let currentTheme = 'default';

    // 初始化
    function init() {
        // 创建或获取主题链接元素
        themeLink = document.getElementById('theme-link');
        if (!themeLink) {
            themeLink = document.createElement('link');
            themeLink.id = 'theme-link';
            themeLink.rel = 'stylesheet';
            document.head.appendChild(themeLink);
        }

        // 加载保存的主题
        const savedTheme = localStorage.getItem('theme') || 'default';
        setTheme(savedTheme, false);

        // 创建 UI
        createSwitcherUI();

        console.log('[ThemeSwitcher] 初始化完成，当前主题:', currentTheme);
    }

    // 设置主题
    function setTheme(themeId, save = true) {
        const theme = themes.find(t => t.id === themeId);
        if (!theme) {
            console.warn('[ThemeSwitcher] 主题不存在:', themeId);
            return false;
        }

        // 更新链接
        const basePath = '/static/css/';
        if (themeId === 'default') {
            themeLink.href = basePath + 'variables.css';
        } else {
            themeLink.href = basePath + theme.file;
        }

        currentTheme = themeId;

        // 保存到 localStorage
        if (save) {
            localStorage.setItem('theme', themeId);
        }

        // 更新 UI 状态
        updateUI(themeId);

        console.log('[ThemeSwitcher] 切换主题:', theme.name);
        return true;
    }

    // 获取当前主题
    function getCurrentTheme() {
        return currentTheme;
    }

    // 更新 UI 状态
    function updateUI(themeId) {
        // 更新下拉面板中的选中状态
        document.querySelectorAll('.theme-option').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.theme === themeId);
        });

        // 更新当前主题显示
        const theme = themes.find(t => t.id === themeId);
        if (theme) {
            const indicator = document.querySelector('.theme-current-indicator');
            const nameEl = document.querySelector('.theme-current-name');
            if (indicator) {
                indicator.style.background = getThemeGradient(themeId);
            }
            if (nameEl) {
                nameEl.textContent = theme.name;
            }
        }
    }

    // 获取主题预览渐变
    function getThemeGradient(themeId) {
        const gradients = {
            'default': 'linear-gradient(135deg, #18181b, #27272a)',
            'morning': 'linear-gradient(135deg, #f5f5f4, #f97316)',
            'cyberpunk': 'linear-gradient(135deg, #0a0a0f, #ff2d92)',
            'forest': 'linear-gradient(135deg, #1a1f1a, #22c55e)',
            'dream': 'linear-gradient(135deg, #1a1625, #8b5cf6)',
            'ocean': 'linear-gradient(135deg, #0f172a, #3b82f6)',
            'terminal': 'linear-gradient(135deg, #000000, #00ff00)',
        };
        return gradients[themeId] || gradients['default'];
    }

    // 创建切换器 UI
    function createSwitcherUI() {
        const navFooter = document.querySelector('.nav-footer');
        if (!navFooter) {
            console.warn('[ThemeSwitcher] 未找到导航底部区域');
            return;
        }

        // 检查是否已存在
        if (document.querySelector('.theme-switcher')) {
            return;
        }

        // 创建切换器容器
        const switcher = document.createElement('div');
        switcher.className = 'theme-switcher';
        switcher.innerHTML = `
            <div class="theme-current" id="theme-current">
                <div class="theme-current-indicator" style="background: ${getThemeGradient(currentTheme)}"></div>
                <span class="theme-current-name">${themes.find(t => t.id === currentTheme)?.name || '默认 Zinc'}</span>
                <span class="theme-current-arrow">▼</span>
            </div>
            <div class="theme-dropdown">
                <div class="theme-options">
                    ${themes.map(theme => `
                        <button class="theme-option ${theme.id === currentTheme ? 'active' : ''}"
                                data-theme="${theme.id}"
                                data-theme-name="${theme.name}"
                                title="${theme.name}">
                            <div class="theme-preview ${theme.preview}">
                                <div class="theme-preview-colors"></div>
                            </div>
                        </button>
                    `).join('')}
                </div>
            </div>
        `;

        navFooter.insertBefore(switcher, navFooter.firstChild);

        // 绑定事件
        bindEvents(switcher);
    }

    // 绑定事件
    function bindEvents(switcher) {
        // 点击切换器
        const currentBtn = switcher.querySelector('#theme-current');
        currentBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            switcher.classList.toggle('expanded');
        });

        // 点击主题选项
        switcher.querySelectorAll('.theme-option').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const themeId = btn.dataset.theme;
                setTheme(themeId);
                switcher.classList.remove('expanded');
            });
        });

        // 点击其他地方关闭
        document.addEventListener('click', (e) => {
            if (!switcher.contains(e.target)) {
                switcher.classList.remove('expanded');
            }
        });

        // 监听导航折叠状态
        const navMenu = document.getElementById('nav-menu');
        if (navMenu) {
            const observer = new MutationObserver(() => {
                // 折叠状态变化时调整位置
            });
            observer.observe(navMenu, { attributes: true, attributeFilter: ['class'] });
        }
    }

    // 公开 API
    return {
        init,
        setTheme,
        getCurrentTheme,
        themes
    };
})();

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    // 延迟一点确保 DOM 完全就绪
    setTimeout(() => ThemeSwitcher.init(), 100);
});
