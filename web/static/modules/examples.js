/**
 * 示例任务模块
 * 处理示例任务的加载和执行
 */

class ExampleTasks {
    /**
     * 初始化示例任务管理器
     * @param {ClaudeCodeRunner} app - 应用实例
     */
    static init(app) {
        this.app = app;
        this.initExampleButtons();
    }

    /**
     * 初始化示例任务按钮
     */
    static initExampleButtons() {
        // 示例任务视图中的大按钮
        document.querySelectorAll('.btn-example-large').forEach(btn => {
            btn.addEventListener('click', () => {
                const prompt = btn.dataset.prompt;
                this.useExamplePrompt(prompt);
            });
        });
    }

    /**
     * 使用示例提示
     * @param {string} prompt - 示例提示文本
     */
    static useExamplePrompt(prompt) {
        // 切换到当前会话视图
        Navigation.switchView(this.app, Views.CURRENT_SESSION);

        // 填充任务描述
        document.getElementById('prompt').value = prompt;

        // 聚焦到任务描述输入框
        document.getElementById('prompt').focus();
    }
}

// 导出模块
window.ExampleTasks = ExampleTasks;
