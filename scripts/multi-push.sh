#!/bin/bash

# 多远程仓库推送脚本
# 用于同时向GitHub和Gitee推送代码

set -e  # 遇到错误时退出

echo "🚀 开始多远程仓库推送..."

# 检查当前Git状态
if [[ -z $(git status --porcelain) ]]; then
    echo "✅ 工作目录干净，准备推送"
else
    echo "⚠️  工作目录有未提交的更改，请先提交或暂存"
    git status --short
    read -p "是否继续推送? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 获取当前分支
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "📋 当前分支: $CURRENT_BRANCH"

# 检查远程仓库配置
echo "🔍 检查远程仓库配置..."
git remote -v

# 推送到GitHub
echo "📤 正在推送到GitHub..."
if git push origin "$CURRENT_BRANCH"; then
    echo "✅ GitHub推送成功"
else
    echo "❌ GitHub推送失败"
    exit 1
fi

# 推送到Gitee
echo "📤 正在推送到Gitee..."
if git push gitee "$CURRENT_BRANCH"; then
    echo "✅ Gitee推送成功"
else
    echo "❌ Gitee推送失败"
    exit 1
fi

echo "🎉 所有推送完成！"
echo "📊 推送状态:"
echo "  - GitHub: $(git rev-parse HEAD)"
echo "  - Gitee:  $(git rev-parse HEAD)"
