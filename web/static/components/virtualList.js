/**
 * 虚拟滚动列表组件
 * 实现只渲染可视区域内的列表项，提升大数据量列表的性能
 *
 * 功能：
 * - 虚拟滚动：只渲染可视区域 + 缓冲区的列表项
 * - 懒加载：滚动到底部时加载更多数据
 * - 高性能渲染：使用 DocumentFragment 和 requestAnimationFrame
 */

const VirtualList = {
    /**
     * 创建虚拟列表实例
     * @param {Object} options - 配置选项
     * @param {HTMLElement} options.container - 滚动容器元素
     * @param {number} options.itemHeight - 列表项预估高度（像素）
     * @param {number} options.overscan - 上下预渲染的额外项数
     * @param {Function} options.renderItem - 渲染单个列表项的函数 (item, index) => HTMLElement
     * @param {Function} options.onLoadMore - 滚动到底部时的回调函数
     * @param {number} options.loadMoreThreshold - 触发加载更多的阈值（距离底部像素）
     * @param {Function} options.onItemClick - 列表项点击回调 (item, index) => void
     * @returns {Object} 虚拟列表实例
     */
    create(options) {
        const {
            container,
            itemHeight = 76,
            overscan = 5,
            renderItem,
            onLoadMore,
            loadMoreThreshold = 200,
            onItemClick,
        } = options;

        // 内部状态
        let items = [];
        let isLoading = false;
        let hasMore = true;
        let totalHeight = 0;
        let visibleRange = { start: 0, end: 0 };
        let rafId = null;

        // 创建内部 DOM 结构
        const wrapper = document.createElement('div');
        wrapper.className = 'virtual-list-wrapper';

        const content = document.createElement('div');
        content.className = 'virtual-list-content';
        content.style.position = 'relative';
        content.style.overflow = 'hidden';

        wrapper.appendChild(content);

        // 清空容器并添加虚拟列表结构
        container.innerHTML = '';
        container.appendChild(wrapper);

        // 计算可视区域内的列表项范围
        const calculateVisibleRange = () => {
            const scrollTop = container.scrollTop;
            const clientHeight = container.clientHeight;

            const start = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
            const end = Math.min(
                items.length,
                Math.ceil((scrollTop + clientHeight) / itemHeight) + overscan
            );

            return { start, end };
        };

        // 更新内容区域高度
        const updateContentHeight = () => {
            totalHeight = items.length * itemHeight;
            content.style.height = `${totalHeight}px`;
        };

        // 渲染可视区域的列表项
        const renderVisibleItems = () => {
            // 处理空数据状态
            if (items.length === 0 && !isLoading) {
                content.innerHTML = '<div class="empty-placeholder">暂无数据</div>';
                return;
            }

            const newRange = calculateVisibleRange();

            // 如果范围没有变化，跳过渲染
            if (newRange.start === visibleRange.start && newRange.end === visibleRange.end) {
                return;
            }

            visibleRange = newRange;

            // 使用 DocumentFragment 批量更新
            const fragment = document.createDocumentFragment();

            for (let i = visibleRange.start; i < visibleRange.end; i++) {
                const item = items[i];
                if (item === undefined) continue;

                const element = renderItem(item, i);

                // 设置绝对定位
                element.style.position = 'absolute';
                element.style.top = `${i * itemHeight}px`;
                element.style.left = '0';
                element.style.right = '0';
                element.style.width = '100%';
                element.dataset.index = i;

                // 绑定点击事件
                if (onItemClick) {
                    element.addEventListener('click', () => onItemClick(item, i));
                }

                fragment.appendChild(element);
            }

            // 清空并重新添加
            content.innerHTML = '';
            content.appendChild(fragment);

            // 添加加载指示器
            if (isLoading) {
                const loader = document.createElement('div');
                loader.className = 'virtual-list-loader';
                loader.textContent = '加载中...';
                loader.style.position = 'absolute';
                loader.style.top = `${items.length * itemHeight}px`;
                loader.style.left = '0';
                loader.style.right = '0';
                loader.style.padding = '16px';
                loader.style.textAlign = 'center';
                loader.style.color = 'var(--text-muted, #888)';
                content.appendChild(loader);
            }
        };

        // 使用 requestAnimationFrame 优化渲染
        const scheduleRender = () => {
            if (rafId !== null) {
                cancelAnimationFrame(rafId);
            }
            rafId = requestAnimationFrame(() => {
                renderVisibleItems();
                rafId = null;
            });
        };

        // 检查是否需要加载更多
        const checkLoadMore = () => {
            if (isLoading || !hasMore || !onLoadMore) return;

            const scrollTop = container.scrollTop;
            const scrollHeight = container.scrollHeight;
            const clientHeight = container.clientHeight;

            // 距离底部小于阈值时触发加载
            if (scrollHeight - scrollTop - clientHeight < loadMoreThreshold) {
                isLoading = true;
                scheduleRender();
                onLoadMore();
            }
        };

        // 滚动事件处理（带节流）
        let scrollTimeout = null;
        const handleScroll = () => {
            if (scrollTimeout) {
                clearTimeout(scrollTimeout);
            }
            scrollTimeout = setTimeout(() => {
                scheduleRender();
                checkLoadMore();
            }, 16); // ~60fps
        };

        // 绑定滚动事件
        container.addEventListener('scroll', handleScroll, { passive: true });

        // ResizeObserver 监听容器大小变化
        let resizeObserver = null;
        if (window.ResizeObserver) {
            resizeObserver = new ResizeObserver(() => {
                scheduleRender();
            });
            resizeObserver.observe(container);
        }

        // 返回实例对象
        const instance = {
            /**
             * 设置列表数据
             * @param {Array} newItems - 新的数据数组
             * @param {boolean} append - 是否追加到现有数据
             */
            setItems(newItems, append = false) {
                if (append) {
                    items = [...items, ...newItems];
                } else {
                    items = newItems;
                }
                updateContentHeight();
                scheduleRender();
            },

            /**
             * 获取当前数据
             * @returns {Array} 当前列表数据
             */
            getItems() {
                return items;
            },

            /**
             * 设置加载状态
             * @param {boolean} loading - 是否正在加载
             */
            setLoading(loading) {
                isLoading = loading;
                scheduleRender();
            },

            /**
             * 设置是否还有更多数据
             * @param {boolean} more - 是否还有更多数据
             */
            setHasMore(more) {
                hasMore = more;
            },

            /**
             * 获取是否还有更多数据
             * @returns {boolean}
             */
            getHasMore() {
                return hasMore;
            },

            /**
             * 滚动到指定索引
             * @param {number} index - 目标索引
             */
            scrollToIndex(index) {
                const targetTop = index * itemHeight;
                container.scrollTop = targetTop;
            },

            /**
             * 滚动到顶部
             */
            scrollToTop() {
                container.scrollTop = 0;
            },

            /**
             * 强制刷新渲染
             */
            refresh() {
                updateContentHeight();
                visibleRange = { start: -1, end: -1 }; // 强制重置范围
                scheduleRender();
            },

            /**
             * 清空列表
             */
            clear() {
                items = [];
                hasMore = true;
                isLoading = false;
                content.innerHTML = '';
                updateContentHeight();
            },

            /**
             * 销毁实例
             */
            destroy() {
                if (rafId !== null) {
                    cancelAnimationFrame(rafId);
                }
                if (scrollTimeout) {
                    clearTimeout(scrollTimeout);
                }
                if (resizeObserver) {
                    resizeObserver.disconnect();
                }
                container.removeEventListener('scroll', handleScroll);
                container.innerHTML = '';
            },

            /**
             * 获取当前可见范围
             * @returns {Object} { start, end }
             */
            getVisibleRange() {
                return { ...visibleRange };
            },

            /**
             * 获取数据总数
             * @returns {number}
             */
            getTotalCount() {
                return items.length;
            }
        };

        // 初始渲染
        updateContentHeight();
        scheduleRender();

        return instance;
    },

    /**
     * 懒加载管理器
     * 用于管理分页数据的懒加载
     */
    createLazyLoader(options) {
        const {
            initialPage = 1,
            pageSize = 20,
            onLoadPage, // async (page, pageSize) => { items: [], total: number }
            onItemsLoaded, // (items, page, hasMore) => void
        } = options;

        let currentPage = initialPage;
        let totalItems = 0;
        let isLoading = false;
        let hasMore = true;

        return {
            /**
             * 加载下一页数据
             */
            async loadNextPage() {
                if (isLoading || !hasMore) return;

                isLoading = true;

                try {
                    const result = await onLoadPage(currentPage, pageSize);
                    const { items, total } = result;

                    totalItems = total;
                    hasMore = currentPage * pageSize < total;

                    if (onItemsLoaded) {
                        onItemsLoaded(items, currentPage, hasMore);
                    }

                    currentPage++;
                } catch (error) {
                    console.error('加载失败:', error);
                } finally {
                    isLoading = false;
                }
            },

            /**
             * 重置加载器状态
             */
            reset() {
                currentPage = initialPage;
                totalItems = 0;
                hasMore = true;
                isLoading = false;
            },

            /**
             * 获取当前页码
             */
            getCurrentPage() {
                return currentPage;
            },

            /**
             * 获取总数
             */
            getTotalItems() {
                return totalItems;
            },

            /**
             * 获取是否正在加载
             */
            getIsLoading() {
                return isLoading;
            },

            /**
             * 获取是否还有更多
             */
            getHasMore() {
                return hasMore;
            }
        };
    }
};

// 导出到全局命名空间
window.VirtualList = VirtualList;
