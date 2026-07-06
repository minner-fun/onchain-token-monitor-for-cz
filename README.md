# onchain-token-monitor-for-cz

链上取证 + 实时监控案例 · **CZ「The Final Form Bull」**(BSC)

### 👉 [**实时网页面板 · cz.minner.fun**](https://cz.minner.fun/)
> 冷钱包实时余额、筹码分布、刷量倍数、**实时链上成交滚动**、42 币工厂存活数——打开即看,自动刷新。

### 🔔 [**订阅铡刀异动告警 · @minner_cz_bot**](https://t.me/minner_cz_bot)
> 那 7 亿冷钱包一动,第一时间推你 Telegram。扫码订阅:
>
> <img src="docs/qr-bot.png" alt="订阅 @minner_cz_bot" width="150">


> 这是 [`onchain-token-monitor`](https://github.com/minner-fun/onchain-token-monitor) 针对一个具体 BSC 代币做的**案例实例**:一份完整的链上取证报告 + 实时核查工具 + 网页面板 + 24/7 服务器监控。
> 目标:用不可篡改的链上数据,把「谁在控盘、量是不是真的、风险悬在哪里」讲清楚。

---

## 这套「案例」包含什么

| 交付物 | 说明 | 入口 |
|--------|------|------|
| 🖥️ **实时网页面板** | 冷钱包实时余额 · 筹码分布 · 刷量倍数 · **实时成交滚动** · 42 币工厂存活数 · 二维码,自动刷新 | [cz.minner.fun](https://cz.minner.fun/) |
| 📋 **中文取证报告** | 10 节 + 附录,证据分级(✅/🔶/⛔)、全地址可核验 | [docs/报告](docs/报告-CZ-The-Final-Form-Bull.md) |
| ⚡ **`check.py`** | 无需 key,一次性核查单盘(冷钱包动没动 + 量是不是刷的) | ↓ 见下 |
| 🏭 **`factory.py`** | 42 币工厂尸检(现在还剩几个活的) | ↓ 见下 |
| 📡 **`bscmon`** | 24/7 服务器监控,冷钱包异动 → Telegram | ↓ 见下 |
| 🔔 **订阅 Bot** | `/start` 订阅广播 · `/status` 查现状 · `/subs`(管理员) | [@minner_cz_bot](https://t.me/minner_cz_bot) |

---

## 📋 取证报告(先看这个)

**[docs/报告-CZ-The-Final-Form-Bull.md](docs/报告-CZ-The-Final-Form-Bull.md)**

一句话结论:

> 发行 CZ 的地址是一台 **6 天量产 42 个代币(全 `…4444` 靓号)的土狗工厂**,CZ 只是第 3 号产品,背后还有一个分发过 **2 万+ BNB(~$1,100 万)** 的金主钱包供血。就 CZ 一个盘:一个地址发行 51 秒内就把 **70% 供应量锁进冷钱包、至今一枚未动**;这 700M 免费铸的、币价 3 天被刷量拉 **260 倍**、现值 **~$2,850 万**,而项目方真实现金投入几乎为零(~$1 万流动性、当天已卖币回本)。$1.1 亿「成交量」建在 **86 万美元流动性**上——量是「做」出来的;真正吃到拉盘的是一个 **`0x4337…` 出货家族**(前 15 名提走 ~$2.1M、几乎没花钱买)。**近乎零成本的免费筹码 + 人为放量,风险全在买盘一侧。**

报告里每条结论都标了证据等级(✅ 实证 / 🔶 推断 / ⛔ 不可知),并附全部关键地址,可自行核验。

---

## ⚡ 实时核查工具(能直接跑)

`check.py`:无需 API key,直接从 BSC 节点读每个关键钱包的**实时余额**,从 DexScreener 读价格 / 流动性 / 成交量,一眼看清两件事——**70% 冷钱包动没动、成交量是不是虚的**。

```bash
pip install pyyaml
python check.py
```

实测输出(节选):

```
=== CZ (The Final Form Bull) · BSC ===
price $0.0466 | liq $830,529 | vol24h $49,550,978
vol/liq turnover: 59.7x  <-- INFLATED: volume can't be organic at this ratio

watched wallets (live balanceOf):
  Cold wallet (70% guillotine)   700,006,211  (70.00%)  0x28816c4c...29307
     ✅ still dormant (guillotine intact)
```

> 换句话说:**任何人现在跑一遍,都能看到那 7 亿枚(70%)还原封不动地压在市场头上。** 一旦这个数字开始下降,就是最高级别的离场信号。

---

## 🏭 工厂扫描器(`factory.py`)—— 一眼看穿「土狗流水线」

发行 CZ 的地址 `0x1bff8f0a…` 是一台**代币工厂**:6 天量产 42 个代币(全 `…4444` 靓号)。`factory.py` 内置了这 42 个链上追出来的地址,跑一遍 DexScreener 出**尸检报告**——现在还剩几个活的:

```bash
python factory.py
```

实测(节选):

```
  #  launched   symbol        liquidity      24h vol  status
  3  2026-07-03 CZ             $780,295  $40,329,886  ✅ alive  ← CZ（工厂最成功的一个）
  8  2026-07-04 HEYI           $143,615   $4,234,300  ✅ alive
  6  2026-07-04 HEYI                 $0      $59,560  💀 DEAD
 33  2026-07-06 红牛                   $0     $180,499  💀 DEAD
 42  2026-07-06 屁股决定脑袋               $0      $21,917  💀 DEAD

Body count: 16/42 already dead, 26 still trading.
```

名字全是回收的币安 / CZ 叙事——多个 `HEYI`(何一)、`BINANCIAN`、`🔶 BNB`、`CZ / CZ2.0 / CZ3.0`、`红牛 / 金牛 / 登天牛`……**一条把「币安人物」当模板批量生产的流水线,CZ 只是碰巧拉得最猛的那个。**

> 动态模式(查任意部署者,需免费 BscScan key):`BSCSCAN_API_KEY=... python factory.py --deployer 0x…`

---

## 📡 24/7 常驻监控(`bscmon`)

`check.py` 是一次性快照;`bscmon/` 是常驻守护进程,把信号做成 24/7 自动监控 + **Telegram 告警**(架构思路复用 `onchain-token-monitor`)。

```bash
python -m bscmon.run --once     # 自检:各任务跑一次,写入 data/cz_monitor.db
python -m bscmon.run            # 常驻:按间隔轮询,冷钱包一动就推 Telegram
```

Telegram 可选:在 `.env` 填 `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`(不填则只打印+写库)。

| 信号 | 监控对象 | 触发 | 告警级别 |
|------|----------|------|----------|
| 🔴 **铡刀异动** | 冷钱包 `0x28816c4c…` 余额 | 余额下降 = 70% 开始动 → 顶级离场信号 | **critical(推 Telegram)** |
| 🔻 **部署者出货** | 部署者 `0x1bff8f0a…` | 余额下降 / 转出 | warn(推) |
| 🤖 **虚假放量** | vol24h ÷ 流动性 | 比值畸高 = 量是刷的 | info(只写库,不推) |

**核心信号(冷钱包异动)用 `balanceOf` 轮询,任何公共 BSC 节点都能跑,开箱即用。**
要额外**命名转出去向**(进池 / 进 CEX / 拆分到新地址)需要 `eth_getLogs`——公共免费节点大多限制它,把 `.env` 里的 `BSC_RPC` 指向一个支持 logs 的节点(自建 / Ankr / Alchemy / QuickNode)即可;不配也不影响铡刀告警。

配置见 [`config.yaml`](config.yaml)(全部地址已链上核实)。

### 🔔 订阅 Bot([@minner_cz_bot](https://t.me/minner_cz_bot))

铡刀告警不只推给自己——**任何人 `/start`(或扫面板二维码)即订阅,冷钱包异动时群发所有订阅者**。

| 指令 | 谁能用 | 作用 |
|------|--------|------|
| `/start` | 所有人 | 订阅铡刀异动告警 + 欢迎语 |
| `/status` | 所有人 | 实时现状:价格 / FDV / 流动性 / 换手 / 冷钱包余额与状态 |
| `/subs` | **仅管理员** | 订阅者列表(别人调用返回无权限) |

---

## 数据来源

BSC 链上(Dune:`erc20_bnb.evt_transfer`、`dex.trades`)· DexScreener · GoPlus · BSC RPC(`balanceOf`)。全部查询可复现。

## 免责声明

本仓库只陈述链上行为与时间线,用于研究与风险监控演示。**不构成对任何主体的法律定性,也不构成投资建议。** 中心化交易所内部、地址背后的真实身份、以及冷钱包未来是否砸盘,均为链上不可知项。

## 关于

需要对某个代币做「谁在控盘」的取证报告,或给你的代币 / 金库做 24/7 监控?

- Portfolio: [minner.fun](https://minner.fun/) · GitHub: [github.com/minner-fun](https://github.com/minner-fun)
