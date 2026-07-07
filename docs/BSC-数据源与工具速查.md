# BSC 数据源 & 工具速查

> 做链上取证 / 监控要用到的 BSC(BNB Chain)数据源全景。按"用来干嘛"分类,每个标注:**能力**、**是否免费覆盖 BSC**、**要不要 key / 怎么拿**、**本项目怎么用**。
> 一句话先记住:**「查余额 / 读合约」用 RPC(免费);「按地址查交易历史」必须用索引 API(Ankr/Covalent/Moralis);「行情 / 成交」用 DexScreener/GeckoTerminal;「批量 SQL 分析」用 Dune;「代币安全」用 GoPlus。**

---

## 0. 一张表看懂选型

| 你想做的事 | 用什么 | 免费? |
|-----------|--------|-------|
| 查某地址的代币余额、读合约状态 | **公共 RPC**(`eth_call` / `balanceOf`) | ✅ 免费无 key |
| 查某地址的原生 BNB 余额、扫区块 | **公共 RPC**(`eth_getBalance` / `eth_getBlockByNumber`) | ✅ 免费无 key |
| **按地址查交易历史 / 转账记录** | **索引 API**:Ankr / Covalent / Moralis | ⚠️ 要各自的 key(有免费额度) |
| 查代币价格 / 流动性 / 24h 量 | **DexScreener** | ✅ 免费无 key |
| 查某池子的实时成交流、"新池子" | **GeckoTerminal** | ✅ 免费无 key |
| 批量 SQL 分析(几千地址、全网聚合) | **Dune** | ⚠️ 免费额度 + 积分 |
| 代币安全 / 是否貔貅 / 持有人 / creator | **GoPlus** | ✅ 免费无 key(限流) |
| 看单笔交易 / 合约代码(网页) | **BscScan 网站** | ✅ 免费 |

**关键坑(2026 现状)**:BscScan 的 API 已并入 **Etherscan V2 统一接口**,而且**免费档不再覆盖 BSC**(BSC 要付费档)。所以"按地址查交易"别指望免费的 BscScan key——要用 Ankr / Covalent / Moralis。

---

## 1. 区块浏览器 & 交易查询

### BscScan(网站)· https://bscscan.com
- **能力**:网页上看任意地址的交易、代币转账、持仓、合约源码、内部交易。做人工核查最顺手。
- **免费**:网页完全免费,不用登录。
- **本项目**:报告里每个地址都能在这核对;告警里的 `bscscan.com/address/…` 就是跳这。

### Etherscan V2 API(BscScan 的 API 现在长这样)
- **地址**:`https://api.etherscan.io/v2/api?chainid=56&...`(`chainid=56` = BSC)。
- **能力**:`txlist`(地址的普通交易)、`tokentx`(代币转账)、`txlistinternal`(内部交易 / 合约创建)、`getcontractcreation` 等。
- **⚠️ 免费覆盖 BSC?**:**不**。免费档只给以太坊主网;BSC 返回 *"Free API access is not supported for this chain. Please upgrade your api plan."* 要覆盖 BSC 得买付费档(有月费)。
- **key 怎么拿**:https://etherscan.io/apis 注册 → API Keys → 新建。一把 key 在 V2 里理论上多链通用,但**免费额度不含 BSC**。
- **本项目**:因此我们**没用它**——`funder` 监控改成了纯 RPC 扫区块,`factory.py --deployer` 的动态模式也受此限制。

> 记忆点:**老的 `api.bscscan.com`(V1)已废弃**,会提示你转 V2。别再找"BscScan 免费 key"了,那条路对 BSC 已经关了。

---

## 2. RPC 节点(链的"原始读接口")

RPC = 直接问节点的标准接口。**免费、无 key**,但只能做"点查",不能"按地址翻历史"。

- **常用免费端点**:`https://bsc-dataseed.binance.org`(币安官方,余额/读合约稳)、`https://bsc-rpc.publicnode.com`、`https://1rpc.io/bnb`、`https://rpc.ankr.com/bsc`。
- **能做**:
  - `eth_call` → 读合约(如 `balanceOf` 查代币余额)✅
  - `eth_getBalance` → 查原生 BNB 余额 ✅
  - `eth_getBlockByNumber(block, true)` → 拉整个区块的所有交易(含 from/to/value)✅
  - `eth_blockNumber` → 最新块高 ✅
- **不能做 / 有坑**:
  - ❌ **没有"按地址查交易"的方法**——这是 RPC 的天然缺陷,必须靠索引 API。
  - ⚠️ `eth_getLogs`(查事件日志)在免费公共节点上**普遍限流**:bsc-dataseed 直接拒(limit exceeded)、publicnode 403、1rpc 只给 50 个区块范围。要稳用得上带 key 的节点。
- **本项目**:`check.py`、`bscmon` 的余额/铡刀信号、`funder` 的余额+扫区块,全走公共 RPC。**核心信号无 key 开箱即用**就是这么来的。

---

## 3. 索引 / 数据 API(能"按地址查交易"的)★

这类服务把链数据预先索引好,所以能回答 RPC 回答不了的问题:**"地址 X 的所有交易 / 代币转账 / 发过的币"**。**这就是我们做 A(盯地址、找发币)缺的那块拼图。** 都要各自的免费 key。

### Ankr · https://www.ankr.com
- **两种东西**:
  1. **免费公共 RPC**:`https://rpc.ankr.com/bsc`(和第 2 节的 RPC 一样,点查用)。
  2. **Advanced API**(要 key):`ankr_getTransactionsByAddress`、`ankr_getTokenTransfers`、`ankr_getTokenHolders` 等,**多链(含 BSC)一个 key 全覆盖**。这就是"按地址查交易"。
- **免费覆盖 BSC?**:✅ Advanced API 有免费额度,覆盖 BSC。
- **key 怎么拿**:注册 Ankr 账号 → 建一个 Endpoint / Project → 拿到形如 `rpc.ankr.com/multichain/<KEY>` 的地址,POST `ankr_getTransactionsByAddress`。
- **适合**:实时"盯某地址的新交易 / 新发的币"。**A 方案的首选。**

### Covalent / GoldRush · https://goldrush.dev
- **能力**:统一 REST API,`/v1/56/address/{addr}/transactions_v3/`(地址全部交易)、`/v1/56/address/{addr}/balances_v2/`(全代币余额)、`/v1/56/tokens/.../token_holders_v4/`。`56` = BSC。
- **免费覆盖 BSC?**:✅ 免费档有额度(按 credits),覆盖 BSC。
- **key 怎么拿**:goldrush.dev 注册 → 拿 API Key → 请求头 `Authorization: Bearer <KEY>`。
- **适合**:一次性拉某地址的完整交易/余额历史,做深挖(B 方案很顺手)。

### Moralis · https://moralis.io
- **能力**:Web3 Data API,`getWalletTransactions`、`getWalletTokenTransfers`、`getWalletTokenBalances`、`getContractEvents`,BSC(chain=`0x38`)。
- **免费覆盖 BSC?**:✅ 免费档有月额度。
- **key 怎么拿**:moralis.io 注册 → Web3 APIs → 拿 API Key,请求头 `X-API-Key: <KEY>`。
- **适合**:和 Ankr/Covalent 同类,选一个用即可。

### 其它
- **Bitquery**(GraphQL,强大但学习曲线陡,免费额度小)、**Nodereal MegaNode**(RPC + 增强接口,免费档)。备选,不急着上。

> **给你的建议**:先注册 **一个** 就够——**Ankr(实时盯地址)** 或 **Covalent/GoldRush(拉历史深挖)**。拿到 key 给我,A 方案就能升级成"自动发现新 deployer"。

---

## 4. DEX 行情 & 成交

### DexScreener · https://dexscreener.com · api.dexscreener.com
- **能力**:`/latest/dex/tokens/{addr}` → 价格 / 流动性 / 24h 量 / FDV / 交易对。支持逗号批量(一次最多 30 个 token)。
- **免费 / key**:✅ 免费无 key,**带 CORS(`*`)浏览器可直连**。
- **本项目**:`check.py`、`factory.py`、面板、`bscmon` 的市场信号全用它。

### GeckoTerminal · https://www.geckoterminal.com · api.geckoterminal.com
- **能力**:`/networks/bsc/pools/{pool}/trades` → **实时逐笔成交(买/卖/USD/时间/tx)**;`/networks/bsc/new_pools` → **最新建的池子**;`/networks/bsc/tokens/{addr}` → 代币信息。
- **免费 / key**:✅ 免费无 key(约 30 req/min),**带 Origin 时给 CORS,浏览器可直连**。
- **本项目**:面板的**实时成交滚动**用它;**A 方案**盯"新池子"也用它。

---

## 5. 链上分析:Dune · https://dune.com
- **能力**:用 SQL(DuneSQL / Trino)查预索引的链数据。BSC 关键表:
  - `erc20_bnb.evt_transfer`(所有 ERC20 转账,含 mint from=0x0)
  - `dex.trades`(所有 DEX 成交,带 `amount_usd`)
  - `bnb.transactions`(原生交易,查资金流 / 金主出账)
  - `cex.addresses`(交易所地址标签)
  - `prices.usd`(历史币价)
- **免费 / key**:有免费额度 + 查询消耗 credits;大范围扫描(如 42 个币、5,486 个 deployer)会吃 credits。
- **本项目**:整份取证报告的重活都在这——发行结构、金主 $51M、5,936 币网络、赢家榜,全是 Dune 跑出来的。**B 方案(深挖某地址)也用它。**

---

## 6. 代币安全扫描

### GoPlus · https://gopluslabs.io · api.gopluslabs.io
- **能力**:`/api/v1/token_security/56?contract_addresses=…` → 是否貔貅、买卖税、owner 是否弃权、可否增发、LP 锁没锁、**creator 地址**、top 持有人。
- **免费 / key**:✅ 免费无 key(限流,量大可申请 key)。
- **本项目**:recon 一眼看合约安全面用它;**A 方案**里"查新币的 creator 是不是我们盯的 deployer"也靠它的 `creator_address`。

### 其它:Honeypot.is(貔貅模拟)、TokenSniffer(综合评分)——网页快查,备选。

---

## 7. 本项目用了哪些(功能 → 工具映射)

| 功能 | 用的工具 | 要 key? |
|------|----------|---------|
| 冷钱包实时余额、铡刀告警 | 公共 RPC(`balanceOf`) | 否 |
| 金主大额出账预警(funder) | 公共 RPC(`eth_getBalance` + 扫区块) | 否 |
| 价格 / 流动性 / 刷量倍数 | DexScreener + Binance ticker | 否 |
| 面板实时成交滚动 | GeckoTerminal | 否 |
| 42 币工厂尸检(factory.py) | DexScreener(批量) | 否 |
| 取证报告(发行/金主/赢家/网络) | Dune | 免费额度 |
| 合约安全面 / creator | GoPlus | 否 |
| **A 方案:盯已知 deployer 的新盘** | GeckoTerminal(new_pools)+ GoPlus(creator) | 否 |
| **A 升级:自动发现新 deployer** | Ankr / Covalent(按地址查交易) | **要 key** |
| **B 方案:深挖某地址** | Dune | 免费额度 |

---

## 8. 给你的上手清单(按顺序)

1. **先熟悉网页**:bscscan.com 随便点个地址,看它的 Transactions / Token Transfers / Internal Txns 三个页签——理解"交易 / 代币转账 / 内部交易"的区别。
2. **理解 RPC 的边界**:记住"余额能查、历史查不了"。
3. **注册一个索引 API**(二选一):
   - 想**实时盯地址** → **Ankr**(Advanced API);
   - 想**拉历史深挖** → **Covalent/GoldRush**。
   拿到 key 发我,A 方案就能自动发现新 deployer。
4. **GoPlus / DexScreener / GeckoTerminal** 不用注册,直接用。
5. **Dune** 复杂查询交给我跑(B 方案深挖)。

> 拿到 Ankr 或 Covalent 的 key 后告诉我,我把 A 方案升级成"金主给谁打钱→自动盯那个地址→抓它发的币"的全自动版。在那之前,A 先用无 key 版(盯已知 deployer + 新池子)跑起来。
