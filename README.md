# AI-Quant

个人 AI 量化学习仓库，按子目录存放不同项目。

## 项目目录

| 项目 | 路径 | 说明 |
|---|---|---|
| 长江电力量化分析 | `/`（根目录） | 早期练手项目 |
| MA5/MA15 交叉策略回测 | `/ma-strategy/` | 五只标的均线交叉策略分析 + 自动刷新报告 |

## 在线报告

- 长江电力：`https://soniawill.github.io/AI-Quant/`
- MA 策略：`https://soniawill.github.io/AI-Quant/ma-strategy/`

## 自动刷新

MA 策略报告配置了 GitHub Actions 定时任务：

- 工作流文件：`.github/workflows/refresh-ma-strategy.yml`
- 运行频率：每天北京时间 16:00（UTC 08:00）
- 功能：自动拉取最新行情 → 计算信号 → 回测 → 生成 `index.html` → 部署到 GitHub Pages

如需手动触发，进入仓库 **Actions** → **定时刷新 MA 策略报告** → **Run workflow**。

## 本地开发

进入对应子目录后按该项目的 README 操作即可。
