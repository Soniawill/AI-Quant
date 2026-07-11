# AI-Quant

个人 AI 量化学习仓库，按子目录存放不同项目，共用 `shared-data/` 行情数据。

## 项目目录

| 项目 | 路径 | 说明 |
|---|---|---|
| 长江电力量化分析 | `/`（根目录） | 早期练手项目 |
| MA5/MA15 交叉策略回测 | `/ma-strategy/` | 均线交叉策略 + 自动刷新 |
| 海龟交易法策略回测 | `/turtle-strategy/` | 唐奇安通道 + ATR + 自动刷新 |

## 共用数据

`shared-data/` 存放五只标的的日线行情数据：
- 香农芯创 `300475.SZ`
- 立讯精密 `002475.SZ`
- 工业富联 `601138.SH`
- 通信 ETF `515880.SH`
- 积存金 `AU9999.SGE`

## 在线报告

- 长江电力：`https://soniawill.github.io/AI-Quant/`
- MA 策略：`https://soniawill.github.io/AI-Quant/ma-strategy/`
- 海龟策略：`https://soniawill.github.io/AI-Quant/turtle-strategy/`

## 自动刷新

| 工作流 | 文件 | 频率 | 功能 |
|---|---|---|---|
| MA 策略 | `.github/workflows/refresh-ma-strategy.yml` | 每天 16:00 | 自动拉数据 → 计算 MA 信号 → 回测 → 部署 |
| 海龟策略 | `.github/workflows/refresh-turtle-strategy.yml` | 每天 16:30 | 自动读取 shared-data → 计算通道/ATR → 回测 → 部署 |

进入仓库 **Actions** 可以手动触发或查看运行记录。
