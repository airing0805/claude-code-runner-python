/**
 * 工具渲染器注册表
 * v0.5.3 - 工具渲染器重构
 *
 * 统一管理和导出所有工具渲染器
 */

// 导入所有渲染器
import { BaseRenderer } from './base.js';
import { ReadRenderer, FileContentRenderer } from './readRenderer.js';
import { EditRenderer, WriteRenderer } from './editRenderer.js';
import { BashRenderer, BashResultRenderer } from './bashRenderer.js';
import { GrepRenderer, GlobRenderer, SearchResultRenderer } from './searchRenderer.js';
import { TodoRenderer } from './todoRenderer.js';
import { TaskRenderer } from './taskRenderer.js';
import { AskQuestionRenderer } from './askQuestionRenderer.js';

/**
 * 工具输入渲染器映射表
 * 用于渲染 tool_use 类型的消息
 */
const inputRenderers = {
    Read: ReadRenderer,
    Edit: EditRenderer,
    Write: WriteRenderer,
    Bash: BashRenderer,
    Grep: GrepRenderer,
    Glob: GlobRenderer,
    Task: TaskRenderer,
    TodoWrite: TodoRenderer,
    AskUserQuestion: AskQuestionRenderer
};

/**
 * 工具结果渲染器映射表
 * 用于渲染 tool_result 类型的消息
 */
const resultRenderers = {
    Read: FileContentRenderer,
    Edit: null,  // 使用默认渲染
    Write: null, // 使用默认渲染
    Bash: BashResultRenderer,
    Grep: SearchResultRenderer,
    Glob: SearchResultRenderer,
    Task: null,  // 使用默认渲染
    TodoWrite: null, // 使用默认渲染
    AskUserQuestion: null // 使用默认渲染
};

/**
 * 工具渲染器管理器
 */
export const ToolRenderers = {
    /**
     * 注册输入渲染器
     * @param {string} toolName - 工具名称
     * @param {Object} renderer - 渲染器对象
     */
    registerInputRenderer(toolName, renderer) {
        inputRenderers[toolName] = renderer;
    },

    /**
     * 注册结果渲染器
     * @param {string} toolName - 工具名称
     * @param {Object} renderer - 渲染器对象
     */
    registerResultRenderer(toolName, renderer) {
        resultRenderers[toolName] = renderer;
    },

    /**
     * 获取输入渲染器
     * @param {string} toolName - 工具名称
     * @returns {Object|null}
     */
    getInputRenderer(toolName) {
        return inputRenderers[toolName] || null;
    },

    /**
     * 获取结果渲染器
     * @param {string} toolName - 工具名称
     * @returns {Object|null}
     */
    getResultRenderer(toolName) {
        return resultRenderers[toolName] || null;
    },

    /**
     * 渲染工具输入
     * @param {string} toolName - 工具名称
     * @param {Object} input - 工具输入参数
     * @returns {HTMLElement|null}
     */
    renderInput(toolName, input) {
        const renderer = this.getInputRenderer(toolName);
        if (renderer && typeof renderer.render === 'function') {
            return renderer.render(input);
        }
        return null;
    },

    /**
     * 渲染工具结果
     * @param {string} toolName - 工具名称
     * @param {Object} options - 渲染选项
     * @returns {HTMLElement|null}
     */
    renderResult(toolName, options) {
        const renderer = this.getResultRenderer(toolName);
        if (renderer && typeof renderer.render === 'function') {
            return renderer.render(options);
        }
        return null;
    },

    /**
     * 检查工具是否有专用输入渲染器
     * @param {string} toolName - 工具名称
     * @returns {boolean}
     */
    hasInputRenderer(toolName) {
        return toolName in inputRenderers;
    },

    /**
     * 检查工具是否有专用结果渲染器
     * @param {string} toolName - 工具名称
     * @returns {boolean}
     */
    hasResultRenderer(toolName) {
        return toolName in resultRenderers && resultRenderers[toolName] !== null;
    },

    /**
     * 获取所有已注册的输入渲染器名称
     * @returns {string[]}
     */
    getRegisteredInputRenderers() {
        return Object.keys(inputRenderers);
    },

    /**
     * 获取所有已注册的结果渲染器名称
     * @returns {string[]}
     */
    getRegisteredResultRenderers() {
        return Object.keys(resultRenderers).filter(k => resultRenderers[k] !== null);
    },

    /**
     * 获取所有已注册的渲染器（输入+结果）
     * @returns {Object} 包含 inputRenderers 和 resultRenderers 的对象
     */
    getAllRenderers() {
        return {
            inputRenderers: { ...inputRenderers },
            resultRenderers: { ...resultRenderers }
        };
    },

    /**
     * 批量注册输入渲染器
     * @param {Object} renderers - 渲染器映射表 { toolName: renderer }
     */
    registerInputRenderers(renderers) {
        if (renderers && typeof renderers === 'object') {
            Object.entries(renderers).forEach(([name, renderer]) => {
                this.registerInputRenderer(name, renderer);
            });
        }
    },

    /**
     * 批量注册结果渲染器
     * @param {Object} renderers - 渲染器映射表 { toolName: renderer }
     */
    registerResultRenderers(renderers) {
        if (renderers && typeof renderers === 'object') {
            Object.entries(renderers).forEach(([name, renderer]) => {
                this.registerResultRenderer(name, renderer);
            });
        }
    }
};

// 导出所有渲染器
export {
    BaseRenderer,
    ReadRenderer,
    FileContentRenderer,
    EditRenderer,
    WriteRenderer,
    BashRenderer,
    BashResultRenderer,
    GrepRenderer,
    GlobRenderer,
    SearchResultRenderer,
    TodoRenderer,
    TaskRenderer,
    AskQuestionRenderer
};

// 默认导出
export default ToolRenderers;

// 别名导出（符合文档命名）
export const RendererRegistry = ToolRenderers;
