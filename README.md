# onchain-token-monitor-for-cz

链上取证 + 实时监控案例 · **CZ「The Final Form Bull」**(BSC)

> 这是 [`onchain-token-monitor`](https://github.com/minner-fun/onchain-token-monitor) 针对一个具体 BSC 代币做的**案例实例**:一份完整的链上取证报告 + 一个能直接跑的实时核查工具。
> 目标:用不可篡改的链上数据,把「谁在控盘、量是不是真的、风险悬在哪里」讲清楚。

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

---

## 数据来源

BSC 链上(Dune:`erc20_bnb.evt_transfer`、`dex.trades`)· DexScreener · GoPlus · BSC RPC(`balanceOf`)。全部查询可复现。

## 免责声明

本仓库只陈述链上行为与时间线,用于研究与风险监控演示。**不构成对任何主体的法律定性,也不构成投资建议。** 中心化交易所内部、地址背后的真实身份、以及冷钱包未来是否砸盘,均为链上不可知项。

## 关于

需要对某个代币做「谁在控盘」的取证报告,或给你的代币 / 金库做 24/7 监控?

- Portfolio: [minner.fun](https://minner.fun/) · GitHub: [github.com/minner-fun](https://github.com/minner-fun)
