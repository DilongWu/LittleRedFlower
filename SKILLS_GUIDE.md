# Skills Configuration Guide for LittleRedFlower Project

## ✅ Skills 已配置完成！

我已经为你的项目创建了 **5 个专业 Skills**，配置文件在 `skills_config.json`

---

## 🎯 什么是 Skills？

**Skills 是 Claude Agent 的"专业工具包"**，当你要求 Claude 执行某个任务时：

```
你的请求 → Claude 检查可用 Skills → 使用对应的最佳实践 → 执行任务
```

### 类比理解：
- **没有 Skills**：Claude 像一个通用工人，什么都会一点
- **有了 Skills**：Claude 像专家团队，每个人精通一个领域

---

## 📦 已安装的 5 个 Skills

### 1️⃣ **commit** - Git 提交助手
**触发方式**: `/commit` 或 "帮我提交代码"

**做什么**:
- 分析 `git diff` 和 `git status`
- 生成符合规范的 commit message
- 自动区分中英文场景（A股功能用中文，技术改动用英文）

**示例**:
```bash
# 你修改了美股数据接口
你: /commit

Claude 会:
1. 运行 git diff 查看改动
2. 分析修改内容
3. 生成: "feat(us-stocks): add multi-threading for data fetching"
4. 执行: git commit -m "..."
```

---

### 2️⃣ **test** - 测试执行器
**触发方式**: `/test` 或 "运行测试"

**做什么**:
- 自动找到所有 test_*.py 文件
- 运行 pytest 并生成报告
- 分析失败原因并给出修复建议

**示例**:
```bash
你: /test api/services/us_stocks.py

Claude 会:
1. 运行: pytest test_us_stocks.py -v
2. 显示测试结果
3. 如果失败，分析原因
4. 给出修复代码建议
```

---

### 3️⃣ **review-pr** - 代码审查助手
**触发方式**: `/review-pr 42` 或 "审查 PR #42"

**做什么**:
- 获取 PR 的代码变更
- 重点检查：API 破坏性变更、安全问题、性能影响
- 给出改进建议

**示例**:
```bash
你: /review-pr 42

Claude 会检查:
✓ API 接口是否有破坏性变更
✓ 数据源错误处理是否完整
✓ 缓存逻辑是否正确
✓ 是否有安全风险（API Key 泄露）
✓ 文档是否更新
```

---

### 4️⃣ **fastapi-helper** - FastAPI 开发助手
**触发方式**: `/fastapi` 或 "创建一个新的 API 端点"

**做什么**:
- 遵循 FastAPI 最佳实践
- 自动添加 Pydantic 验证
- 生成 OpenAPI 文档
- 检查异步操作正确性

**示例**:
```bash
你: /fastapi 帮我创建一个获取 A 股指数的端点

Claude 会:
1. 使用 Pydantic 定义响应模型
2. 添加 async/await（因为涉及 I/O）
3. 包含完整的文档字符串
4. 添加错误处理
5. 添加到合适的 router
```

**生成代码示例**:
```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class IndexResponse(BaseModel):
    """A股指数响应模型"""
    code: str
    name: str
    price: float
    change_pct: float

@router.get(
    "/api/index/{code}",
    response_model=IndexResponse,
    summary="获取A股指数详情",
    description="根据指数代码获取实时行情数据"
)
async def get_index_detail(code: str):
    """获取指数详情

    Args:
        code: 指数代码（如 000001 表示上证指数）

    Returns:
        IndexResponse: 指数详细信息
    """
    try:
        # 业务逻辑...
        pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

### 5️⃣ **react-helper** - React 开发助手
**触发方式**: `/react` 或 "创建一个新的 React 组件"

**做什么**:
- 使用 React 18 最佳实践
- 正确使用 hooks
- 实现加载和错误状态
- 性能优化（useMemo, useCallback）

**示例**:
```bash
你: /react 创建一个股票价格卡片组件

Claude 会:
1. 使用函数组件 + hooks
2. 添加 loading/error 状态处理
3. 使用 Lucide React 图标（已安装）
4. 实现 memo 优化
5. 添加 PropTypes 验证
```

**生成代码示例**:
```jsx
import { memo, useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Loader2 } from 'lucide-react';

const StockCard = memo(({ symbol, name }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await fetch(`/api/stock/${symbol}`);
        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [symbol]);

  if (loading) return <Loader2 className="animate-spin" />;
  if (error) return <div>Error: {error}</div>;

  const isUp = data.changePct > 0;

  return (
    <div className="stock-card">
      <h3>{name}</h3>
      <div className="price">
        {data.price}
        {isUp ? <TrendingUp /> : <TrendingDown />}
      </div>
      <span className={isUp ? 'up' : 'down'}>
        {data.changePct > 0 ? '+' : ''}{data.changePct}%
      </span>
    </div>
  );
});

export default StockCard;
```

---

## 🚀 如何使用 Skills？

### 方法 1: 使用触发词（推荐）
```
/commit
/test
/review-pr 42
/fastapi
/react
```

### 方法 2: 自然语言
```
"帮我提交代码"           → 触发 commit skill
"运行所有测试"           → 触发 test skill
"审查最新的 PR"          → 触发 review-pr skill
"创建一个新的 API"       → 触发 fastapi skill
"写一个 React 组件"      → 触发 react skill
```

---

## 🔧 手动激活 Skills（如果需要）

如果 Skills 没有自动生效，请运行：

```bash
# 移动配置文件到 Claude 目录
mv skills_config.json .claude/skills.json

# 或者手动创建软链接
ln -s $(pwd)/skills_config.json ~/.claude/skills.json
```

---

## 💡 Skills 工作原理

```
┌─────────────┐
│ 你的请求    │
└──────┬──────┘
       │
       ▼
┌─────────────────────────┐
│ Claude 分析请求         │
│ "这个任务需要 commit"   │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│ 加载 commit skill       │
│ 读取最佳实践指令        │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│ 执行任务                │
│ - git diff              │
│ - 分析变更              │
│ - 生成 commit message   │
│ - git commit            │
└─────────────────────────┘
```

---

## 📊 Skills vs 没有 Skills 的对比

| 任务 | 没有 Skills | 有 Skills |
|------|------------|----------|
| **提交代码** | 你自己写 commit message | Claude 分析代码自动生成规范 message |
| **运行测试** | 手动 pytest | Claude 自动找测试文件 + 生成报告 + 分析失败 |
| **代码审查** | 你自己逐行看代码 | Claude 自动检查安全/性能/最佳实践 |
| **写 API** | 可能漏掉验证/文档 | Claude 自动添加 Pydantic + 文档 + 错误处理 |
| **写组件** | 可能忘记优化 | Claude 自动添加 memo + loading 状态 + 错误处理 |

---

## 🎯 实战示例

### 场景 1: 开发新功能
```
你: 我想添加一个 A 股龙虎榜数据的 API

Claude (自动触发 fastapi skill):
✓ 创建 Pydantic 模型
✓ 添加路由端点
✓ 实现数据获取逻辑
✓ 添加错误处理
✓ 生成 API 文档
✓ 创建对应的前端组件（触发 react skill）

你: /test

Claude (触发 test skill):
✓ 创建测试文件 test_longhubang.py
✓ 运行测试
✓ 报告结果

你: /commit

Claude (触发 commit skill):
✓ 分析代码变更
✓ 生成: "feat(龙虎榜): 新增龙虎榜数据API及前端展示"
✓ 提交代码
```

### 场景 2: 修复 Bug
```
你: test_us_stocks.py 测试失败了，帮我看看

Claude (自动触发 test skill):
✓ 运行 pytest test_us_stocks.py -v
✓ 分析错误日志
✓ 定位问题：缓存键名不一致
✓ 给出修复代码

你: 帮我修复

Claude:
✓ 修改 us_stocks.py
✓ 重新运行测试
✓ 测试通过！

你: /commit

Claude (触发 commit skill):
✓ 生成: "fix(us-stocks): resolve cache key mismatch issue"
```

---

## ⚙️ 配置文件位置

- **项目配置**: `.claude/skills.json`（项目特定）
- **全局配置**: `~/.claude/skills.json`（所有项目共享）
- **临时文件**: `skills_config.json`（需手动移动到 .claude 目录）

---

## 🔍 验证 Skills 是否生效

在 Claude Code 中输入：
```
/commit
```

如果 Claude 开始分析 git 状态，说明 skill 已生效！ ✅

---

## 🎓 总结

**你的理解完全正确！**

> Skills 就是让 Claude Agent 在执行任务时能更专业、更规范、更高效。

**类比**：
- **没有 Skills** = 雇了一个全能助手（什么都会一点）
- **有了 Skills** = 雇了一个专家团队（每个人精通一项）

当你说"提交代码"时，commit skill 确保 Claude 会：
✓ 检查 git 状态
✓ 分析代码变更
✓ 生成规范的 commit message
✓ 遵循你的项目风格（中英文混合）

而不是随便写一个简单的 commit message！

---

需要我：
1. ✅ **演示如何使用这些 Skills**？（比如现在就试试 /commit）
2. 📝 **创建更多自定义 Skills**？（比如"金融数据验证 skill"）
3. 🔧 **调整 Skills 配置**？（修改触发条件或行为）

告诉我你想试试哪个！🚀
