# 闸 limit 真源闭集：兼容 basalt 启动配置形制＋废除硬编码兜底（rev14）— 施工票

## 票头（登记区）

- 票 ID：`2026-11-19-ledger-gate-limit-truth-source`
- 票名：闸 limit 真源闭集：兼容 basalt 启动配置形制＋废除硬编码兜底（rev14）
- 票型：功能新增＋口径修订（施工票通道；票种效力＝改动授权（候裁＝H-1 一项＝失败态新语义，放行前不得默认生效），不承载终局判定）
- 起草席位／修票权席位：架构席
- 开端读数：ANCHOR＝`2f50a645bbce7e1459046857e645d78e81263fc8`（本席当轮实跑 `git -C D:\Projects\strata-ledger-proxy rev-parse HEAD` ＝ 该值，main＝rev13 v2 票投递头；`git status --short` ＝ ` M CHANGELOG.md / M MANIFEST.md / M README.md / M bootstrap.py / M daily_report.py / ?? .scratch/ / ?? selftest_daily_report.py`＝**rev13 施工在途面**，见④施工面纪律）。代码面另证：`git diff f775864 HEAD -- collector_proxy.py selftest_proxy.py monitor_ext.py` 空＝本票三张主改文件在 f775864→ANCHOR 区间零改动，rev12 完工头锚点全部有效。
- 决策输入件（唯一口径真源，票面不得重开人类已裁口径）：
  1. **本票效力来源**＝人类 10:35 逐字原件＋B1 登记：`D:\Strata\.workbuddy\collab\input\2026-11-19-1035-gate-limit-basalt-verbatim.md`（本票实读引用）——「我认为可以对网关做一下升级，去兼容 basalt 而不是用硬编码兜底并发量！实际终端能承载的并发量真源只能由人类写进 parallel」。主理人路由注记（同件在册）两条诉求＝①解析器兼容 basalt 启动配置形制（basalt config v2 的 parallel 在 model 条目内，非顶层）；②废除「读不到 parallel →退静态 max_inflight 硬编码顶替执法」失败态——**真源闭集＝只认人类写进启动配置的 parallel；网关不许自创、也不许用备用数字顶替真源执法**。路由注记明示「失败态新语义涉安全口径，票面须列候裁呈决策者」＝本票 H-1。
  2. 被承接件：rev11/rev11a（跟随链与 mtime 守卫缓存形态＝本票改造基座）、rev12（gate-events 三行闭集＋红线六＝本票冻结面，完工 HEAD＝f775864）、rev13（日报闸统计，票 v2 已投、QA 复审在途、施工未提交＝本票禁动面）。全部 append-only 不回改。
  3. 衔接调研件（本票实读引用）：`D:\Strata\.workbuddy\collab\research\basalt-gw-compat-2026-11-19.md`——basalt serve 壳 fork 自 Strata，API/usage 字段逐字兼容；唯 config v2 把 `parallel` 放 model 条目；现解析器读 basalt 文件读不到顶层 parallel＝静默退兜底＝「跟随静默失效」。
- 架构席起草实核（本席当轮实跑，读数在册）：
  - 三套回归基线（母本仓根实跑）：`python selftest_proxy.py`＝**45/45 PASS**、`grep -c '^PASS  gate:'`＝**23**；`selftest_monitor.py`＝**54/54**；`selftest_watchdog.py`＝**16 passed 0 failed**。
  - 现闸跟随实现（ANCHOR 实读锚点）：`collector_proxy.py`（1041 行）`GATE_DEFAULTS` 83 行／`_last_limit` 279 行／`_strata_parallel_parse` 292 行／`_strata_parallel_cache` 318 行／`_strata_parallel_limit` 323 行／`_gate_params` 353 行（**383 行失败态＝`limit = v if v is not None else static_limit`＝本票废除对象**）；`_append_line` 904 行；main 挂点注释 1023-1025 行。
  - basalt 形制实核（只读源 `D:\Strata\.scratch\basalt-src`，serv/config.py 实读）：config v2 顶层闭集键＝`version/server/engine/models`（151-164 行 `read_config`：**意外顶层键直接拒**＝两键并存文件中顶层 `parallel` 在 basalt 侧非法，为形制判别提供依据）；`parallel` ∈ MODEL_OPTIONS 26 行（可写 model 条目）；顶层 `engine` 段可被 model 条目继承（89-90 行注释＋196-203 行装配）；缺省＝1（527-528 行 `--parallel` help「default 1」）；`PARALLEL_MAX=8`（21 行，钳制属引擎业务沿 rev11a A-4）；`models` 必须非空 dict 列表（178-179 行）。
  - 在岗实配（只读）：`D:\Strata-toolkit\strata-ledger-proxy\config.json` 现值 `max_inflight:2, gate_follow:true, strata_config:"D:\\Strata\\strata-unsloth-ud-iq4_xs.json"`；该启动配置文件顶层 `"parallel": 2`（Strata 形制实存）。母本仓 `config.json` 无三键（untracked，在岗另配）。
  - 可观测面实核：`monitor_ext.py` 白名单摘键（561-564 行 `{k: g[k] for k in ("inflight","queued","limit","waited_total","beat_total")}`）＝ext.json gate 段六键扩展的必经点；`_push_gate`（collector_proxy 282-289 行）＝快照生产点；selftest_proxy 24 号断言用 `set(g) >= {五键}` 子集判定＝加键不炸既有断言；`monitor.js` 只消费 `queued/limit`＝零波及。
  - gate-events 冻结面实核：selftest_proxy 354-356 行 `GEV_FIELDS`/`GEV_SEP_KEYS`＝rev12 闭集；本票**零事件字段增减**＝该组断言（G-A/G-D/23 号等）零改动。
  - 解析器候选体实跑：本席 scratch 盒 `D:\Projects\strata-ledger-proxy\.scratch\rev14-gate-limit-truth-source\`（`region.py`＋`probe.py`）＝16 fixture 断言全过（Strata 顶层/缺键/bool 值/0 值、basalt 条目/两键并存/条目 max/engine 继承/engine 坏值/空 models/models 非列表/条目非 dict/顶层 list、坏 JSON、缺文件）；候选体哈希（规范化 CRLF＋去尾空行后 sha256 前 8）＝**`1166d156`**，票内 ③-7 探针逐字对拍。
- 前置票：rev10、rev10a、rev11、rev11a、rev12（完工 HEAD＝f775864）；rev13（并行在途，文件交集＝零，见④）
- 候裁点：**H-1 一项**（失败态新语义三选项＝真源缺失时闸怎么办——人类原话直指该行为、路由注记明列候裁呈决策者＝决策者保留闸，**不随票默认放行**）
- Agent 适配度：内部票·适配度不适用
- 修订记录：**v1**（初稿；母本仓除本票文件外零触碰；票未放行、零施工）

### 准入四判据自查（票面自证）

1. **无 API 变更**：对外 HTTP 面零改动；`/ext.json` gate 段增一枚 `limit_src` 键（子集判定既有断言不炸、monitor.js 零消费＝②-3 G-4/G-5）；`requests-*.jsonl` 与 `gate-events-*.jsonl` 两文件面格式**零改动**（GEV_FIELDS 闭集不回改）。
2. **口径已裁**：真源闭集＝人类写进启动配置的 parallel（10:35 已裁）；basalt 形制要兼容（10:35 已裁）；硬编码兜底要废（10:35 已裁）——**唯失败态「闸怎么办」人类未裁＝H-1 上楼**；其余（形制判别规则、多条目聚合、继承读点、可观测落点、max_inflight 键去留随 H-1 联动、测试形态）＝装配细节，票裁 A-1～A-8 决毕，不上楼。
3. **可机械验收**：③节全部判据＝命令＋期望读数（闭集核验、写死代码体哈希探针、三套逐套报数新期望 48/48＋gate 26、失败态 ledger-service.log 告警行 grep、ext.json limit_src 读数、结构计数不变面）。
4. **不触真源**：六票 append-only 不回改；在岗机 `D:\Strata-toolkit\` 零触碰；引擎侧配置与 `D:\Strata\strata-unsloth-ud-iq4_xs.json` 零触碰；`daily_report.py` 零触碰（rev13 领地）；requests 记账账本格式零触碰。

---

## 票体四字段（自包含）

### ① 目标

闸 limit 跟随器（`_strata_parallel_parse`/`_strata_parallel_limit`，rev11a 形态）两改：

1. **解析器兼容两类启动配置形制**：Strata 形制（顶层 `parallel`）与 basalt config v2 形制（`parallel` 在 `models` 条目内，顶层 `engine` 段可继承）。形制判别＝纯结构判别（②-3 G-1 写死），**禁按文件名猜**。
2. **废除硬编码兜底失败态（本 rev 核心）**：现失败态（文件缺/JSON 坏/顶层无键）＝「退 config.json 里写死的 `max_inflight` 顶替执法」整条废除。真源闭集＝只认人类写进启动配置的 parallel；读不到真源时**任何网关侧数字不得顶替**。失败态具体语义＝三选项候裁（H-1，票给建议＋利害＋立场，见候裁单列；本票 ②-3 施工规格按**建议态甲（无真源＝不执法＋显式告警＋自愈）**写死——H-1 若裁乙/丙走回流件改票后施工，见候裁单列）。

配套：limit 来源可观测（ext.json gate 段新增 `limit_src` 键）；`max_inflight` 键语义重新登记（不再被跟随态消费，保留为**非跟随模式**的静态上限——随 H-1 联动，见 A-6）；README/MANIFEST/CHANGELOG/config.template.json 同步登记。

**换脑依赖声明（沿 rev13 例）**：rev14 上线**不依赖**换脑完成——全部验收在测试环境（selftest 起进程）可判；在岗生效依赖换脑（现岗 rev11a 脑，rev12 换脑已排 03:00 静默窗，rev14 排在其后由主理人另排窗，不入本票验收）。完工终态＝③节判据逐条读数达标＋三套回归全绿（proxy **48/48**（gate **26**）、monitor 54/54、watchdog 16/0）。

### ② 规格

#### ②-0 红线纪律（一票到底，违一条即整票判红）

- **红线一（真源闭集·人类 10:35 字面）**：跟随态的有效 limit **只**能来自 `strata_config` 所指文件的 parallel（顶层／models 条目／engine 段三读点之一）；**失败态禁任何网关侧数字顶替执法**（`max_inflight`、字面常量、缓存旧值、猜值一律禁）。机检＝③-3（`_gate_params` 旧兜底行删除行＋diff 新增面禁 `else static_limit` 形态）＋新断言（失败态零执法＋limit_src 读数）。
- **红线二（rev12 冻结面）**：`Gate` 类 token 闭集沿 rev12 ③-8 全套零改动（`git diff -w` 口径）；`GEV_FIELDS`/`GEV_SEP_KEYS` 两常量与事件行字段闭集零增减；`queue_wait_ms` 写点零改动；总账 rec 字典零新增键。机检③-4/③-5。
- **红线三（缺省零回归）**：`gate_follow` 缺省 false＝非跟随路径逐字节不变（`limit = static_limit` 原语义保留）；闸关（limit 0）时行为与 ANCHOR 一致（零 gate-events 文件、ext.json 无 gate 段）。既有 selftest_proxy 45 断言中**非跟随 21 名全部零改**；改体仅限跟随组 2 名（K-1/A-4ff 反向改判）＋1 名扩判据（A-4/24 号）；新断言只增（gate 23→**26**，N 45→**48**）。monitor 54/54、watchdog 16/0 两文件零触碰原样通过（机检③-2）。
- **红线四（热路径纪律）**：每对话请求仍＝一次 `os.stat`＋元组比较，守卫命中零 open 零 parse；**禁每请求重读解析**（mtime 守卫缓存纪律不变）；零新增上游调用（`urlopen` 计数仍＝3）、零新增锁、零新增线程（告警去抖用无锁 bool——良性竞争：告警行最多多写/少写一行，不涉执法正确性，登记 A-7）。`global _strata_parallel_cache` 声明坑（rev11 D1/rev11a B-1 同族两犯史）＝写死代码体内声明在场，③-7 哈希探针覆盖。机检③-6。
- **红线五（禁动面互不侵犯）**：`daily_report.py` 零触碰（rev13 领地，其 C1/C2 态读 `max_inflight`/`gate_follow` 两键的判别在本票后仍成立——两键键名与在场性不变，登记④）；`selftest_daily_report.py`（rev13 在途新文件）零触碰；rev10/rev10a/rev11/rev11a/rev12/rev13 六票本体＋勘误件 append-only 不回改。

#### ②-1 声明闭集（本票唯一可写仓内面）

```
collector_proxy.py
selftest_proxy.py
monitor_ext.py            (仅白名单一行，G-5)
config.template.json      (comment 口径整改＋零新键)
README.md
MANIFEST.md
CHANGELOG.md
tickets/rev14-gate-limit-truth-source-ticket.md   (本票本体，登记面，不计施工验收面)
```

`daily_report.py`、`selftest_daily_report.py`、`selftest_monitor.py`、`selftest_watchdog.py`、`bootstrap.py`（无新测试文件，REQUIRED 清单不动）、`monitor.js`/`monitor.html`/`monitor.css`/`monitor-sprite.svg`/`ext.js`、`html_report.py`、`ledger_watchdog.py`、`switch_proxy.py`、`paths.py`、`config.json`、`config-examples/**`、`docs/**`、`data/**`、`legacy/**`、`service-examples/**`：不入闭集零触碰。`config.template.json` **零新键**（`max_inflight`/`gate_follow`/`strata_config` 三键键名不动，只改 comment 口径——加键＝加死面，沿 rev12 A-6 同判）。

#### ②-2 禁动面（零触碰清单）

- `daily_report.py`／`selftest_daily_report.py`：**零触碰**（rev13 领地＋在途施工面）。rev14 完工 commit 不得含这两文件任何 diff（机检③-1）。
- `collector_proxy.py` 内非本票域面零改动：`Recorder`、`Gate` 类全体（红线二 token 闭集）、`do_POST` 闸挂点（710-747 行区）、`key_identity`、日报线程、`_append_line` 本体、main() 挂点注释。
- `requests-*.jsonl` 键面、`gate-events-*.jsonl` 字段面：零改动（红线二）。
- 引擎侧任何文件（`D:\Strata\serve\`、`D:\Strata\strata-unsloth-ud-iq4_xs.json`）、在岗 `D:\Strata-toolkit\`：零触碰。
- 六前置票本体＋勘误件：append-only 不回改。

#### ②-3 collector_proxy.py 逐条施工规格（行号＝ANCHOR 实读锚点；G-1/G-2 代码体写死，逐字转录）

**G-1＋G-2 写死替换体（现体 292-350 行区＝`_strata_parallel_parse` 定义至 `_strata_parallel_limit` 尾 `return v` 全段替换；新体首行 `def _parallel_value(p):` 起、尾行 `    return v` 止）**：

```python
def _parallel_value(p):
    """rev14 A-1: one written parallel value -> gate limit. Validity rule is the
    rev11a one, semantics unchanged: an int (not bool) >= 1 is taken as-is;
    False/None/absent/bool/non-int/<1 = engine single-shot semantics -> 1.
    NO PARALLEL_MAX clamping here (clamping is the engine's business, rev11a A-4;
    basalt's own clamp is 1..8, serve/config.py parallel_count — not ours).
    """
    if isinstance(p, int) and not isinstance(p, bool) and p >= 1:
        return p
    return 1


def _strata_parallel_parse(path):
    """rev14 (INTK-0008): parse one engine startup-config file, BOTH forms.
    Form is discriminated by JSON structure only, NEVER by file name:
    "models" key holding a list -> basalt config v2 reader; else Strata reader.

    Returns (limit, src) or None (file/JSON unreadable = failure state, the
    caller decides per ticket H-1). src read point is a closed set:
    "top" / "entry" / "engine" / "default".

    Two-key files (top-level "parallel" AND a "models" list) are basalt form:
    top-level "parallel" is NOT a legal basalt v2 key (serve/config.py
    read_config rejects unexpected top-level keys) and is NOT read.

    basalt reader: models must be a non-empty list of dicts (else None); each
    entry takes its own "parallel", else the top-level "engine" section's,
    else 1 (both engines' documented default when the key is absent). Gate
    limit = MAX across entries (ticket A-2). Never raises, zero urlreq, zero
    threads.
    """
    try:
        with open(path, encoding="utf-8") as f:
            obj = json.load(f)
    except Exception:
        return None
    if not isinstance(obj, dict):
        return None
    entries = obj.get("models")
    if isinstance(entries, list):
        if not entries or not all(isinstance(e, dict) for e in entries):
            return None
        shared = obj.get("engine")
        shared = shared.get("parallel") if isinstance(shared, dict) else None
        best, src = None, "default"
        for ent in entries:
            if "parallel" in ent:
                v, s = _parallel_value(ent["parallel"]), "entry"
            elif shared is not None:
                v, s = _parallel_value(shared), "engine"
            else:
                v, s = 1, "default"
            if best is None or v > best:
                best, src = v, s
        return best, src
    return _parallel_value(obj.get("parallel")), "top"


_strata_parallel_cache = None   # 模块级：(path:str, guard:(mtime_ns,size), (limit,src)) | None
                                # 无锁纪律：写＝整体重绑元组（GIL 原子）；多请求线程并发
                                # miss 时允许重复解析（幂等读数，last-write-wins，无撕裂
                                # 读、无正确性问题）——引新锁即违红线四。

def _strata_parallel_limit(c):
    global _strata_parallel_cache   # ← 必须（rev11a B-1 修·rev11 D1 同族坑第二次）：
                                    # 函数体内对 _strata_parallel_cache 的任何赋值使 Python
                                    # 把该名全程判为局部——缺这行则读点 cache = ... 先于
                                    # 赋值执行＝UnboundLocalError，且本函数炸点穿
                                    # _gate_params 穿 do_POST（实码 673 行无外层 try）
                                    # ＝跟随态每请求热路径炸。教训就近登记于此，照抄勿删。
    raw = c.get("strata_config")
    if not raw:
        return None                          # 未配路径：不猜，报失败态（调用侧按 H-1 裁定处置）
    path = expand_path(raw, c.get("config_dir"))   # @here/相对口径（paths 已依赖）
    try:
        st = os.stat(path)
    except Exception:
        # 抓 Exception 非 OSError（rev11a B-1 顺带修·QA 探针实证）：os.stat 对含 NUL 的
        # 路径串抛 ValueError（非 OSError 族）——统一报失败态，一切读失败不抛穿热路径。
        _strata_parallel_cache = None        # stat 失败＝缓存作废，本请求入失败态
        return None
    guard = (st.st_mtime_ns, st.st_size)
    cache = _strata_parallel_cache
    if cache is not None and cache[0] == path and cache[1] == guard:
        return cache[2]                      # 命中：零 open 零 parse
    v = _strata_parallel_parse(path)
    if v is not None:
        _strata_parallel_cache = (path, guard, v)
    else:
        _strata_parallel_cache = None        # 解析失败＝不缓存坏值，下请求再试
    return v
```

（返回值改元组 `(limit, src)`＝A-5；`None`＝失败态语义不变。缓存三元组第三元素随形改元组，整体重绑纪律不变。）

**G-3 `_gate_params` 失败态改体（现体 353-395 行函数体内三处）**：

1. 现 355 行 `global _last_limit` → `global _last_limit, _last_limit_src`；现 359 行 except 分支内 `_last_limit = GATE_DEFAULTS[0]` 后插一行 `_last_limit_src = "config_fail"`。
2. 现 380-385 行（`follow = ...` 至 `limit = static_limit`）替换为（**按 H-1 建议态甲写死；H-1 裁乙/丙＝本块走回流件改票后照新写死体转录**）：

```python
    follow = c.get("gate_follow") is True
    if follow:
        v = _strata_parallel_limit(c)
        if v is None:
            # rev14 H-1 甲（真源闭集）：读不到 parallel＝无真源，闸停执法＋显式告警。
            # 禁 max_inflight/任何网关侧数字顶替（人类 10:35 字面已裁兜底之废）。
            limit, src = 0, "follow_fail"
            _announce_follow_failure(c.get("out_dir"))
        else:
            limit, src = v
            global _follow_fail_latched
            _follow_fail_latched = False     # 恢复即解除告警锁存（下轮故障再告）
    else:
        limit, src = static_limit, "static"
    _last_limit, _last_limit_src = limit, src
```

（`global` 行须在函数体首部与 `_last_limit` 声明合并——Python `global` 声明多处合法但风格合一，施工时写为 `global _last_limit, _last_limit_src, _follow_fail_latched` 一行置于 355 行位；上面代码块内 `global _follow_fail_latched` 行仅作位置示意，**终态以函数体首行单条 global 三名为准**——此句属装配说明，不构成第二处声明。）

3. 现 365-379 行注释块内 A-3 段（`max_inflight` 两用途口径）改写：跟随态失败不再退静态（H-1 甲）；`max_inflight` 仅剩非跟随模式一用途（A-6）。注释改动不入红线二 token 面。

**G-4 告警与来源面（模块级新增，落位＝现 279 行 `_last_limit = 0` 之后）**：

```python
_last_limit_src = ""     # rev14: 最近一次 limit 来源（闭集：top/entry/engine/default/static/config_fail/follow_fail）

_follow_fail_latched = False   # 告警去抖锁存（无锁 bool，A-7：良性竞争＝告警行最多多/少写一行，禁引锁违红线四）


def _announce_follow_failure(out_dir):
    """rev14 H-1 甲：跟随真源不可得＝停执法。告警只在状态翻转时写一行（禁每请求刷屏），
    落 ledger-service.log（与 main() 启动行同文件同族）。"""
    global _follow_fail_latched
    if _follow_fail_latched or not out_dir:
        return
    _follow_fail_latched = True
    _append_line(os.path.join(out_dir, "ledger-service.log"),
                 f"[{datetime.now():%Y-%m-%d %H:%M:%S}] GATE FOLLOW FAILURE: "
                 "startup-config parallel unreadable -> gate NOT enforcing (no stand-in number, INTK-0008). "
                 "Check strata_config path/file; gate self-heals when the file is readable again.")
```

（`_append_line`＝现 904 行既有 helper，本体零改。）

**G-5 `_push_gate` 来源上送（现体 282-289 行）**：快照行 `_monitor_ext.push_gate(gate.snapshot(_last_limit))` 替换为：

```python
        snap = gate.snapshot(_last_limit)
        snap["limit_src"] = _last_limit_src
        _monitor_ext.push_gate(snap)
```

（`Gate.snapshot` 本体零改——rev12 冻结面；limit_src 在 push 侧附加。）

**G-6 monitor_ext.py 白名单（现体 563-564 行摘键 tuple）**：`("inflight", "queued", "limit", "waited_total", "beat_total")` → 追加 `"limit_src"`（六键）。除该行外 monitor_ext.py 零触碰。

#### ②-4 selftest_proxy.py 逐条施工规格（既有 45 断言面：21 名零改、跟随组 3 名改判/扩判、新增 3 名；期望 N=48、gate=26）

**改判两名的名与断言效力反转（跟随失败态族——H-1 甲口径）**：

- **K-1 改体留名换**：现 1185-1227 行「gate:follow boot fallback to static max_inflight」→ 更名 `gate:follow truth source failure gates off`。工序骨架复用（pin_slot＋第二请求判别）：follow ON、`strata_config` 指不存在路径、`max_inflight:1`——**新期望反转**：第 2 请求在 0.65s 内**完成**（200，非排队；停执法＝不经闸）；ext.json **无 gate 段**（limit 0＝acquire 不触发＝无 push）；`data/ledger-service.log` 含 `GATE FOLLOW FAILURE` ≥1 行。detail 含状态/日志 grep 读数。
- **A-4ff 改体留名换**：现 1299-1348 行「gate:follow file failure falls back to static」→ 更名 `gate:follow file failure gates off then self-heals`。两失败态（缺文件→坏 JSON）各验「无 gate 段＋第 2 请求快速完成」；**新增收尾步**：`strata_config` 重指回可读文件（`{"parallel":2}`）→第 3 请求组恢复执法（pin 1 个后排队出现、ext gate 段回来、`limit==2`、`limit_src=="top"`）＝自愈行为证。

**扩判据两名（名不变）**：

- A-4「gate:follow limit from strata_config parallel」（现 1229-1297 行）：断言式增 conjunct `g_sc1.get("limit_src") == "top"`（fixture 仍 Strata 顶层形制，工序零改）。
- 24 号「gate:ext.json gate section shape」（现 1134-1140 行）：断言式增 conjunct `g.get("limit_src") == "static"`（该阶段非跟随＝来源 static）。

**新增三名（落位＝跟随组 A-5 断言（现 1350-1360 行）之前；沿用组内 cfg 自恢复纪律）**：

- `gate:follow basalt entry parallel followed`：写 basalt 形制 fixture `{"version":2,"models":[{"model":"m1","parallel":2}]}`，`max_inflight:1`（判别：旧形态读不到顶层→退 1→第 2 请求排队；新形态 limit 2→第 2 请求 0.65s 内完成）；ext `gate.limit == 2` 且 `limit_src == "entry"`。detail 含两读数。
- `gate:follow two-key file reads basalt form only`：fixture 顶层 `"parallel":5` ＋ `models:[{"model":"m1","parallel":1}]`——判别两键并存歧义：limit 必须＝**1**（第 2 请求在 0.65s 仍排队），ext `limit_src == "entry"`；顶层 5 被无视（若读点顺序错＝limit 5→第 2 快速完成→判红）。
- `gate:follow engine section inherit and entry max`：fixture `{"engine":{"parallel":2},"models":[{"model":"m1","parallel":1},{"model":"m2"}]}`——条目 1 ∨ 继承 2＝聚合 max 2（A-2）：第 2 请求 0.65s 内完成，ext `limit == 2`；中段改 fixture 为条目全删 parallel＋engine 段保留→`limit_src == "engine"`。detail 含两态读数。

**fixture 五态覆盖对照（路由件⑥要求）**：Strata 形制＝A-4（既有改扩）；basalt 形制＝新名 1；两键并存＝新名 2；文件缺失＝K-1 改判＋A-4ff 第一步；JSON 坏＝A-4ff 第二步。五态全覆盖、无遗漏态。

**纯解析器单元层（登记不实施，YAGNI）**：解析器真值表已由本票起草实跑 16 fixture 在册（scratch 件），行为面由五态 live 断言承载；独立纯函数套＝另票再议（沿 rev13 A-6「重活不入轻套」反判——此处反过来：轻活不另立套）。

收尾纪律：每断言 cfg 自恢复（rev10a 教训沿例）；不写仓内 `data/`；A-5「follow on still never polls upstream」（现 1350-1360 行）**零改动**——新增三断言均在 follow 组内，hits 零判据自动纳入它们（新形态零上游 GET 行为证顺带扩面）。

#### ②-5 登记面

- **登-1 README.md**：第八节「闸卡启动配置上限（rev11a 改形）」段改写＝两类形制口径（Strata 顶层／basalt v2 条目＋engine 继承＋缺省 1）＋「读不到＝停执法＋告警＋自愈」（H-1 甲随放行；裁乙/丙则登记面随改）＋`limit_src` 可观测口径；第九节第 13 条「读数不可得时的回退次序」改写＝回退链 max_inflight 档作废（沿 rev11a 两级收缩再收一级）。含字面 `basalt` ≥1、`真源` ≥1。
- **登-2 MANIFEST.md**：新增 rev14 节（倒序）＝G-1~G-6 逐面摘要＋GEV_FIELDS 零改登记＋`max_inflight` 语义重登记（A-6）；文件数不变（无新增/删除文件）。
- **登-3 CHANGELOG.md**：新增 rev14 节（倒序置顶），含人类 10:35 需求字面引用＋「兜底废除」前后行为对照＋失败态三选项与 H-1 处置登记。
- **登-4 config.template.json comment**：跟随段改写——「`strata_config` 读不到…退回 max_inflight 兜底（建议与人类已裁并发数同值）」句**删除**，改为「读不到＝闸停执法＋ledger-service.log 告警＋文件恢复自愈（INTK-0008 真源闭集）；两类启动配置形制自动判别」；`max_inflight` 说明补「仅非跟随模式生效」。JSON 键面零增删。

### ③ 验收标准（全机械可判：命令＋期望读数）

> 母本仓根跑，基线＝`2f50a64`；回执逐条附命令原文与读数。基线对照（架构席当轮实跑在册）：proxy 45/45（gate 23）、monitor 54/54、watchdog 16/0。

1. **闭集核验**：`git diff --name-only 2f50a64 | grep -vE '^(collector_proxy\.py|selftest_proxy\.py|monitor_ext\.py|config\.template\.json|README\.md|MANIFEST\.md|CHANGELOG\.md|tickets/rev14-gate-limit-truth-source-ticket\.md)$' | wc -l` ＝ **0**。
   - **补盲读数**：回执另附 `git status --short` 原文——除已登记面外须空面：允许项仅本票本体与临时工作物 `?? .scratch/2026-11-19-ledger-gate-limit-truth-source/`（完工 commit 前清零残留）；出现 `daily_report.py`/`selftest_daily_report.py`/`bootstrap.py` 任何 `M`/`??` 行＝侵 rev13 领地，判红。
2. **三套回归逐套报数（红线三）**：`python selftest_proxy.py` 退出码 0 且 **48/48**、`grep -c '^PASS  gate:'` ＝ **26**；`selftest_monitor.py` **54/54**；`selftest_watchdog.py` **16 passed 0 failed**；`git diff --name-only 2f50a64 | grep -cE 'selftest_(monitor|watchdog)\.py'` ＝ **0**。
3. **兜底废除（红线一·结构面）**：`git diff 2f50a64 -- collector_proxy.py | grep -c '^-.*else static_limit'` ≥ **1**（旧兜底行被删）；`git diff 2f50a64 -- collector_proxy.py | grep -cE '^\+.*(else static_limit|\? static)'` ＝ **0**（新增面零静态顶替）；`grep -c 'follow_fail' collector_proxy.py` ≥ **3**。
4. **rev12 冻结面（红线二）**：`git diff -w 2f50a64 -- collector_proxy.py | grep -cE '^[-+].*(self\.inflight <|self\.inflight \+=|self\.inflight -=|self\._waiters\.append|self\._waiters\.popleft|self\._waiters\.remove|self\._seq \+=|self\.queued \+=|self\.waited_total|self\.beat_total \+=|self\._cond\.wait|self\._cond\.notify)'` ＝ **0**；`git diff 2f50a64 -- selftest_proxy.py | grep -cE '^[-+].*GEV_(FIELDS|SEP_KEYS) ='` ＝ **0**（两闭集常量定义行零改）；`git diff 2f50a64 -- collector_proxy.py | grep -cE '^[-+].*queue_wait_ms'` ＝ **0**。
5. **写死代码体逐字对拍（G-1/G-2 转录探针·常规工序升格）**：母本仓根跑

   ```bash
   python - <<'EOF'
   import ast, hashlib, sys
   src = open("collector_proxy.py", "rb").read().replace(b"\r\n", b"\n")
   tree = ast.parse(src)
   want = {"_parallel_value", "_strata_parallel_parse", "_strata_parallel_limit"}
   parts = []
   for node in tree.body:
       name = getattr(node, "name", None)
       seg = None
       if isinstance(node, ast.FunctionDef) and name in want:
           seg = ast.get_source_segment(src.decode("utf-8"), node)
       elif isinstance(node, ast.Assign):
           t = node.targets[0]
           if isinstance(t, ast.Name) and t.id == "_strata_parallel_cache":
               seg = ast.get_source_segment(src.decode("utf-8"), node)
       if seg:
           parts.append(seg)
   body = "\n\n".join(parts)
   while body.endswith("\n"):
       body = body[:-1]
   b = (body + "\n").encode("utf-8")
   print("bytes", len(b), "sha8", hashlib.sha256(b).hexdigest()[:8])
   sys.exit(0 if hashlib.sha256(b).hexdigest().startswith("1166d156") else 1)
   EOF
   ```

   退出码 **0**、sha 前 8 ＝ **`1166d156`**（架构席起草实跑值，scratch 件 `D:\Projects\strata-ledger-proxy\.scratch\rev14-gate-limit-truth-source\region.py` 在册可对拍）。注：探针取「三函数＋缓存声明」四段按 AST 源序重拼，与 region.py（同四段同序，不含其后 `_gate_params`）逐字节对拍；施工席若拆序写码＝探针判红，照抄勿拆。**global 声明坑自查项（同族两犯史）**：`grep -c 'global _strata_parallel_cache' collector_proxy.py` ＝ **1**（写死体在场）＋`grep -c 'global _last_limit, _last_limit_src, _follow_fail_latched' collector_proxy.py` ＝ **1**（G-3 合并声明行）。
6. **热路径结构计数不变（红线四）**：`grep -c 'urlopen' collector_proxy.py` ＝ **3**；`grep -c 'threading.Thread'` ＝ **1**；`grep -cE 'threading\.(Lock|RLock|Semaphore)\('` ＝ **1**；`grep -c 'threading.Condition()'` ＝ **1**；`grep -c 'os\.stat(' collector_proxy.py` ＝ **1**（禁每请求重读之外的新 stat 点）；行为证＝A-5 断言 hits=0 零改动 PASS。
7. **失败态可观测（H-1 甲行为面）**：回执贴 K-1 改判断言 detail 原文（含 `GATE FOLLOW FAILURE` 日志 grep ≥1、ext 无 gate 段读数）＋A-4ff 自愈步 ext `limit==2`/`limit_src=="top"` 读数＋新名 1 `limit_src=="entry"` 读数＋新名 2「顶层 5 被无视」读数（limit==1）。新名逐名 PASS（②-4 三名＋改判两名＋扩判两名，八名 detail 全贴）。
8. **告警去抖（禁刷屏）**：K-1 工序（失败态期间 ≥3 个对话请求）后 `grep -c 'GATE FOLLOW FAILURE' <测试 data>/ledger-service.log` ＝ **1**（翻转写一行）。
9. **登记面**：`grep -c 'basalt' README.md` ≥1；`grep -c '真源' README.md` ≥1；CHANGELOG rev14 节含 `10:35` 字面 ≥1＋`兜底` ≥1；`git diff 2f50a64 -- config.template.json | grep -cE '^\+  "'` ＝ **0**（模板零新键）；`git diff 2f50a64 -- config.template.json | grep -c '"max_inflight"'` ＝ **0**（键行本体零改）。
10. **fail-closed 反例守卫（红线一行为面）**：`grep -cE '429|409' collector_proxy.py` ＝ **0**（H-1 甲下仍无拒绝态；若 H-1 裁乙＝此判据随回流件改票重定）。

### ④ 边界约束

- **票间关系（互不侵犯·红线五）**：rev13（日报闸统计）与本票**文件交集＝零**——rev13 主战场 `daily_report.py`/`selftest_daily_report.py`/`bootstrap.py`，本票主战场 `collector_proxy.py`/`selftest_proxy.py`/`monitor_ext.py`；两票共享登记面（README/MANIFEST/CHANGELOG）＝**不同节区**（rev13 日报节区／rev14 闸节区），merge 无冲突面。**跨票语义依赖（诚实登记）**：rev13 日报 C1 态判别读 `max_inflight`/`gate_follow` 两键在场性——rev14 后两键仍在、语义不变（`max_inflight` 仅非跟随模式生效不影响 C1「静态关闸」判别：C1 条件＝`max_inflight<=0 且 gate_follow is not True`，跟随开闸走 C2 分支）＝rev13 判据零波及，无需 rev13 改票。rev14 完工 commit 若含 rev13 在途面＝③-1 判红。
- **上线/生效两态（换脑依赖声明）**：完工＝合母本仓即「上线」（不依赖换脑）；在岗生效＝随下次换脑部署（现岗 rev11a 脑；rev12 换脑排 03:00 静默窗；rev14 换脑由主理人另排窗，票外观察面不入验收）。**在岗 config 无需改键即安全**：在岗 `gate_follow:true`＋`max_inflight:2`＋Strata 顶层 parallel 实存＝新代码在岗首请求走「top 读数 2」路径，行为与现岗一致；仅当启动配置不可读时才进入新失败态（甲＝停执法＋告警）——换脑窗内若引擎配置恰好不可读，闸临时停执法不炸服务（limit 0＝闸关语义既有），告警行可查。
- **同源与引用纪律**：口径真源＝10:35 逐字件；「真源闭集」定义不得走样（三读点全在人类手写的启动配置文件内；网关 config.json 的 `max_inflight` **不是**真源，只在非跟随模式作静态上限）。工程师席不得据票外记忆补设计，疑义走回流件。basalt 版本漂移风险登记：本票形制判别对 basalt v0.4.0 config v2 实测；若 basalt 改形制（v3/新读点）＝另票跟随，本票不预答。
- **施工面纪律**：母本仓开分支/工作树，基线＝`2f50a64`；**rev13 在途面共存纪律**：工作区现有 ` M daily_report.py` 等未提交面＝rev13 施工席在途工作，本票施工席**禁 stash／禁 checkout 清理／禁提交**这些面；commit 用 pathspec 限定闭集八文件（`git add collector_proxy.py selftest_proxy.py monitor_ext.py config.template.json README.md MANIFEST.md CHANGELOG.md tickets/rev14-*.md`），禁 `git add -A`；临时工作物只落仓根 `.scratch/2026-11-19-ledger-gate-limit-truth-source/`，完工 commit 前自查零残留；禁磁盘根裸路径/宿主 Temp/仓外自建目录。
- **交付与 commit 纪律**：单一工程师席新鲜实例、票间串行、同席禁多实例；完工 commit 前回执先行，落 `D:\Strata\.workbuddy\collab\receipts\2026-11-19-ledger-gate-limit-truth-source-receipt.md`：开端 HEAD＋写入清单＋③逐条读数（含③-5 探针原始输出＋②-4 八名断言 detail 全文＋③-7 日志样张）＋`.scratch/` 自查。
- **票放行**＝主理人程序确认；**H-1 不随放行默认生效**——放行前决策者必须对 H-1 三选项表态（甲随票面写死体默认装配，乙/丙走回流件改票后再施工）。票面 ②-3 G-3 写死体＝甲态体；H-1 未表态前本票可施工性判定＝**受限可施工**（甲态面可先施工，失败态消费面待裁；见可施工性判定节）。

## 租约段（票内·经架构签注由 B2 lease-issuer 实例化）

- path_globs：`collector_proxy.py`、`selftest_proxy.py`、`monitor_ext.py`、`config.template.json`、`README.md`、`MANIFEST.md`、`CHANGELOG.md`、`tickets/rev14-gate-limit-truth-source-ticket.md`
- deny_globs：`daily_report.py`、`selftest_daily_report.py`、`selftest_monitor.py`、`selftest_watchdog.py`、`bootstrap.py`、`monitor.js`、`monitor.html`、`monitor.css`、`monitor-sprite.svg`、`ext.js`、`html_report.py`、`ledger_watchdog.py`、`switch_proxy.py`、`paths.py`、`config.json`、`config-examples/**`、`docs/**`、`data/**`、`legacy/**`、`service-examples/**`、`.scratch/**`、`D:\Strata-toolkit\**`、`D:\Strata\**`
- 灰度判据（票内声明字段·decision-pack 读取）：三套回归退出码全 0＋proxy **48/48（gate 26）**＋③-3 兜底废除两读数（≥1／＝0）＋③-5 探针 sha8＝`1166d156`＋③-7 八名断言逐名 PASS——测试环境判据，不依赖在岗换脑。
- 席位 ID／票 ID／哈希：由状态机签发，非人工填写

## 票裁已决（A-1～A-8·起草席决；推翻走回流件）

- **A-1｜形制判别＝纯结构判别写死**：JSON 顶层 dict 且 `models` 键持 list→basalt 读路径；否则 Strata 读路径（顶层 `parallel`）。路由件①「禁止按文件名猜」落点。结构判据取 basalt 自身强制面（`read_config` 151-164 行顶层闭集键＋意外键拒）＝判别力有源可引。非 dict 顶层（list/标量）→失败态 None（不是「读不到键退 1」——文件形制根本不对＝真源不可得，入 H-1 失败态处理）。
- **A-2｜basalt 多条目聚合＝MAX across entries**。理由：多 model 配置下引擎可能以不同 parallel 各起进程（config.py 226-249 行 `model_settings` 逐条目装配），闸 limit 卡「引擎任一进程能同时接的上限」＝取 max 才不误杀（取 min＝对高并发条目误杀，违背「防误杀」验收重心族既有口径；取首条目＝对「首条目恰未写 parallel」的配置误杀）。max 读点＝人类写进该文件的诸 parallel 中最大者，仍在真源闭集内，非网关自创。歧义登记：多条目不同值时 ext `limit_src` 只出胜者源名不出逐条目表——逐条目对账属排障增强，YAGNI。
- **A-3｜engine 段继承读点＋缺省 1**：basalt 语义＝条目缺 `parallel` 时继承顶层 `engine` 段（config.py 89-90/196-203 行实证），两处皆缺＝引擎缺省 1（`--parallel` help「default 1」）。缺省 1 与 Strata 顶层无键→卡 1 同判（rev11a 既有语义「字段缺席＝引擎单发语义，闸卡 1」平移）。**注意与失败态的边界**：文件可读且形制对但无键＝缺省语义卡 1（人类可写可不写，引擎本身也按 1 跑，卡 1≠顶替）；文件不可读/形制不对＝真源不可得＝入 H-1 失败态。两者禁混。
- **A-4｜两键并存读点顺序裁定＝basalt 形制下顶层 `parallel` 不读**。路由件警示的歧义面（Strata 顶层键＋basalt 条目键并存）：A-1 判别后天然互斥——有 `models` list 即 basalt 文件，其顶层 `parallel` 是 basalt 侧非法键（read_config 拒意外顶层键＝basalt 自己会拒绝启动这种文件），网关读它＝跟随一个引擎根本不消费的数字＝违真源闭集。测试名 2 钉死（顶层 5 被无视）。不做「顶层优先」：那等于给非法键发执法权。
- **A-5｜解析器返回值升格 `(limit, src)` 元组**。src 闭集四值 `top/entry/engine/default`＋调用侧补 `static/config_fail/follow_fail` 六值全链（`_last_limit_src`→`_push_gate`→monitor_ext 白名单→ext.json）。理由：路由件⑤「limit 来源须可查证」；gate-events 三行闭集**不加字段**（改闭集＝rev12 冻结面破口，事件行已有 `limit` 快照够对账，来源由 ext 段＋告警行承载＝改面最小）；ext 段既有断言用 `>=` 子集判定零炸；monitor.js 零消费零波及。缓存第三元素随升格＝整体重绑纪律不变。
- **A-6｜`max_inflight` 键去留＝保留＋语义收窄为「非跟随模式静态上限」**。理由：①非跟随模式（`gate_follow:false`，缺省）的静态闸仍有合法用户（无引擎配置可读的裸部署），删键＝断该模式＋违缺省零回归；②rev13 日报 C1/C2 态判别消费此键在场性（④跨票语义登记），删键波及 rev13；③废除的是**跟随失败态对它的消费**，不是键本身。登记面同步＝登-1/登-4（README/模板 comment 明写「仅非跟随模式生效」＋在岗「建议保留人类已裁值当兜底」句删除）。
- **A-7｜告警去抖用无锁 bool 锁存**。`_follow_fail_latched` 翻转写一行；多线程并发失败态下最多多写/少写一行告警（GIL 原子 bool 赋值，无撕裂）；引锁＝违红线四「零新增锁」。告警落 `ledger-service.log`（既有服务日志，main 启动行同文件同族）＝不建新文件不建键；恢复路径（G-3 else 分支）解锁存。禁 stdout-only 方案：在岗 stdout 被 watchdog 重定向到 watchdog log（实核 ledger_watchdog.py 214 行），排障面应落数据目录服务日志＝与账本同目录一处可查。
- **A-8｜改判两断言＝名随语义改（不沿用旧名）**。K-1/A-4ff 旧名含「fallback to static」字样，H-1 甲下语义反转（失败＝停执法非退静态）——留名会让断言清单说谎（名与效力相反＝读者面污染，沿 rev13 Y-8「效力以断言名为准」纪律反向应用：名必须与效力一致）。gate 计数 23→26＝2 改名＋3 新增，逐名在册可数。

## 候裁单列（H-x·起草席不自行拍）

- **H-1｜失败态新语义三选项**（真源不可得时闸怎么办——人类 10:35 已裁「废除硬编码兜底」，但「废了之后闸怎么办」未裁；路由注记明列「涉安全口径，票面须列候裁呈决策者」＝决策者保留闸，列 H，不随放行默认）。死命令语境诚实解读：`parallel=2` 本身是人类写的，「兜底」之恶在于**那个数字不是当时真源**（在岗两键同值 2 时看不出差别，恰恰证明它平时没用、出错时才暴露它是顶替者），而非「闸无上限」本身。三选项利害：
  - **(甲·票面建议·立场＝采此) 闸停执法（limit 0＝闸关既有语义）＋`ledger-service.log` 显式告警一行＋文件恢复自愈**。利：①「不执法」是网关**自身**既有可回退态（`max_inflight:0` 缺省即此），非新造第三态，语义零发明；②并发实际由引擎槽位承接（超出 parallel 的请求引擎侧排队——网关「卡上限」职权失效但引擎真源仍守门，调研件§一「换 upstream 指过去即可跑」独立成立）；③fail-open 窗口有告警行＋ext 无 gate 段双证据可查，事后对账＝gate-events 缺口本身即证据（闸开有行/停执法无行＋告警行）；④不炸服务：换脑窗/引擎配置临时不可读不导致接入全断。害：失败窗口内第 3 路对话可放行到引擎（风险被引擎自身 parallel 兜住，但网关层防线暂缺——这正是「人类真源缺位时网关无权代行」的字面后果）。
  - **(乙) 拒绝启动/拒绝服务（fail-closed）**：跟随开但真源不可得＝服务不起或对话请求全拒。利：绝无「无网关上限」窗口。害：①与 rev10 起六票「永无拒绝态」红线正面冲突（`grep -cE '(429|409)'`＝0 是全链既有判据，③-10 沿例）——开拒绝态＝改安全口径本体，影响面远超本 rev；②「读不到」的成因里最常見的是**文件被保存中途/路径笔误**这类瞬时事故，代价＝团队接入全断，与「兜底之恶＝数字假」的原始危害不成比例；③看门狗 5s 补岗×起不来的循环。若决策者采乙＝须另立「拒绝态」口径票扩全链红线，非本票写死体可承载。
  - **(丙) 其它候选：失败态沿最后一次读得值（last-good）**——rev11 运行时轮询时代有此档、rev11a 已随读源作废。**起草席明确反对**：last-good＝缓存旧数字顶替当下文件＝与 max_inflight 兜底同族（只是旧得早晚不同），违「真源闭集」字面（当时的真源是文件现值，不是旧值）；列此仅为候裁面完备。
  - **票装配**：②-3 G-3/②-4 改判族/③-7/③-8/③-10 全按甲写死；决策者裁乙/丙＝回流件改票（G-3 块＋失败态断言族＋对应判据重装配），改面集中、不伤解析器兼容面（G-1/G-2 与失败态正交，甲乙丙通用）。
  - 真冲突核：诉求①②本体（兼容 basalt／废兜底）＝10:35 已裁不入 H；形制判别/聚合/继承/可观测/键去留＝装配面 A 裁毕；残余（basalt 未来形制漂移、`/v1/responses` 端点扩面）＝④另票，不上楼。

## 健康账登记（回流素材）

1. **「两键同值」遮蔽失败态语义（供 sops 立账，本票不代立）**：在岗 `max_inflight:2` 与启动配置 `parallel:2` 同值两年，兜底路径在生产从未显形（K-1 类断言只在测试盒里红过）——「安全兜底」若与真源常年同值，其「假」要靠形制漂移（换 basalt）才暴露；同类「兜底与真源同值＝死面假活」需在 SOP 巡检立负样本判据（兜底值改一个数，执法应无变化→有变化即兜底在用）。
2. **「静默失效」的观测补课（素材）**：rev14 前读不到真源退兜底＝ext.json 无任何痕迹（limit 仍是数、gate 段仍出）；本票补 `limit_src` 后「跟随是否真跟随」一查即知。「观测面应随兜底类回退同票出生」入素材，供 object-audit 判据域引用。

## 可施工性判定（架构席自评）

- 全部挂点在 `2f50a64` 实测存在：`collector_proxy.py` 1041 行实读锚点——`_strata_parallel_parse` 292／`_strata_parallel_cache` 318／`_strata_parallel_limit` 323／`_gate_params` 353（383 行兜底行＝废除对象）／`_push_gate` 282／`_append_line` 904；`monitor_ext.py` 白名单 563-564；selftest_proxy 跟随组 1176-1362（K-1 1224／A-4 1290／A-4ff 1342／A-5 1357／24 号 1137）。
- 候选体已实跑：本席 scratch 盒 `region.py`＋`probe.py` 16 断言全过＋sha8 `1166d156` 在册——③-5 探针与票内写死体同源可对拍。基线三套读数在册（45/45·gate 23／54/54／16/0）。
- 判别力自评：③-3 对「兜底暗渡」判红；③-5 哈希对「写死体走样／global 声明丢」判红；新名 2 对「读点顺序错」判红；新名 1 对「basalt 形制不识别」判红（旧形态必红＝真判别非重言）；K-1/A-4ff 改判对「失败态语义回退」判红；③-6 对「热路径加料」判红；③-4 对「rev12 冻结面破口」判红；③-1 补盲读数对「侵 rev13 领地」判红。
- 未实跑面（留施工/QA）：②-3 G-3/G-4/G-5 写死块与②-4 八名断言体的首跑（本票锚点为实码行号＋语义等价推演）；在岗实跑失败态告警实见（④换脑后票外）。判定＝**受限可施工**：解析器兼容面（G-1/G-2＋新名 1/2/3）与 H-1 正交可先装配；失败态消费面（G-3/G-4＋改判族）待 H-1 表态（甲＝现写死体直接装配；乙/丙＝回流件改票后再施工）。

—— 架构席 · rev14 v1 · 开端 HEAD 实测 `2f50a645bbce7e1459046857e645d78e81263fc8`（git -C D:\Projects\strata-ledger-proxy rev-parse HEAD）· 2026-11-19 · 起草实核与候选探针件居仓根 `.scratch/rev14-gate-limit-truth-source/`＋治理族 `D:\Strata\.workbuddy\collab\`（本票文件本体落仓根 `tickets/`，路由件指定）