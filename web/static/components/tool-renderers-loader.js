/**
 * 工具渲染器加载器
 * v0.5.3 - 将 ES 模块渲染器导出到全局作用域
 */

// 动态导入并挂载到全局
async function loadToolRenderers() {
    try {
        const module = await import('/static/components/tool-renderers/index.js');

        // 挂载到全局
        window.ToolRenderers = module.ToolRenderers || module.default;

        // 挂载各个渲染器
        window.BaseRenderer = module.BaseRenderer;
        window.ReadRenderer = module.ReadRenderer;
        window.FileContentRenderer = module.FileContentRenderer;
        window.EditRenderer = module.EditRenderer;
        window.WriteRenderer = module.WriteRenderer;
        window.BashRenderer = module.BashRenderer;
        window.BashResultRenderer = module.BashResultRenderer;
        window.GrepRenderer = module.GrepRenderer;
        window.GlobRenderer = module.GlobRenderer;
        window.SearchResultRenderer = module.SearchResultRenderer;
        window.TodoRenderer = module.TodoRenderer;
        window.TaskRenderer = module.TaskRenderer;
        window.AskQuestionRenderer = module.AskQuestionRenderer;

        console.log('ToolRenderers loaded successfully');
    } catch (err) {
        console.error('Failed to load ToolRenderers:', err);
    }
}

// 立即执行
loadToolRenderers();
