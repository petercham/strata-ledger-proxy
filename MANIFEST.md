# 清单与来源登记

发行版本：`strata-ledger-proxy` 2026-11-09（本次修订 2026-11-17 · rev8 后补：`config-examples/` 两份脱敏真机样例 + README 第十一节「真机踩坑登记」（症状式 10 条）；git 仓形态，无 ZIP）
用途：给另一台机器（代号 5090）替换旧的「旁路边读引擎日志」账本链的**独立工具包**。
运行要求：本机 Python 3.13 实测通过；3.8 未实测，静态检查未见 3.9+ 专有语法（内置泛型下标 `list[...]`、`X | Y` 联合类型、match 语句等均未使用）。主链仅标准库；`psutil` 与 `nvidia-smi` 为监控增强，缺失时自动降级。目标机若用更旧版本，请先跑 `bootstrap.py --selftest` 验证。

---

## 一、文件清单

本发行版共 **31 个文件**（根目录 23 个 + `service-examples/` 3 个 + `legacy/` 3 个 + `config-examples/` 2 个；下表把服务示例与兼容件各归并成一行通配登记）。逐项来源见下表，仓内条目以当次实际提交为准，不在此写死随版本变化的计数。

| 文件 | 作用 | 来源 |
|---|---|---|
| `config.template.json` | 配置模板，不含任何本机绝对路径或真人姓名 | 本包新写 |
| `bootstrap.py` | 生成配置 / 只读自检 / 跑回归自测 | 本包新写 |
| `paths.py` | 跨平台路径解析（`@here` / `@pkg` / `~` / 相对 / 绝对） | 本包新写 |
| `README.md` | 安装、验收、迁移、回滚、边界 | 本包新写 |
| `SKILL.md` | 宿主 Agent 的部署工序入口（模式判定、自检、拍板项、工序、验收、投递） | 本包新写 |
| `CHANGELOG.md` | 版本改动登记（人读摘要，明细仍以本文件为准） | 本包新写 |
| `MANIFEST.md` | 本文件 | 本包新写 |
| `collector_proxy.py` | 反代 + 按 key 记账 + 日报线程 + 硬件监控合并 | 实例版副本 + 路径补丁 |
| `monitor_ext.py` | 硬件采样（GPU 含 UUID、显存/编解码利用率与每卡 PCIe 链路实测 18 列）、自带 `/monitor` `/monitor.js` `/monitor.css` `/monitor-sprite.svg` `/ext.json` `/health` 路由；**不再向任何页面注入脚本** | 实例版副本 + 2026-11-16 重构（见 2.8 / 2.9 / 2.10 节） |
| `monitor.html` | 自持监控页骨架：官方 Strata 监视页的完整复刻 + 本包硬件卡「融合视图」（状态卡 / 融合卡网格 / Context fill / Recent requests / Conversation cache），页脚自报账本工具自持页面 | 本包新写（2026-11-16，三稿重写为融合视图，见 2.9 节） |
| `monitor.js` | 监控页逻辑：每秒并发 fetch `/ext.json` + `/metrics` 双源独立容错；GPU 卡片与波形历史按 UUID 绑定、槽位号仅展示；引擎 key 读写官方同键 `localStorage["strata.apikey"]` | 本包新写（2026-11-16，三稿重写，见 2.9 节） |
| `monitor.css` | 页面样式：官方 st-* 设计令牌与组件类逐条移植为包内自有文件（深浅色两套），零运行时依赖官方 CSS | 本包新写（2026-11-16 三稿，见 2.9 节） |
| `monitor-sprite.svg` | 页面图标精灵：12 个 symbol 几何逐字拷自官方 sprite 以保视觉一致；由反代在 `/monitor-sprite.svg` 提供，本包从不加载官方 sprite | 本包新写（拷自官方素材，2026-11-16 三稿） |
| `ext.js` | 旧注入式监控脚本，仅为「官方页面尚未恢复原状」的过渡兼容保留；新部署不需要。**注意**：过渡期内它仍按 nvidia-smi 槽位号分桶历史，仍可能串卡——不修复串卡，只兜过渡显示 | 实例版副本 + 2026-11-16 跨源 API 解析（见 2.8 节），退役中 |
| `daily_report.py` | 按天日报 | 母本副本 + 路径补丁 |
| `html_report.py` | 交互式网页报表 | 母本副本 + 路径补丁 |
| `ledger_watchdog.py` | 5 秒巡检、配置热更新、立即补岗、脱离会话拉起服务 | 本机运维脚本副本 + 补丁 |
| `switch_proxy.py` | 唯一切换入口，有会话硬拒绝 | 本机运维脚本副本 + 补丁 |
| `selftest_proxy.py` | 回归自测（假上游 + 临时端口），用例数见 2.4 节 | 本机自测副本 + 补丁 |
| `selftest_watchdog.py` | 临时端口回归用例，用例数按当次实际输出报出 | 本机自测副本，未改 |
| `selftest_monitor.py` | 监控页回归用例（18 列解析 / UUID 身份 / PCIe 链路与零告警纪律 / lead 单线 PCIe 卡 / disks-net innerHTML / mx-sw 10×3 / disk rev6 与 net rev6b 卡形态 / CPU 图例与配色 / 小字基线骨架 / node 冒烟 / 路由与融合页静态资产断言），用例数按当次实际输出报出 | 本包新写（2026-11-16，三稿扩充 + 四稿扩充 + 五稿对齐 + 六稿卡重构/图例/骨架对齐，见 2.9 / 2.10 / 2.11 节） |
| `start.bat` | Windows 启动（GBK + CRLF） | 本包新写 |
| `start.sh` | Linux / macOS 启动（LF） | 本包新写 |
| `service-examples/*` | 登录自启 / systemd / launchd 示例 | 本包新写 |
| `config-examples/windows-5090-single-gpu.json` | Windows 单卡终端在岗配置样例（IPv6 双栈门面 + 引擎退环回 + lock 避让改值示范） | 000 在岗实机抄录，去 `key_labels`，2026-11-17 |
| `config-examples/ubuntu-pro5000-4090-dual-gpu.json` | Linux 双卡工作站装配参考样例（双卡零配置示范，comment 内嵌降级与 systemd 口径） | 按模板缺省口径组装（非实机抄录），2026-11-17 |
| `legacy/collector_log.py` | 旧读日志采集器（可选兼容件） | 母本副本，未改 |
| `legacy/scheduler.py` | 旧定时排程（可选兼容件） | 母本副本，未改 |
| `legacy/README.md` | 兼容件说明 | 本包新写 |

---

## 二、改动登记

下表按「相对源文件做了什么」逐项列出，不设总数（每次交付以本表实际行数为准）。所有改动均限定在路径/端口解析、可选功能降级、断连保护、归因修正与文档同步，**流式逐块转发、响应头透传、按 key 记账、`ts` 取请求开始时刻、32 MiB 记账副本上限、排队数 128、看门狗「只在端口关闭时拉起自己的子进程」、切换时「有会话硬拒绝且 `--force` 不覆盖」这些契约一律未改**。

### 2.1 移植补丁（首版相对源文件）

| 文件 | 改动 | 为什么 |
|---|---|---|
| `collector_proxy.py` | `load_config()` 改走 `paths.load_config()` | `out_dir` / `web_root` 支持相对路径与占位符，配置不再写死盘符 |
| `daily_report.py` | 同上 | 单独命令行跑日报时也能解析相对路径 |
| `html_report.py` | `--config` 分支改走 `paths.load_config()`；`config.json` 位置改用配置里的真实路径 | 配置不在 `out_dir` 时也能读到人名映射 |
| `monitor_ext.py` | 去掉原文件里写死的 Windows 部署根默认值；`web_root` 为空或目录不存在时跳过页面注入，采样器照常工作 | 目标机没有该目录，页面注入必须可跳过 |
| `ledger_watchdog.py` | 默认服务脚本从「用户主目录下 WorkBuddy 技能目录」改成**本包同目录**；环境变量/配置覆盖改用 `paths.expand_path` | 目标机可能没装 WorkBuddy，包必须自包含 |
| `switch_proxy.py` | 判忙时按配置的 `out_dir` 找账本文件，不再固定在脚本旁边 | 数据目录搬走后会话检查不能失效 |
| `selftest_proxy.py` | `PROXY_SCRIPT` 从写死的绝对路径改成 `__file__` 同目录 | 自测在任何机器上都能跑 |
| `selftest_watchdog.py` | 无需改动，已是按 `__file__` 推导 | — |

### 2.2 模块动态加载兜底（首版后补）

`selftest_watchdog.py` 等用 `importlib` 从文件路径加载模块时，包目录不一定在 `sys.path`，直接 `from paths import ...` 会抛 `ModuleNotFoundError: paths`。以下模块在导入 `paths` 前各加一行 `sys.path.insert(0, HERE)`：

| 文件 | 行 | 说明 |
|---|---|---|
| `daily_report.py` | 19 | 供反代进程内日报线程以 import 方式加载 |
| `html_report.py` | 25 | 同上 |
| `ledger_watchdog.py` | 67 | 供自测以 `importlib` 加载 |
| `switch_proxy.py` | 45 | 同上 |
| `bootstrap.py` | 26（本轮补，见 2.6 节） | 清掉 P3-2：宿主用 `importlib` 从文件路径加载本文件时也能找到 `paths` |

注：`collector_proxy.py:66`、`legacy/scheduler.py:52` 也有 `sys.path.insert`，但那是**源文件自带的**、用于导入同目录监控/日报模块，**非本包新增**，不在本表登记范围内。

### 2.3 交付前修复（2026-11-09 轮）

| 文件 | 改动 | 对应项 |
|---|---|---|
| `paths.py` | `expand_path()` 收尾处：非绝对路径且无盘符时先 `os.path.join(base, s)`，纯相对路径改为相对**配置文件所在目录**解析，不再随 cwd 漂移 | 必修 1 |
| `paths.py` | 新增 `ports_from_config()`：从 config 读 `listen`（`rpartition(":")`，兼容 `[::]:端口`）与 `watchdog_lock_port`，坏配置安全回退 | 必修 2 |
| `ledger_watchdog.py` | `--port` / `--lock-port` 默认改 `None`；`main()` 在日志与 `port_is_up()` 之前用 `ports_from_config()` 补齐，显式 CLI 值优先（自测传参不受影响） | 必修 2 |
| `switch_proxy.py` | `main()` 用 `global` 从 config 重绑 `PROXY_PORT` / `WATCHDOG_LOCK_PORT`；`port_up()` 默认值改为**调用时**解析，避免函数定义时固化 8080 | 必修 2 |
| `config.template.json` | 新增 `watchdog_lock_port`；`comment` 说明端口自动跟随、两锁端口须不同、相对路径语义 | 必修 2 |
| `README.md` | 第三步表格补 `watchdog_lock_port` 与「只改 listen 一处」说明；第 11 行改为不依赖外部升级说明文档的自包含说明；补物理硬盘清单的平台差异 | 必修 2 / 3 |
| `MANIFEST.md` | 本节重写、运行要求改为如实口径 | 必修 3 |
| `monitor_ext.py` | `_smi_exe()` 去掉最后一个盘符字面量：`SystemRoot` 为空直接返回 `nvidia-smi`，行为不变 | 必修 4 |
| `collector_proxy.py` | 单实例锁默认值改为 `43177`，与模板一致（原默认值与模板不符） | 必修 4 |
| `collector_proxy.py` | `do_GET` 上游异常分支加 `responded` 保护：已发出响应头时只 `close_connection`，不再追加第二个 502 | 可选（低风险） |
| `README.md` | `key_labels` 示例换成虚构指纹 `01234567` / `abcdef01`，注明须用 `--fp` 实算；全包 4 个真实指纹与 4 个真人姓名 0 命中 | 必修 A |
| `README.md` | 第四节标题与条目如实化：网页报表标注「需手动生成/刷新」，验收清单第 6 条拆成日报 / 网页报表两条独立命令，§八表格增一行网页报表命令 | 必修 B |
| `html_report.py` | 页脚「每天 0 点日报链自动刷新」改为「由 html_report.py 生成 · 手动重跑可刷新」 | 必修 B |
| `README.md` | 启动表「长期运行建议」改为「**生产必须**装 service-examples 自启件」，`start.sh` / `start.bat` 标注仅交互式试跑；第九节新增第 7 条会话消失边界；第五节新增第 8 条关终端后自检 | 必修 C |
| `start.sh` | 顶部注释与 echo 提示加醒目告示：前台 `exec`，关终端 / SSH 断开服务即消失，生产必须装自启件 | 必修 C |
| `ledger_watchdog.py` | `launch_ledger()` 的 `subprocess.Popen`：POSIX 分支加 `start_new_session=True` 让子进程脱离终端会话、不受 SIGHUP 连带；Windows 仍只传 creationflags | 必修 C |
| `switch_proxy.py` | `report()` / `do_switch()` / argparse 里的端口提示由写死 `8080` 改为按 `PROXY_PORT` 动态显示 | 交付前一致性（额外） |
| `MANIFEST.md` | 第三节去掉「8 处」写死计数；第五节扫描断言改为「所有 .py 代码零硬编码；文档以占位方式描述来源」 | 必修 D |

### 2.4 按 key 归因修复（2026-11-11 轮）

| 文件 | 改动 | 对应项 |
|---|---|---|
| `collector_proxy.py` | 新增 `key_identity(headers, cfg)` 返回 `(tag, fp)`：先 `raw.strip()`，再用 `raw[:7].lower() == "bearer "` 剥前缀，使 `Bearer` / `bearer` / `BEARER` 按 RFC 7235 大小写不敏感地归一；`key_tag()` 保留为向后兼容 wrapper | A（真 bug） |
| `collector_proxy.py` | 账本 `rec` 构造改为一次 `tag, fp = key_identity(...)`，不重复算 hash；新增 `fp` 字段（8 位小写 hex 或 `none`），原始指纹永久留存，便于事后拆分 / 追查撞码 | A |
| `selftest_proxy.py` | 新增归因用例：`Bearer` / `bearer` 同 `key`+`fp`、混合大小写 `BEARER` 同 `key`+`fp`、`x-api-key` 的 chat 请求记录合法 `fp`、全量账本行 `fp` 格式校验（含无 key 的 `none` 行）；用例数按当次实际输出报出，不写死 | B |
| `bootstrap.py` | 新增 `import re`；`do_check()` 在 `web_root` 之后新增**纯读取**的 `key_labels` 校验：键须 8 位小写 hex（大写判不合格并提示改小写）、值须非空字符串、两指纹映射同一姓名仅 warn、缺失/空 `{}` warn | C |
| `bootstrap.py` | 清掉审计残留 R-3：`lock_port` 与 `watchdog_lock_port` 相同 → `fails.append` | C |
| `README.md` | 第三节补三个坑（`--fp` 算裸 key 别带 `Bearer `、空 `key_labels` 显示 8 位码看似撞车、同姓名合并不可从历史拆开）；第四节字段清单加入 `fp` 并说明不影响出报表；第五节第 3 条验收补 `fp`；第九节新增第 8 条「32 位空间可能撞码、保留 `fp` 便于发现、不做自动碰撞检测」 | D |
| `daily_report.py` / `html_report.py` | **已核查、未改**：两者均按 `r.get("key")` 分组，代码里没有对账本字段做白名单或严格集合断言（`CANON_INT` 只是 `rec.setdefault` 的整型字段），新增 `fp` 不影响出日报 / 网页报表 | A（核查） |
| `MANIFEST.md` | 本文件新增 2.4 节；第一节 `selftest_proxy.py` 用例数不再写死；第五节补「按实际用例数报出」口径 | E |

**回归自测用例数口径**：两套均以 `RESULTS` / `PASS`/`FAIL` 实际计数输出，文档**不写死具体用例数**；每轮增减用例以当次输出为准。交付包内 `selftest_watchdog.py` 与生产 `usage/selftest_watchdog.py` 各按自身当次输出分别报出（生产版另含端口解析与 `--lock-wait` 接管用例，两者数量可以不同）。

### 2.5 文档层重构（docs-r2，2026-11-12）

| 文件 | 改动 | 说明 |
|---|---|---|
| `SKILL.md` | 新增：宿主 Agent 部署工序入口（frontmatter `name: strata-ledger-deploy`；含触发条件、模式判定表、三条前置自检、必问人类拍板项、编号工序、验收判据、运维与故障、边界与债、每日投递工序） | 内容全部取自本包既有事实（README / MANIFEST / legacy README），未发明新能力 |
| `CHANGELOG.md` | 新增：倒序登记 v1（2026-11-09）、rev（2026-11-11）、docs-r2（2026-11-12）三轮 | 人读摘要，逐项明细仍以本文件第二节为准 |
| `README.md` | 仅在顶部引言后插入「Agent 部署入口」短小节（3 行），其余内容一字未动 | 指引宿主 Agent 直接按 `SKILL.md` 执行 |
| `MANIFEST.md` | 第一节登记两个新文件；本小节；「发行版本」行修订日期更新为 2026-11-12 | — |

**本次为纯文档层改动，未改任何 `.py` / `.bat` / `.sh` / 配置模板**：所有运行件（`collector_proxy.py`、`daily_report.py`、`ledger_watchdog.py`、`switch_proxy.py`、`bootstrap.py`、`paths.py`、`monitor_ext.py`、`ext.js`、`html_report.py`、`selftest_*.py`、`legacy/*`、`service-examples/*`、`config.template.json`、`start.bat`、`start.sh`）本轮零改动，上文登记的契约不变量（流式逐块转发、响应头透传、按 key 记账、`ts` 取请求开始时刻、32 MiB 记账副本上限、排队数 128、看门狗「只在端口关闭时拉起自己的子进程」、切换「有会话硬拒绝且 `--force` 不覆盖」）全部未动。

**生产母本同步（只改文件，绝不重启）**：用户主目录下 WorkBuddy 技能目录里的 `collector_proxy.py` 已按 A 的两处改动同步；生产数据目录里的 `selftest_proxy.py` 与本包版同构（唯一差异是 `PROXY_SCRIPT` 写死为生产脚本绝对路径），已同步加等价用例并在临时端口跑通。11-11 轮当时 **磁盘代码已更新 ≠ 进程已生效**，已注明 8080 常驻进程仍加载修改前的模块、需等无会话窗口按纪律走 `switch_proxy.py`。此后主理人已于 **2026-11-12 20:19** 完成切换，**11-11 归因修复版在生产 8080 上实证生效**；本轮（见 2.6 节）又把看门狗磁盘代码两边对齐，但**看门狗进程仍待主理人在无会话窗口自行交接**。本轮全程未启动、未停止、未重启、未连接、未占用任何生产服务端口。

### 2.6 看门狗对齐 / 自启接管 / 重打包（2026-11-12 轮）

本轮把「交付包 / 生产看门狗 / 开机自启」三条线一次对齐并重新打包。生产改动**只改磁盘文件，未重启任何进程**。

| 文件 | 改动 | 对应项 |
|---|---|---|
| 生产 `usage/ledger_watchdog.py` | 新增**自包含** `ports_from_config(path, default_port=8080, default_lock_port=43176)`，语义与包内 `paths.py` 的 `ports_from_config()` 一致，但**不 `import paths`**（`usage/` 目录没有该文件，须保持单文件自包含） | A |
| 生产 `usage/ledger_watchdog.py` | `parse_args()` 的 `--port` / `--lock-port` 默认改 `None`，help 写明默认跟随 `config.json`；`main()` 在 `args.config` 规范化之后、任何日志与 `port_is_up()` 之前用 `ports_from_config()` 补齐，显式 CLI 参数始终优先 | A |
| 生产 `usage/ledger_watchdog.py` | `launch_ledger()` 的 `subprocess.Popen` 改 `popen_kwargs` 字典：Windows 分支保留 `creationflags`，POSIX 分支加 `start_new_session=True` | A |
| 生产 `usage/ledger_watchdog.py` | **未改**：`resolve_collector()` 默认路径仍落到用户主目录下 WorkBuddy 技能目录；`--lock-wait` 候补接管锁循环一字未动 | A（保持） |
| 生产 `usage/selftest_watchdog.py` | 新增端口解析与接管用例：`ports_from_config()` 六种配置形状（正常 / `[::]:端口` / 坏 JSON / 端口非数字 / 缺 `watchdog_lock_port` / 非 dict）与进程级「config `listen` 跟随」「显式 `--port`/`--lock-port` 优先」「`--lock-wait` 候补接管」；原有回归用例逐字保留，用例数按当次实际输出报出 | B |
| 启动夹 `Strata ledger watchdog.vbs` | `sh.Run` 命令行末尾给 `ledger_watchdog.py` 追加 `--lock-wait 86400`，登录副本改为热备候补、旧看门狗退出后零缝隙接管；英文注释写清原因，纯 ASCII + CRLF；`python.exe` 与脚本路径未改 | C |
| `service-examples/Strata ledger watchdog.vbs` | 同步 `--lock-wait 86400` 写法与英文注释；清掉 P3-5：中文注释改纯 ASCII、UTF-8/LF 改 ASCII/CRLF（GBK 友好），可执行语句全 ASCII | C |
| `bootstrap.py` | 顶部 `HERE` 定义后加 `sys.path.insert(0, HERE)` 兜底，清掉 P3-2（`importlib` 从文件路径加载时 `ModuleNotFoundError: paths`） | D |
| `README.md` | 第三节补第 4 个坑（畸形 `Authorization: Bearer ` 记成陌生 8 位指纹而非 `none`，有意为之，便于发现配错客户端）；第九节第 3 条同步边界；第二节补 VBS `--lock-wait` 候补接管说明 | D |
| `MANIFEST.md` | 本文件：第一节文件总数口径改 24 且不写死、清掉写死用例数（P3-4）、2.2 节补登记 `bootstrap.py`、修正 2.5 节「生产 8080 仍跑旧代码」过时断言、新增本小节 | D |
| `CHANGELOG.md` | 新增 2026-11-12 记录，写明本轮改动与生产进程状态 | D |
| `strata-ledger-proxy-2026-11-12.zip` | 重打包为 **24 文件**版，保留 11-09 / 11-11 两个旧 ZIP | D |

**生产进程状态（如实）**：生产 `8080` 已于 2026-11-12 20:19 切换到 11-11 归因修复版并实证生效（由主理人完成，本席未参与）；本轮**看门狗磁盘代码已对齐但进程未重启、未交接**，待主理人在无会话窗口自行完成。本轮全程未启动 / 停止 / 重启 / 连接 / 占用 `8080` / `8787` / `20003`。

**P3-6 处理**：`selftest_watchdog.py` 仍用固定临时端口（`19080` / `43976` 及本轮新增的 `19xxx` / `43xxx` 高位端口），未改成绑定端口 0 取空闲端口。评估：临时端口均取自高位段、且每次运行在全新临时目录，端口冲突概率低，**保留为已知低风险**，本轮不改动，避免牵动原有 16 个已验证用例。

---

### 2.7 终版修正（2026-11-12 晚 · Windows 自启示例静默失败）

| 文件 | 改动 | 为什么 |
|---|---|---|
| `service-examples/Strata ledger watchdog.vbs` | 注释改为「VBS 留在包目录、启动夹只放快捷方式」；可执行语句不再经额外的命令处理器中转，用 `Chr(34)` 拼引号，并支持 `STRATA_PYTHON` 环境变量覆盖解释器（回退 `python`） | 原注释让人把 VBS 复制进启动夹，而脚本按自身目录找 `ledger_watchdog.py`；复制后目录变成启动夹、主程序找不到且静默失败。快捷方式不改变脚本的真实路径 |
| `README.md` | 第二节平台表格、启动逻辑段、第九节第 7 条同步改成「启动夹放快捷方式」，补原因与 `STRATA_PYTHON` 用法 | 文档不能继续把人往坑里带 |
| `SKILL.md` | 第 6 步 Windows 行与紧随的说明同步 | 宿主 Agent 按 SKILL 执行，口径必须一致 |
| `CHANGELOG.md` / 本文件 | 新增本轮人读摘要与本节 | 改动可追溯 |

不变项：包内所有 `.py`、`config.template.json`、`start.bat`、`start.sh` 一字未改；`--lock-wait 86400` 候补接管参数保留；VBS 仍为纯 ASCII + CRLF、引号成对；本轮未启动 / 停止 / 重启 / 连接 / 占用任何生产服务端口。

---

### 2.8 监控页重构：自持独立页，按 UUID 绑卡（2026-11-16 轮）

重构动机（生产实证缺陷）：官方页注入混合体把 Pro5000 的负载波形画到 4090 卡片上。根因在旧 `ext.js`：波形历史按 nvidia-smi 的 `index` 存、卡片标签按卡名重建，而本机槽位序会漂（历史事故：gpu:0 错落 4090 时 decode 210→13.7 tok/s；开机计划任务还会 disable→enable 4090）。本机铁律：判卡一律 UUID/卡名，槽位号不作身份判据。用户已拍板**彻底弃用官方 webui 集成**。

| 文件 | 改动 | 为什么 |
|---|---|---|
| `monitor_ext.py` | `GPU_QUERY` 10 列 → 14 列（新增 `uuid,utilization.memory,utilization.encoder,utilization.decoder`；**11-16 二稿更正**：首稿写的 `encoder.utilization/decoder.utilization` 在 621.24 驱动下让整条 nvidia-smi 查询 rc=2 失败、所有显卡消失，已换成驱动实证可用的名字）；解析改 `parse_gpu_csv()`：csv 模块 + `skipinitialspace`（卡名含逗号不串列）、不足 14 列整行丢弃（旧驱动不得错位填值）、缺 UUID 退卡名身份（绝不退 index）；每行 JSON 新增 `uuid/mem_util/enc_util/dec_util` | 身份必须稳定；旧口径把波形画到别的卡上 |
| `monitor_ext.py` | **删除 `attach()` / `pages()` / `Watcher` / `_write()` / `MARK` / `SCRIPT` / `ELEMENT` / `PAGE_GLOBS` 整套注入机制**；`start()` 不再起 Watcher；`web_root` 配置字段弃用（留着不报错） | 本工具不再写任何它不拥有的页面 |
| `monitor_ext.py` | `answer()` 新增 `/monitor`（回 `monitor.html`）与 `/monitor.js`（回 `monitor.js`）两个自持路由；`/ext.js` 保留为退役过渡 shim；`/ext.json`、`/health`、`/` 不认领等语义不变 | 页面结构与数据接口分离，页面归本包所有 |
| `monitor.html` / `monitor.js` | 新增自包含页面与脚本：卡片排布 Speed→GPU→RAM→Disk→Net 风格（大数字+副行+180 点 1s sparkline），100% 自写、零第三方、内联 CSS、深浅色跟随 `prefers-color-scheme`；GPU 卡片与波形历史一律按 `uuid` 绑定（DOM id 由 uuid 哈希），uuid 消失时卡片与历史一并移除；GPU 主数字=SM util，副行含显存 used/total、显存/编码/解码利用率、温度、功率/限、SM 时钟、驱动模式，标题显示卡名+驱动模式+`#index`（标注仅展示） | 修根因：槽位号不可作身份 |
| `collector_proxy.py` | 仅 docstring 与一行启动提示改口径（监控页在 `/monitor`）；代码接线未动（`_monitor_ext.answer()` / `start()` 签名不变） | 最小改动 |
| `ext.js` | 数据源解析改为按 `document.currentScript` 的 src 推断 origin（跨源加载时也能读到反代的 `/ext.json`，反代对 `/ext.json` 发 `Access-Control-Allow-Origin: *`；同源加载行为不变，仍是 `""`） | 官方控制台页在 :8787、`/ext.json` 在反代端口，过渡期跨源取数必须可用 |
| `selftest_monitor.py` | 新增 21 个用例（本轮实测 21/21 PASS）：14 列解析、N/A→None、短行丢弃、带引号逗号卡名、缺 UUID 退卡名、**index 0/1 互换而 UUID 稳定→身份不串卡**、注入机制确认已删、`/monitor` `/monitor.js` 内容与路由、`/` 不认领、临时端口 19091 最小服务 HTTP 级断言 | 防回归 |
| `bootstrap.py` | `REQUIRED` 加 `monitor.html` `monitor.js` `selftest_monitor.py`（13 项）；`--check` 的 `web_root` 提示改为「已弃用，监控页自带 /monitor」；`--selftest` 跑三套 | 口径一致 |
| `config.template.json` | `comment` 重写：web_root 弃用说明 + 监控页地址 + 按卡身份绑定说明 | 模板不把人往坑里带 |
| `README.md` | 第二节配置表 `web_root` 行移除并注明弃用；第五节第 5 条改为打开 `/monitor`；第六节整节重写（自持页 + UUID 绑定 + 6.1 从旧注入式升级的一次性操作：重启一次走 `switch_proxy.py`、给 `index.html.orig` 恢复命令（不执行）、旧 `ext.js` 退役路径）；自测口径改三套 | 部署说明必须如实 |
| `SKILL.md` | 第 3 步 `web_root` 口径、验收第 5 条 `/monitor`、`--selftest` 三套口径同步 | Agent 工序与人类文档一致 |

**11-16 二稿补修（工程复核后，同一轮登记）**：①`monitor_ext.py` `GPU_QUERY` 编解码字段名改驱动实证名（见上表，真 bug）；②`selftest_monitor.py` 对字段名断言收紧（断言含 `utilization.encoder/utilization.decoder` 且不含旧名）；③`CHANGELOG.md` 更正 11-12 段不存在的 `archive/` 回滚件说法；④`README.md` 第八节 / `SKILL.md` 运维段 / 本节补**看门狗划界**：本包 `ledger_watchdog.py` 只守护本包记账反代（`listen` 端口），Strata 官方引擎壳（`terminal/serve/server.py`）自带引擎进程看护，与本包看门狗无关、不碰不依赖；⑤`bootstrap.py` docstring 与用法行「两套」改「三套」、本节第五节「两套回归」改三套；⑥`README.md` 6.1 第 3 条补「旧注入页过渡期仍按槽位分桶、仍可能串卡」提示，第六节补 `/monitor` 自身故障退回路径（退旧 ZIP 整包；shim 不兜 /monitor 故障）。

**契约不变量未动**：流式逐块转发、响应头透传、按 key 记账、`ts` 取请求开始时刻、32 MiB 副本上限、排队 128、看门狗「只在端口关闭时拉起自己的子进程」、切换「有会话硬拒绝且 `--force` 不覆盖」。`/ext.json` 只增字段（`uuid/mem_util/enc_util/dec_util/gpu_query_fields`），向后兼容：旧 `ext.js` 过渡期照常渲染。

**生产侧待办（本轮不执行，README 6.1 已给命令）**：生产 `terminal/serve/web/index.html` 里已注入的 `<script src="/ext.js">` 与 `<!-- monitor-ext -->` 需从同目录 `index.html.orig` 恢复；8080 记账反代需按切换纪律（先 `switch_proxy.py --check` 无人在线）重启一次才吃到新代码。本轮未启动 / 停止 / 重启 / 连接 / 占用任何生产服务端口。

---

### 2.9 监视页三稿：官方监视页完整复刻 + 硬件卡融合视图（2026-11-16 三稿）

升级动机（用户拍板终极形态）：把二稿的「简单自持卡片页」重写为「官方 Strata 监视页的完整复刻 + 本包硬件卡」融合视图——视觉与之前寄宿在官方页的形态一致，但页面、CSS、图标、数据请求、渲染全部是本包自有文件，零注入、零依赖官方页 DOM / CSS / sprite。

| 文件 | 改动 | 为什么 |
|---|---|---|
| `monitor.css` | **新增**：官方 `tokens.css` 全套 `--st-*` 设计令牌（light/dark 两套，accent 等同值）、`components.css` 组件类子集（st-card / st-metric__* / st-progress / st-gauge / st-table / st-badge / st-btn / st-input）、`app.css` 监视布局段，逐条移植为包内自有文件；字体退系统栈（官方 Outfit woff2 不拷） | 视觉一致但运行时零依赖官方 CSS 文件 |
| `monitor-sprite.svg` | **新增**：从官方 sprite.svg 逐字提取页面用到的 12 个 symbol（gauge/gpu/layers/thermometer/bolt/link/cpu/disk/memory/experts/sun/moon）；文件头注释自报出处 | 图标几何一致但本包从不加载官方 sprite |
| `monitor.html` | 重写为融合视图骨架：`mx-header`（含 `#mx-status` 断源指示 + 主题按钮，主题读写官方同键 `strata.theme`）；模型状态卡（6 中文徽章 + 进度条）；`#metrics` 融合卡网格；Context fill 卡（环形仪表 dasharray/rotate 同官方 + Experts in VRAM / System RAM / GPU temperature 三条进度）；Recent requests 表 9 列（中文表头）+ totals；Conversation cache 卡；`#apikey-row` 小输入框（401/缺 key 时出现）；页脚自报「本页为 Strata 账本工具自持页面…不加载其他网站资源」 | 页面结构照官方监视页复刻，内容归本包所有 |
| `monitor.js` | 重写：每秒 `Promise.all` 并发 fetch `/ext.json`（本包硬件采样）与 `/metrics`（反代原样转发引擎 8787），两源独立容错、任一失败只影响自己半边渲染；渲染函数对照官方 app.js 口径：renderState（徽章点亮条件同官方）、renderSpeed（tok_s 主曲线 + prefill 副曲线，波形优先引擎 `history` 数组、无则本地 180 点缓冲）、renderCpu（`/metrics` 有 `hardware.cpu` 才画）、renderGpus（每卡按 **uuid** 绑卡与历史、index 仅展示、含显存/显存利用率/编码/解码/温度/功率/SM 时钟——不含官方单卡 load/VRAM 重复卡）、renderRam（`/ext.json` 含 swap）、renderDisks/renderNet（每物理盘、每已连接网卡 + 合计行）、renderCtx（ctx 环表 + 三条进度，双源混用）、renderRequests（9 列 + badge 映射 + hit_rate/PCIe/prefill 速率 + totals + 「全部」开关走 `/metrics?requests=all`）、renderConvCache；引擎 key 读写官方同键 `localStorage["strata.apikey"]`（JSON 字符串口径同官方 app.js），401/403 触发页面输入框存回同键；每张网格卡带 `data-mx-section`，`pruneSection()` 只清本区卡防跨区误删 | 融合数据来自两个源且必须互不拖垮；GPU 身份 UUID 契约不得回归 |
| `monitor_ext.py` | **唯一 py 改动**：`answer()` 增两条静态路由 `/monitor.css`（text/css）与 `/monitor-sprite.svg`（image/svg+xml），均走既有 `_read_asset()`（每请求现读磁盘，改静态资产不需重启 8080；此 py 改动上线需按切换纪律重启窗口，时机主理人定）。采样器 / 14 列 GPU_QUERY / `parse_gpu_csv()` / `start()` 签名一行未动 | 路由是唯一必须过 py 的部分；契约不变量全部保留 |
| `selftest_monitor.py` | 第 7 段断言改为融合页元素（`id="metrics"` / state-badges / ctx-fill / req-body / cc-card / `/monitor.css` / `/monitor-sprite.svg` 引用、页面不含 `web/sprite.svg` / `app.css` / `components.css`、js 含 `strata.apikey` 与 `/metrics`、css 含 `--st-accent`、sprite 含 8 个被引用 symbol）；HTTP 段新增 `/monitor.css`（text/css）与 `/monitor-sprite.svg`（svg content-type + 非空 body）用例；docstring 同步。用例数按当次实际输出报出 | 静态资产与「零官方依赖」是可自动化的断言 |
| `bootstrap.py` | `REQUIRED` 加 `monitor.css`、`monitor-sprite.svg`（13 → 15 项）：静态资产齐全断言落在装机自检 | 缺文件在 `--check` 就能看到而不是页面 404 |

**未动清单（三稿）**：GPU 采样线程、14 列契约与字段名、`parse_gpu_csv()`、`/ext.json` 结构、`collector_proxy.py`（反代本来就把 `/metrics` 原样转发引擎）、看门狗、切换纪律、记账主链、`ext.js` shim。官方 `terminal/serve/web/` 下任何文件未写。ZIP 未重打（打包由主理人统一做）。

**生产上线提醒（本包不代做）**：`monitor_ext.py` 的两条新路由需 8080 按切换纪律（先 `switch_proxy.py --check` 无人在线）重启一次才生效；`monitor.html/css/js/sprite` 四个静态资产本身是每请求现读磁盘，路由生效后替换即时可见、无需再重启。

---

### 2.10 监视页四稿：每卡 PCIe 链路字段 + 每卡多色实时线路波形（2026-11-16 四稿）

动机（用户指令，同日口径修订覆盖首版告警设计）：融合页此前只有一张来自引擎 `/metrics` 的 "PCIe" 卡，只描述引擎所用那张卡（Pro5000）；4090 实际 Gen4 ×8 在页面完全看不到。**用户修订口径**：本机 ×8 就是稳态正常值（7950X 平台双卡各 8 lane），Gen/宽度只作**中性信息展示，不做任何退化告警/红标**；展示形态 = 一张 PCIe 卡、每 GPU 一条彩色实时线路波形、图例标注卡名 + 链路规格 + 当前吞吐。首版实现过的退化徽章机制已全部移除，selftest 断言其不再出现。

| 文件 | 改动 | 为什么 |
|---|---|---|
| `monitor_ext.py` | `GPU_QUERY` 追加 4 列 `pcie.link.gen.current,pcie.link.width.current,pcie.link.gen.max,pcie.link.width.max`（14→18）；`GPU_FIELDS` 14→18；`parse_gpu_csv()` 新增 key `pcie_gen/pcie_width/pcie_gen_max/pcie_width_max`（`_num()` 容错 N/A；「不足 `GPU_FIELDS` 列整行丢弃」规则保留——旧 14 列形态同样被丢弃）。**每卡吞吐**：621.24 驱动无 `pcie.throughput.tx/rx` 查询字段（真机 rc=2 实证），改用 `nvidia-smi dmon -s t -c 2` 读 rxpci/txpci MB/s（取最后一行=完整 1s 窗样本），新增 `parse_dmon_txrx()` + `gpu_txrx_sample()`；采样线程 GPU tick 上**同 tick 按枚举序**与 uuid 配对写入每卡 `pcie_rx_mb/pcie_tx_mb`（跨 tick 身份一律 uuid 的契约不变）；`/ext.json` 顶层新增 `pcie_txrx_supported`（dmon 不可用时页面显示「不支持」） | dmon 单次 ~1.4s 在采样线程内跑，不阻塞反代与 /ext.json；引擎 `/metrics` 的 gpu_pcie_rx_mb 只描述引擎所用那张卡，不能当通用每卡数据源 |
| `monitor.js` | 顶部 PCIe 卡升级为「PCIe 线路」多序列图：`drawMultiSpark()` 每 GPU 一条固定色板线（6 色板，深浅色主题都可读），`hist.pcie[uuid]` 按 uuid 绑历史（卡消失清历史，与 GPU 卡同契约）；图例每卡一行 `卡名 · Gen5 ×8 · 360 MB/s`（纯文字，无 warn/danger tone）；引擎 `/metrics` rx 作「引擎侧实测」一条并入同图。GPU 卡副行加**中性** `PCIe Gen5 ×8` 文字段。首版的退化徽章机制（`badgeSlot`/`mx-badge--danger`/degraded 判据）**已全部移除** | 用户口径：×8 稳态正常、空闲降代 Gen1 也正常，不告警 |
| `monitor.css` | 新增 `.mx-legend`/`.mx-legend__row`（中性图例行，10×3px 色块与波形同色）；首版 `.mx-bdg`/`.mx-badge--danger` 已删除 | 样式表零告警元素 |
| `selftest_monitor.py` | 假 CSV 全部改 18 列（4090 行是空闲 Gen1 样本，按中性数据断言）；新用例：4 个 PCIe key 解析、链路字段中性断言、`GPU_QUERY` 含 4 条 pcie 查询且 `GPU_FIELDS==18`、**旧 14 列形态整行丢弃**、`parse_dmon_txrx()`（末行样本覆盖/垃圾行跳过/空输出）、js 含多序列渲染（`drawMultiSpark`/`SERIES_COLORS`/`mx-legend__row`/`pcie_rx_mb`）且**零告警残留**（`mx-badge--danger`/`degraded`/`badgeSlot` 必须缺席） | 防回归 + 防告警设计复活 |

**真机实证（621.24 驱动，只读）**：链路查询 rc=0——Pro5000 当前 Gen5 ×8 / max Gen5 ×16，4090 当前 Gen1 ×8（空闲降代）/ max Gen4 ×16，代码不写死代际；`pcie.throughput.tx/rx` 查询字段不存在（rc=2）→ 走 dmon 兜底；`dmon -s t` 可用：两卡 rxpci/txpci 有值（空载 Pro5000 rx≈0-19/tx≈3-303 MB/s、4090 全 0），采样线程集成后同 tick 配对实证写入成功。

**显示规则基线（主理人在生产副本热修，包内已同版，selftest 锁死不回归）**：GPU 卡标题只留卡名 + `#槽位`（无模式徽章）；大数字 = `util%` 后接模式徽章（`height:20px`，不再写 "% SM"、模式不挤标题）；卡图标统一走 `cardHtml opts.icon`，label 不带图标（修双图标偏右）。2026-11-16 晚实证：生产 `~\.workbuddy\skills\token-ledger\scripts\` 与包内 monitor.js/css/html/sprite/monitor_ext/collector_proxy/ext.js/paths.py **逐字节一致**——该目录即 8080 生产加载目录（热读），两边无版本落差；基线三条已写成 selftest 断言防下次改动覆盖回去。

**契约不变量未动**：UUID 身份、`/ext.json` 只增字段（`pcie_*` 链路四个 + 每卡 `pcie_rx_mb/pcie_tx_mb` + 顶层 `pcie_txrx_supported`，旧消费者向后兼容）、路由、记账主链。四稿含 `monitor_ext.py` 改动，上线需要 8080 按切换纪律重启一次窗口。

---

### 2.11 监视页五稿收口：PCIe 卡单卡化对齐 selftest + 重打 ZIP（2026-11-16 五稿）

背景：四稿上线后主理人在生产副本连续热修前端（已落母本与生产两边、字节级一致），最终形态与四稿描述有差：PCIe 卡从「每 GPU 一条线 + 独立图例区」简化为**单卡单线**——大数字 = 本轮 `pcie_rx_mb` 最大那张卡的即时 MB/s，小字固定两行（第一行固定文案「当前最高读速」，第二行 = `mx-sw` 短线图例 + 显卡名），独立图例区删除（`cardHtml` 不再传 `legend:true`、`mx-legend` 容器 `innerHTML` 置空）；磁盘/网卡卡小字改走 `innerHTML`（小字内嵌 `mx-sw` 短线图例 HTML）；`mx-sw` 为 10×3 短线。零告警纪律与显示基线不变。本轮**只改 `selftest_monitor.py` 断言与文档/打包**，功能代码一字未动。

| 文件 | 改动 | 为什么 |
|---|---|---|
| `selftest_monitor.py` | 作废「js 含 `mx-legend__row`（每卡图例行）」断言；对 PCIe 卡的断言改为五稿终态：lead 选择关键串（`if (!lead \|\| rx > (lead.pcie_rx_mb \|\| 0)) lead = g;`）、小字第一行固定文案「当前最高读速」、第二行 `sub.innerHTML = \`当前最高读速<br>${sw(leadColor)}…`；**新增**独立图例区缺席断言（js 不含 `mx-legend__row`、不传 `legend: true`、`-lg` 容器置空）；**新增** disks/net 小字走 `innerHTML` 断言；**新增** `.mx-sw` 10×3 短线断言；「告警缺席」断言保留并**加强**（js/css 同时断言 `mx-bdg`/`mx-badge--danger`/`degraded`/`badgeSlot` 全缺席）；「显示基线」断言原样保留。docstring 同步。当次 39/39 全绿 | 断言必须锁住前端终态而不是四稿旧形态；两组防回归纪律只增不减 |
| `README.md` | 第六节 PCIe 线路卡条目改为五稿终态描述（单卡单线 + 两行小字 + 图例区取消 + 磁盘/网卡短线图例），删除「图例逐行标注卡名/链路规格/引擎侧实测对照」的旧描述 | 文档与页面终态一致 |
| `MANIFEST.md` | 本节新增；头部修订口径更新 | 登记 |
| `CHANGELOG.md` | 新增五稿收口条目 | 登记 |

**母本↔生产实证（本轮）**：`monitor.html` / `monitor.js` / `monitor.css` / `monitor-sprite.svg` / `monitor_ext.py` / `collector_proxy.py` / `ext.js` / `paths.py` / `daily_report.py` / `html_report.py` 逐一 `cmp` 字节级一致（生产目录 `~\.workbuddy\skills\token-ledger\scripts\` 缺 `ledger_watchdog.py`/`selftest_*` 等属部署子集，不算分叉——生产侧另有本机运维版看门狗）。

**追加（磁盘/网卡大数字排版热修锁断言 + 再重打）**：主理人又一处前端热修（已落生产+母本、字节级一致）——磁盘/网卡卡大数字只留数值大号，单位 MB/s 与 `sw(RW_DOWN)` 读/下行标记全部收进 `<small>` 小字档。`selftest_monitor.py` 对应新增一条「disk/net 大数字的 读/下行 标记必须在 `</small>` 内」的精确形态断言（含反例守卫：标记不得回到大数字档），当次 **40/40** 全绿。ZIP 再次覆盖重打，仍 **29 文件**口径。

**追加（前端热修事故 + 三项形态锁断言 + 再重打）**：主理人再一批前端热修（monitor.js + monitor.css，已落生产+母本、cmp 字节级一致），其中含一起**线上事故**：上一版热修引用了未定义常量 `SPEED_DECODE`/`SPEED_PREFILL`，页面 JS 抛 ReferenceError，**所有读数全部消失**（用户线上实锤）。修复为 CSS 类方案：js 顶部 `swc(cls)` 助手 + 速度卡小字图例 `swc("mx-sw--decode")`/`swc("mx-sw--prefill")`；css 新增 `.mx-sw--decode{background:var(--st-accent)}` / `.mx-sw--prefill{background:color-mix(in srgb,var(--st-accent) 65%,black)}`（与波形两线同色随主题）。本轮 `selftest_monitor.py` 新增四组锁定：①**事故回归**——js 中 `SPEED_DECODE`/`SPEED_PREFILL` 标识符永不允许出现 + swc 定义与两个 CSS 类必须在位；②速度卡图例形态（subD/subP innerHTML 以 swc decode/prefill 开头）；③磁盘/网卡大数字 **`&nbsp;` 形态**更新（作废上一轮普通空格逐字节断言，反例守卫保留）；④CPU 单插槽路径原形态锁死 + 多插槽分支（`hw.cpu_sockets` >1 → speed 版式 + `hist.cpuSock` 分桶）存在性断言。**另新增 node 冒烟守卫**（内联在 selftest，运行时生成临时 harness，不增包内文件数）：以最小 DOM stub 真跑 monitor.js IIFE + tick 渲染链（/metrics 先 401 后 200 含多插槽 CPU 数据），任何 ReferenceError/TypeError/未处理 rejection 即红——`node --check` 抓不到未定义标识符，只有真跑能抓（正是本次事故的类）。无 node 的机器该守卫记跳过不记失败。当次 **45/45** 全绿；ZIP 再覆盖重打，仍 **29 文件**口径。

**追加（磁盘/网卡卡重构 + CPU 卡图例 + 小字基线对齐，断言对表 + 再重打）**：主理人同批四路前端热修（monitor.js + monitor.css，均已落生产+母本、cmp 字节级一致）：①**磁盘卡重构**——标题 `#编号 盘符 型号 · 容量`（`const head = [\`#${d.number + 1}\`]`，内部 0 基、显示从 #1 起），大数字 = 数值 + `<small>` 单位 + 总线规格徽章（`d.bus` 去 `Disk N · ` 前缀），读/写移入小字两行（绿/橙短线）；②**网卡卡**——无线标题「无线网卡」且**不出徽章**、有线标题 = 适配器真名 + 「有线」徽章（中途方案 `NET_KIND_LABEL`/WLAN 徽章已废，断言反向锁死其永不复活），下/上行小字两行；③**CPU 卡图例**——多插槽小字左右 `swc("mx-sw--cpu1"/"mx-sw--cpu2")` + `subOf()`，单插槽小字 `swc("mx-sw--cpu1")` + 核/线程或「整机」兜底（旧 `setSub(id + "-s", st.threads…)` 作废），css 新增 `.mx-sw--cpu1/--cpu2`（info 主题变量），`.st-metric__spark .speed-prefill` 由写死 accent 改 `currentColor 65%` 使右线恒与所在卡主线同色加深；④**小字基线对齐骨架**——`cardHtml` 标题文本包 `<span class="mx-label-t">`（恒一行+省略号），css `.st-metric__value` 加 `min-height:var(--st-fs-stat);white-space:nowrap`（大数字行定高，徽章不撑行）；⑤**GPU 卡序号前置（rev7c）**——标题 = `<span class="muted" title="槽位号会漂，仅供对照，不作为身份">#index+1</span> 卡名`（与磁盘同款、从 1 起），旧 0 基 `${esc(g.index)}` 形态转反例守卫。追加 CSS 微调（rev7b，用户定位小字被压低的真凶=大数字后 `.st-badge` 行内块按基线对齐撑高行框）：中途做过 `.st-metric__value` 加 `inline-flex` 的方案，因间距副作用**已撤销**——终态只新增 `.st-metric__value .st-badge{vertical-align:middle}`，`.st-metric__value` 规则行保持原串+`min-height`+`white-space:nowrap`。断言对表：作废旧「&nbsp; 大数字」两条与 `NET_KIND_LABEL`/`cardHtml … esc(a.name)`/单插槽 `setSub` 旧锁，新锁 disk rev6（`#${d.number + 1}`、spec 徽章、&nbsp; 反例守卫）、net rev6b（无线标题/有线徽章串逐字节、`NET_KIND_LABEL`+`WLAN` 缺席守卫）、cpu 图例（三形态串 + `setSub` 旧行缺席守卫）、图例配色三条 CSS、骨架两条（label 包装行 + `mx-label-t`/`min-height` CSS + `.st-metric__value .st-badge{vertical-align:middle}` 在位与 `display:inline-flex;align-items:center;gap:0` 反例守卫）、gpu 标题 rev7c（muted `#${esc(g.index + 1)}` 前置整串逐字节 + 旧 0 基 `${esc(g.index)}` 缺席守卫）。node 冒烟 stub 的 disks 行含 `number/model/bus/drives/size`、net 行含 `name/kind/down_mb/up_mb`，两卡渲染真跑不抛。当次 **50/50** 全绿；ZIP 再覆盖重打，仍 **29 文件**口径。另：CHANGELOG 顶部补写 **monitor-rev6** 条目收拢本批叙事（含 ReferenceError 事故）。

**重打包**：`strata-ledger-proxy-2026-11-16.zip` 覆盖旧 27 文件版，按包内实际全量重打（根 23 + `service-examples/` 3 + `legacy/` 3 = **29 文件**，`__pycache__` 不入包），打包后以 `zipfile.namelist()` 核对数量。未启动 / 停止 / 重启任何生产进程；8080 未动。

---

### 2.12 rev8 后补：`config-examples/` 样例 + README 真机实测登记（2026-11-17 · 纯文档/样例，功能代码零改动）

背景：两台机器（000 · Windows 5090 单卡、002 · Linux PRO 5000 + 4090 双卡）跑过之后，皮总问「这两台的样例/经验能不能进仓」。判定＝**硬件型号不是本包配置项**（监控按 UUID 动态逐卡发现，配置里没有也无需有机型字段），所以机型不进 `config.json`；可进仓的是两样：①结构示范（脱敏实例配置），②与本包功能相关的实测结论（免得下一台机器重踩）。真实拓扑、真实 IPv6、key 指纹、成员姓名一律不进。

| 文件 | 改动 | 为什么 |
|---|---|---|
| `config-examples/windows-5090-single-gpu.json`（新增） | 000 在岗 `config.json` 实机抄录，仅 `key_labels` 清空；comment 改写为示范口径（IPv6 双栈门面、引擎退环回、lock 避让改值） | 在岗跑通的形态比模板抽象描述更有说服力；直接示范 rev8 双栈写法 |
| `config-examples/ubuntu-pro5000-4090-dual-gpu.json`（新增） | 按模板缺省口径组装的 Linux 双卡装配参考（**非实机抄录**，comment 内如实注明）；示范双卡零配置、缺依赖降级、systemd 口径 | 双卡异构组合最容易让人以为要配显卡——样例的 comment 就是把这层口径随身带上 |
| `README.md` | 第二节第 3 步末尾加「两份真机形态样例」导读表；**新增第十一节「真机实测登记」**（6 条：双栈类属性修与换脑定式 / Win11 注册表 `~MHz` 废源与 PDH 正确源 / 消费卡 ASPM Gen1↔Gen5 链路本态 / 双卡 UUID 自动发现与 `ext.js` 串卡退役 / 缺依赖降级与「装进服务实际用的解释器」/ 登录环境无交互 PATH→自启件绝对解释器路径）。章节编号追加在末尾，既有「第 N 节第 M 条」交叉引用不受影响 | 实测结论不登记，下一台机器就会重踩；登记限定在与本包功能相关的范围 |
| `MANIFEST.md` | 修订口径更新；第一节文件数 29→**31**（新增 `config-examples/` 2 个）并补两行通配登记；本节新增 | 登记 |
| `CHANGELOG.md` | 新增 rev8 后补条目 | 登记 |

**脱敏实证**：两份样例全包扫描——真实 IPv6 地址 0 命中（000 在岗文件里的 `listen` 是 `:::8080` 通配写法，本就不含地址字面量）、真实指纹与真人姓名 0 命中、机器代号（000/002）不出现在样例正文（只按「Windows 单卡终端 / Linux 双卡工作站」中性描述），git 提交信息同口径。

---

### 2.13 第十一节改版：结论式 → 症状式踩坑登记（2026-11-17 · 纯文档，功能代码零改动）

背景：皮总问「两台终端踩过的坑是否也该入仓做经验参考」。判定＝该沉淀，但不进 `config-examples/`——那里是实体样例位（可直接拷改的配置件），坑是知识不是配置，混入会稀释目录语义；正确容器就是第十一节。改版方向：排障的人先看到症状、不知道要找什么，所以六条结论式全部改写为「**症状 → 根因 → 对策**」三段式，节名同步改「真机踩坑登记」。

| 文件 | 改动 | 为什么 |
|---|---|---|
| `README.md` | 第十一节整节改写：原 6 条转三段式；**新增 4 条**——②「gaierror 11001 无限重拉」独立成条（002 首版在跑的人升级指引）；③「引擎区红≠本工具坏」（`/metrics` 浏览器直连引擎、与反代两条独立链路、先分半页再查引擎）；⑨「端口口径全网统一：门面 8080 / 引擎环回 8787，漂移一处全网记例外」；⑩「listen+防火墙+看门狗三件套同轮改，防『端口通但没人守』」。共 10 条 | 结论式对人不可检索，症状式可对照；后 4 条全是实机交过学费的，不登记下一台照踩 |
| `MANIFEST.md` | 本节新增；2.12 历史条目保留当时口径不回改 | 登记 |
| `CHANGELOG.md` | 新增改版条目 | 登记 |

**不入仓边界（同轮裁定，如实登记）**：宿主平台行为（automation 模型绑定、工具假报成功）、本机网络形态（push 走代理回退 HTTP/1.1）、执行沙箱限制（计划任务黑名单）、另一条产品线的档案（生成网关的 speed_bias 与池拓扑）——均与本包无关，写入会误导部署方，一律不入。

---
## 三、如实登记：代码分叉

这套脚本与 5090 工具包里的 `skill-token-ledger/scripts/collector_proxy.py`（母本，260 行）**不是同一份文件**：

- 母本是原型：按 key 归因的能力已有，但转发是 `resp.read()` 整包缓冲，且没有看门狗、日报合并、硬件监控、切换保护、回归自测。
- 本包基于本机实例版（641 行），已修整包缓冲并补齐上述能力，又额外打了 2.1 节登记的那些移植补丁（数量以该表实际行数为准，不写死）。

⇒ **以后改功能要两边对照同步**，不存在单点收口。本包是独立发行版，改它不会自动影响另一台机器上的生产脚本，反之亦然。2026-11-11 轮的归因修复已按此原则两边同步改磁盘，当时两边进程都未重启；此后生产 8080 已于 2026-11-12 20:19 切换到 11-11 修复版并实证生效。2026-11-12 轮又按此原则把看门狗的「端口跟随 config / POSIX 脱离会话」行为两边对齐（生产看门狗进程待主理人交接，见 2.6 节）。

带过来的 5090 母本能力（`force_include_usage`、非 2xx 落账、`--fp` 算指纹、按 key 映射）都保留了，没有丢。

---

## 四、明确没有带过来的东西

| 5090 旧链有 | 本包情况 | 影响 |
|---|---|---|
| 完全不进业务链路 | 做不到，反代天然在中间 | 故障面更大，靠守护进程 + 切换纪律兜住 |
| 断点续读（offset）、断线回放 | 不需要，代理直接截获响应，没有日志可追 | 无 |
| 开机补跑昨天日报 | 改为「服务启动先查一次」，效果等价 | 无 |
| `prefill_tok_s` 字段、并发事件行 | 本链不产生 | 旧数据在网页报表里少一列，日报不受影响 |

---

## 五、交付前验证（由 QA 独立复核）

- 包内全部 `.py` 语法编译通过。
- 在**全新临时目录**复制整包、生成配置、用临时端口跑 `selftest_proxy.py`、`selftest_watchdog.py` 与 `selftest_monitor.py`；三套回归按**实际用例数**报出，不写死历史数字。
- 生产 `usage/selftest_watchdog.py` 单独跑通并按当次实际用例数报出；单独实测生产看门狗新增的自包含 `ports_from_config()`（正常配置 / `[::]:端口` / 坏 JSON / 端口非数字 / 缺 `watchdog_lock_port`）与显式 `--port` / `--lock-port` 优先语义。
- 两个启动夹 VBS 可执行语句与注释全 ASCII、CRLF 换行，命令行含 `--lock-wait 86400`；可由 VBScript 解析（静态检查，不真执行）。
- 2026-11-12 ZIP 为 24 文件，只含 `config.template.json` 不含 `config.json`，`start.sh` 包内权限 0755，`start.bat` 保持 GBK + CRLF；全包（源 24 + 包内 24）真实指纹与真人姓名 0 命中。
- `bootstrap.py --check` 用临时端口配置跑通；坏配置（大写 hex 键、空姓名、同姓名合并、`lock_port == watchdog_lock_port`、空 `key_labels`）确实能报出对应的 fail / warn。
- 全包扫描：所有 `.py` 代码零硬编码（无盘符、无用户名、无 Python 版本路径）；文档以占位方式描述来源，不含真实 key 指纹与真人姓名。
- 伪装 `sys.platform` 为 `linux` / `darwin` 跑路径与端口分支，不崩；缺 `lsof` 时安全降级。
- 确认全程未连接、未占用、未重启生产端口；8080 监听 PID 在交付前后保持一致。
