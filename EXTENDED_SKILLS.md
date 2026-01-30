# 扩展 Skills 配置说明

## 🎯 针对 LittleRedFlower 项目的专属 Skills

以下是为你的金融数据平台定制的 3 个额外 Skills，可以添加到 `.claude/skills.json`：

---

### 1️⃣ deploy-azure Skill

```json
{
  "name": "deploy-azure",
  "description": "Deploy to Azure App Service and monitor deployment status",
  "enabled": true,
  "trigger": "/deploy",
  "instructions": "When the user asks to deploy to Azure:\n1. Check current git status - ensure working directory is clean\n2. Verify latest commit is pushed to main branch\n3. Check GitHub Actions workflow status:\n   - gh run list --workflow=main_littleredflower.yml --limit 5\n   - gh run watch (if deployment in progress)\n4. Monitor deployment:\n   - Show build job status\n   - Show frontend build output\n   - Show Azure deployment status\n5. After deployment:\n   - Provide deployment URL: https://littleredflower.azurewebsites.net\n   - Suggest testing critical endpoints\n   - Check for any deployment errors\n6. Troubleshooting:\n   - Check Azure App Service logs if needed\n   - Verify environment variables\n   - Check Python/Node versions match workflow"
}
```

**使用场景**:
- 提交代码后准备部署
- 检查部署状态
- 排查部署失败问题

**示例**:
```bash
你: /deploy
Claude:
  ✓ 检查 git 状态... 干净
  ✓ 最新 commit: 6d0fe54 已推送
  ✓ 触发 GitHub Actions workflow
  ⏳ 监控部署进度...
  ✅ 部署成功! https://littleredflower.azurewebsites.net
```

---

### 2️⃣ check-ci Skill

```json
{
  "name": "check-ci",
  "description": "Check GitHub Actions CI/CD status and logs",
  "enabled": true,
  "trigger": "/ci",
  "instructions": "When the user asks about CI/CD status:\n1. List recent workflow runs:\n   - gh run list --limit 10\n2. Show details of latest run:\n   - gh run view --log (if failed)\n3. Analyze failures:\n   - Identify which job failed (build or deploy)\n   - Extract error messages\n   - Suggest fixes based on error type\n4. For this project, common issues:\n   - Frontend build failures (npm ci, npm run build)\n   - Python dependency issues\n   - Azure deployment timeout\n   - Missing secrets/env variables\n5. Provide actionable next steps"
}
```

**使用场景**:
- 快速查看 CI/CD 状态
- 分析构建/部署失败原因
- 获取修复建议

**示例**:
```bash
你: /ci
Claude:
  最近 5 次运行:
  ✅ #42 - main - 2026-01-30 23:46 (成功)
  ❌ #41 - main - 2026-01-30 22:15 (失败)

  失败原因: 前端构建失败
  错误: npm ERR! missing script: build

  建议修复:
  1. 检查 web/package.json 中是否有 "build" 脚本
  2. 确保 vite 已正确安装
```

---

### 3️⃣ validate-data Skill

```json
{
  "name": "validate-data",
  "description": "Validate financial data sources and API responses",
  "enabled": true,
  "trigger": "/validate",
  "instructions": "When the user asks to validate data:\n1. Check data source availability:\n   - Test AkShare endpoints\n   - Test yfinance for US stocks\n   - Verify Tushare Pro token (if configured)\n2. Validate API responses:\n   - Check /api/sentiment endpoint\n   - Check /api/us-tech/latest\n   - Check /api/market/radar\n   - Verify response structure matches Pydantic models\n3. Cache validation:\n   - Check cache hit rates\n   - Verify cache expiration logic\n   - Test cache invalidation\n4. Data quality checks:\n   - Verify data completeness (no missing fields)\n   - Check data freshness (timestamps)\n   - Validate data ranges (prices > 0, percentages -100 to 100)\n5. Performance metrics:\n   - Measure API response times\n   - Check concurrent request handling\n   - Verify timeout protection works\n6. Report findings with specific suggestions"
}
```

**使用场景**:
- 上线前数据验证
- 排查数据异常问题
- 性能基准测试

**示例**:
```bash
你: /validate
Claude:
  📊 数据源检查:
  ✅ AkShare (eastmoney) - 正常
  ✅ yfinance - 正常
  ⚠️  Tushare Pro - 未配置

  🔍 API 端点验证:
  ✅ /api/sentiment - 200ms
  ✅ /api/us-tech/latest - 850ms (缓存命中)
  ❌ /api/market/radar - 超时 (>10s)

  💡 建议:
  1. 优化 market/radar 端点性能
  2. 考虑添加更多缓存层
```

---

## 🔧 如何添加这些 Skills

### 方法 1: 手动编辑（推荐）

1. 打开 `.claude/skills.json`
2. 在 `"skills"` 数组的末尾添加上述 3 个 skill 对象
3. 保存文件
4. 重启 Claude Code（如果需要）

### 方法 2: 合并配置

```bash
# 备份当前配置
cp .claude/skills.json .claude/skills.json.backup

# 手动编辑添加新 skills
code .claude/skills.json
```

---

## 📊 完整 Skills 清单（8个）

| # | Skill | 触发词 | 用途 |
|---|-------|--------|------|
| 1 | commit | `/commit` | Git 提交 |
| 2 | test | `/test` | 运行测试 |
| 3 | review-pr | `/review-pr` | PR 审查 |
| 4 | fastapi-helper | `/fastapi` | API 开发 |
| 5 | react-helper | `/react` | 组件开发 |
| 6 | **deploy-azure** | `/deploy` | **Azure 部署** |
| 7 | **check-ci** | `/ci` | **CI/CD 检查** |
| 8 | **validate-data** | `/validate` | **数据验证** |

---

## 🎯 典型工作流

### 开发新功能完整流程:

```bash
# 1. 开发 API
你: /fastapi 创建一个获取龙虎榜数据的端点

# 2. 开发前端
你: /react 创建龙虎榜数据展示组件

# 3. 运行测试
你: /test

# 4. 验证数据
你: /validate

# 5. 提交代码
你: /commit

# 6. 检查 CI/CD
你: /ci

# 7. 部署到 Azure
你: /deploy
```

---

## 📚 Anthropic 官方 Skills 资源

目前 Anthropic 官方主要提供:
- **内置 Skills**: commit, review-pr, keybindings-help
- **Skills 框架**: 允许用户自定义 Skills（就像我们创建的这些）

官方文档:
- Claude Code 文档: https://docs.anthropic.com/claude-code
- Skills 配置格式: JSON 配置文件 + 自然语言指令

---

## 💡 提示

1. **显式触发更可靠**: 使用 `/deploy` 比说"帮我部署"更准确
2. **Skills 可组合**: 可以在一个任务中触发多个 Skills
3. **自定义指令**: 可以根据项目需求调整 instructions
4. **定期更新**: 随着项目演进，更新 Skills 配置

---

需要帮助添加这些 Skills? 告诉我！
