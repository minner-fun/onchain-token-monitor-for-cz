# onchain-token-monitor-for-cz

链上取证 + 实时监控案例 · **CZ「The Final Form Bull」**(BSC)

> 这是 [`onchain-token-monitor`](https://github.com/minner-fun/onchain-token-monitor) 针对一个具体 BSC 代币做的**案例实例**:一份完整的链上取证报告 + 一个能直接跑的实时核查工具。
> 目标:用不可篡改的链上数据,把「谁在控盘、量是不是真的、风险悬在哪里」讲清楚。

---

## 📋 取证报告(先看这个)

**[docs/报告-CZ-The-Final-Form-Bull.md](docs/报告-CZ-The-Final-Form-Bull.md)**

一句话结论:

> 一个地址在发行 51 秒内就把 **70% 的总供应量锁进一个冷钱包、至今一枚未动**;真实可流通盘只有约 10%;而链上 3 天刷出约 **1.1 亿美元成交量**,却建立在仅 **86 万美元流动性**之上——量是「做」出来的,不是「买」出来的。上方永远悬着一把 70% 的铡刀。

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

## 📡 完整监控设计(4 个信号)

`check.py` 是一次性快照;完整版把这 4 个信号做成 24/7 自动监控 + Telegram 告警(架构复用 `onchain-token-monitor`):

| 信号 | 监控对象 | 触发 = |
|------|----------|--------|
| 🔴 **铡刀异动** | 冷钱包 `0x28816c4c…` 余额 / 转出 | 任何转出 → 顶级离场信号(critical) |
| 🔻 **部署者出货** | 部署者 `0x1bff8f0a…` → 池 / CEX | 持续供货 / 加速(warn) |
| 🤖 **虚假放量** | vol24h ÷ 流动性 | 比值畸高 = 量是刷的(info) |
| 🟢 **托价/对敲舰队** | 做市地址活跃度 | 舰队停摆 = 撑盘结束(warn) |

配置见 [`config.yaml`](config.yaml)(全部地址已链上核实)。

---

## 数据来源

BSC 链上(Dune:`erc20_bnb.evt_transfer`、`dex.trades`)· DexScreener · GoPlus · BSC RPC(`balanceOf`)。全部查询可复现。

## 免责声明

本仓库只陈述链上行为与时间线,用于研究与风险监控演示。**不构成对任何主体的法律定性,也不构成投资建议。** 中心化交易所内部、地址背后的真实身份、以及冷钱包未来是否砸盘,均为链上不可知项。

## 关于

需要对某个代币做「谁在控盘」的取证报告,或给你的代币 / 金库做 24/7 监控?

- Portfolio: [minner.fun](https://minner.fun/) · GitHub: [github.com/minner-fun](https://github.com/minner-fun)
