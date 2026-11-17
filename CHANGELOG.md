# 版本改动登记（CHANGELOG）

倒序登记本包历次改动。详细逐项改动对照表见 `MANIFEST.md` 第二节；本文件只做人读摘要，不重复展开。

---

## 2026-11-17（rev9）· CPU 卡标题带型号（`ext.cpu_name`）

- **采样端**：`monitor_ext.py` 新增 `cpu_name()`——Windows 走注册表 `ProcessorNameString`（与任务管理器显示同源），Linux 走 `/proc/cpuinfo` 的 `model name`；纯标准库、静态读一次进缓存；多余空格折叠、64 字符截断、任何失败返回空串——**采不到就保持光 "CPU" 标题，绝不编名字**。字段进 `/ext.json` 为 `cpu_name`。
- **前端**：CPU 卡（单插槽与多插槽两分支）标题变 `CPU · 型号`；`ensure` 只在卡片首建时写标题，而 `/ext.json` 可能晚于 `/metrics` 到——label 节点每拍**幂等刷新**补齐。型号过长进 `mx-label-t` 一行省略号口径，不撑卡。
- **selftest** 52/52（新增两条：标题两分支+幂等刷新+裸标题永不复活的反例守卫；采样端源锁〔注册表键/proc 路径/空格折叠/截断〕）；proxy 22/22、watchdog 16/16 不变。node 冒烟 stub 喂含 `<x>` 的型号名走 `esc` 转义链。
- 在岗换脑走 `switch_proxy.py`：第一轮判有 2 条 idle 连接**硬拒绝**未 force（纪律优先于便利）；第二轮在操作会话处工具段、无在飞生成的安全窗 `--force` 切成——1.52 秒回岗、`/ext.json` 出 `cpu_name`（AMD Ryzen 9 7950X 16-Core Processor）、前端实拍确认标题一行不撑。README 硬件区截图同步刷新为带型号版。

---

## 2026-11-17（rev8 后补四）· README 配真机在岗截屏两张（纯文档，功能代码零改动）

- 新增 `docs/monitor-hardware.png` / `docs/monitor-ledger.png`：`/monitor` 页真机在岗实拍（Edge headless 截取后按内容边界裁切），插在第一屏卖点区——上半页逐卡逐盘逐网卡硬件读数，下半页逐请求 token 账＋合计行＋对话缓存卡，配两句读法图注（82% 输入复用 ↔ 解码稳 110+ tok/s；深浅两套主题、按 UUID 绑卡）。
- **坚持实拍不示意图**；脱敏双检（截图前目检＋入仓前复检）：无指纹/姓名/key/IPv6——该机无 key 模式，请求表本就无身份列；MANIFEST 新增 2.15 节并登记文件数 31→33。

---

## 2026-11-17（rev8 后补三）· README 开头重写为价值主张开场（纯文档，功能代码零改动）

- **标题区重写**：问题式定位（谁在用 / 用了多少 / 这台机器扛不扛得住）＋五条卖点——①账按人算、数字取引擎官方字段；②长生成不掐线（逐块转发、首字节约 0.01 秒，含「号称流式实为整包缓冲」这个坑的实机 A/B 实证）；③开箱监控页（异构逐卡、读数与任务管理器同源）；④5 秒自愈＋有人用即拒切换；⑤零依赖主链仅标准库。随后紧跟「代价也先说清楚」段引流第九节，再接「三分钟上手」命令块（clone→init→check→start）。
- **第一节主语通用化**：从「我们内部旧链 vs 本工具」改为「自己写脚本读引擎日志的通用做法 vs 本工具」——外部访客没有我们的旧链，对照对象必须是他们会走的路。
- **两处如实化**：开头引用块里指向内部工具包路径的提醒删除（分叉事实仍登记于 MANIFEST 第三节与 SKILL.md，公开仓不写只有我们可达的路径）；macOS 从「实测跑通」改为「同套启动件＋平台模拟验证」（无 macOS 实机，不混称实测）。
- 第二节往后的实操章节口径一律未动。

---

## 2026-11-17（rev8 后补二）· 第十一节改版为「真机踩坑登记」（纯文档，功能代码零改动）

- 原 6 条结论式全部改写为「**症状 → 根因 → 对策**」三段式——排障的人先见到症状、不知道要找什么，结论式不可对照。节名同步改「真机踩坑登记」。
- **新增 4 条**（共 10 条）：②`gaierror 11001` 无限重拉单列成条，附「002 首版在跑先 `git pull`」升级指引；③**引擎区红≠本工具坏**——监视页上半区是浏览器直连引擎 `/metrics`，与反代两条独立链路，先分半页再查引擎进程与 `upstream`；⑨**端口口径全网统一**：门面 `8080`、引擎退环回 `8787`，各机只改数值内的东西，偏离＝全网变更不是本机自由；⑩`listen`+防火墙放行+看门狗重启**三件套同轮**完成，防「端口通但没人守」。
- 不入仓边界同轮裁定：宿主平台行为、本机网络形态、执行沙箱限制、另一产品线档案——与本包无关，一律不入。

---

## 2026-11-17（rev8 后补）· 样例与实测经验入仓（纯文档/样例，功能代码零改动）

- **新增 `config-examples/`**：两份脱敏实例配置——`windows-5090-single-gpu.json`（Windows 单卡终端**在岗实机抄录**，示范 IPv6 双栈门面 + 引擎退环回 + lock 避让改值）与 `ubuntu-pro5000-4090-dual-gpu.json`（Linux 双卡工作站**装配参考**，示范双卡零配置、缺依赖降级、systemd 口径）。机型不是本包配置项（监控按 UUID 动态逐卡发现），样例只示范结构与端口口径；真实地址、指纹、姓名 0 命中。
- **README 新增第十一节「真机实测登记」**：限定与本包功能相关的实测结论 6 条——①IPv6 双栈地址族须在实例化前定类属性（rev8 修）＋改 listen 必重启看门狗（旧脑闪窗定式）；②Win11 注册表 `~MHz` 钉死基准＝废源，实时频率唯一正确源＝PDH × 基准（`PdhClock` 已内置）；③消费卡空闲 ASPM Gen1、负载 Gen5 是链路本态非读数陈旧（饱和拷贝实验实证）；④双卡异构组合无需配置，旧 `ext.js` 槽位分桶有串卡风险已退役；⑤缺 `psutil`/`nvidia-smi` 只降级监控，补装要装进**服务实际使用的那个解释器**；⑥登录环境无交互 PATH，自启件解释器一律绝对路径。
- 第二节第 3 步加样例导读表；`MANIFEST.md` 同步（文件数 29→31、新增 2.12 节）。

## 2026-11-17（rev8）· 000 实测场：双栈监听修复 + CPU/PCIe 卡实时增强 + 改 git 仓分发

全部改动在 000（5090 单卡终端）实测验证后回流。本仓为该包首个 git 分发形态（此前以 zip 传递）。

- **[bug 修] IPv6 双栈监听必炸**：`collector_proxy.py` 的地址族在 `server_bind()` 里才定——但 socketserver 先建 socket 后调 bind，AF_INET 套接字绑 `::` 必 gaierror 11001，看门狗连拉数十次起不来。修法＝地址族在实例化前定为类属性（host 含 `:` → AF_INET6，IP_V6ONLY=0 双栈）。实测：v4+v6 `/health` 双绿、看门狗 5 秒巡检补岗生效。**002 母包需带此修。**
- **CPU 卡大数字后跟实时 GHz（两轮，第一轮被实锤作废）**：第一轮取注册表 `~MHz`——Win11 上它钉死基准频率（实测常年 4500，睿频不进，任务管理器并不读它），4500↔4501 的"吻合"是撞低频瞬间。第二轮＝新增 `PdhClock`（ctypes → pdh.dll，纯标准库无新依赖）：PDH 计数器 `\Processor Information(_Total)\% Processor Performance`（英文计数器路径，中文系统 locale-proof）× `MaxClockSpeed` 基准，与任务管理器"速度"完全同源。实测 5.06–5.15 GHz 跟随负载。任何失败＝字段缺失、前端自动省略，不破账纪律不变。**定式：Windows 实时 CPU 频率唯一正确源＝PDH × 基准频率；注册表 `~MHz` 不可用。**
- **PCIe 线路卡大数字后跟领先卡实际链路 `GenN ×W`**：数据源 nvidia-smi `pcie.link.gen/width.current`（NVML 即时查询，不落注册表）。A/B 饱和拷贝实验验证读数真实：空闲 Gen1×16/SM 195MHz → 9 秒固定内存 H2D 搬运 418.8GiB（≈46GB/s，Gen5 量级，物理上排除虚报）→ 瞬跳 Gen5×16/2902MHz → 停载后 ASPM 延迟降档属链路本态，非读数陈旧。
- **`selftest_monitor.py` 断言对表**：CPU 单插槽大数字断言放宽为「`%` 大数字＋可选 GHz 后缀（门控 `ext.cpu_mhz`）」形态；新增反例守卫＝旧无 GHz 行形态与无门控路径永不复活。当次 **50/50** 全绿；proxy 22/22、watchdog 16/16 不变。
- **分发形态改 git**：仓库只含包体。本机专属件一律不入库（`.gitignore`：`config.json`、`data/`、`*.log`、`relaunch-now.flag`、本机启动 bat）——换机安装走 `python bootstrap.py --init`（template→config，从不覆盖已有配置）。端口口径按 README 缺省：门面 `listen 8080`、引擎环回 `upstream 127.0.0.1:8787`；`lock_port`/`watchdog_lock_port` 按各机在用软件避让自选（000 填 43180/43179 避旧链）。

---

## 2026-11-16（monitor-rev6）· 监视页六稿：磁盘/网卡/CPU 卡形态重构 + 小字基线对齐 + 一起前端事故的收拢

对应 `MANIFEST.md` 2.11 节（明细对照表在该节，此处只收拢叙事）。主理人在生产连续热修前端，本席做「断言对表 + node 冒烟 + 重打 ZIP」收口；功能代码改动均已落生产+母本两边、字节级一致。

- **线上事故与修复（先登记）**：五稿收口后的一版热修引用了未定义常量 `SPEED_DECODE`/`SPEED_PREFILL`，页面 JS 抛 ReferenceError，**所有读数全部消失**（用户线上实锤）。修复为 CSS 类方案（`swc(cls)` 助手 + `.mx-sw--decode/--prefill`）。**新增 node 冒烟守卫**：selftest 内联最小 DOM stub 真跑 monitor.js IIFE + tick 渲染链——`node --check` 抓不到未定义标识符，只有真跑能抓（正是这类事故）；js 中 `SPEED_DECODE`/`SPEED_PREFILL` 永不允许出现（回归断言锁死）。
- **磁盘卡重构**：标题 = `#编号 盘符 型号 · 容量`（编号内部 0 基、显示从 #1 起）；大数字 = 数值 + 单位 + 总线规格代码徽章（去 `Disk N · ` 前缀）；读/写移入小字两行（绿/橙 10×3 短线图例）。
- **网卡卡**：无线网卡标题就叫「无线网卡」且不出徽章；有线网卡标题 = 适配器真名 + 「有线」徽章（中途 `NET_KIND_LABEL`/WLAN 方案已废，断言反向锁死永不复活）；大数字 = 下行数值 + 单位；小字两行 = 下行/上行。
- **CPU 卡图例**：双插槽时左右小字各一条短线对应左右波形色；单插槽也有图例（短线 + 核/线程或「整机」）；波形右线（预填充色）改 `currentColor 65%` 加深——图例颜色恒与所在卡波形色一致。
- **小字基线对齐**：各卡「大数字下面的小字」起始高度统一——`cardHtml` 标题文本包 `mx-label-t`（恒一行 + 超长省略号）、`.st-metric__value` 定高（徽章撑不高行）；徽章撑高行框的真凶用 `.st-metric__value .st-badge{vertical-align:middle}` 修掉（中途 `inline-flex` 方案因间距副作用已撤销并有反例守卫）。
- **GPU 卡序号前置**：标题改为 `#序号 + 卡名`（与磁盘同款、从 1 起），序号带「槽位号会漂，仅供对照，不作为身份」提示；旧「名称在后带 0 基 #index」形态有反例守卫。
- **`selftest_monitor.py`**：断言按以上终态对表（作废旧 `&nbsp;` 大数字、`NET_KIND_LABEL`、单插槽 `setSub`、0 基 `#index` 四组旧锁并转反例守卫），当次 **50/50** 全绿；proxy 22/22、watchdog 16/16 不变。
- **重打包**：`strata-ledger-proxy-2026-11-16.zip` 覆盖重打 **29 文件**，解包实测三套全绿；未启动/停止/重启任何生产进程，8080 未动。

---

## 2026-11-16（monitor-rev5）· 监视页五稿收口：PCIe 卡单卡化对齐 selftest + 重打 ZIP

对应 `MANIFEST.md` 2.11 节。摘要：

- **前端终态登记（主理人热修已落两边，本轮未改功能代码）**：PCIe 线路卡简化为单卡单线——大数字 = 本轮读速最快那张卡的即时 MB/s；小字固定两行（「当前最高读速」+ 同色短线图例与显卡名）；独立图例区删除。磁盘/网卡卡小字走 `innerHTML`（内嵌 10×3 `mx-sw` 短线图例）。零告警纪律与显示基线不变。
- **`selftest_monitor.py` 对齐**：作废「每卡图例行 `mx-legend__row` 存在」断言；PCIe 卡断言改锁五稿终态（lead 选择逻辑关键串、「当前最高读速」固定文案、小字 `innerHTML` 图例+卡名）；新增独立图例区缺席、disks/net `innerHTML`、`.mx-sw` 10×3 短线三组断言；「告警缺席」断言加强（js+css 同时断言四类告警元素全缺席）、「显示基线」断言原样保留。当次 **39/39 全绿**。
- **文档同步**：README 第六节 PCIe 卡描述改为五稿终态；MANIFEST 新增 2.11 节并更新修订口径与文件表。
- **重打包**：`strata-ledger-proxy-2026-11-16.zip` 覆盖旧 27 文件版（旧版漏打 `monitor.css`/`monitor-sprite.svg`），按包内全量重打 **29 文件**，打包后 `zipfile` 核对。
- **母本↔生产**：核心件逐文件 `cmp` 字节级一致；未启动 / 停止 / 重启任何生产进程，8080 未动。

---

## 2026-11-16（monitor-standalone）· 监控页重构：自持独立页，按卡的唯一身份绑卡

对应 `MANIFEST.md` 2.8 节。摘要：

- **彻底弃用官方页面注入**：删掉整套「往 Strata 控制台页面塞脚本」的机制（`attach/pages/Watcher`）。本工具从此不写任何它不拥有的页面；配置里的 `web_root` 字段弃用（留着不报错，可删）。
- **自带监控页**：打开 `http://<主机>:<端口>/monitor` 即完整监控页（`monitor.html` + `monitor.js`，数据走同源 `/ext.json`），卡片布局大数字+副行+波形，零第三方依赖，深浅色跟随系统。
- **修根因**：旧注入页把显卡波形按 nvidia-smi 槽位号存历史，而槽位号会漂（本机实证：A 卡波形画到 B 卡卡片上）。新页一律按显卡唯一身份（UUID）绑定卡片与波形历史，槽位号只在标题展示；极老驱动没有 UUID 时退卡名，绝不退槽位。
- **数据接口只增不改**：`/ext.json` 的 GPU 行新增 `uuid`、显存/编码/解码利用率四个字段（nvidia-smi 查询 10 列 → 14 列）；旧注入页过渡期照常渲染。`/ext.js` 仅为过渡兼容保留，官方页恢复原状后即可退役。
- **新增第三套回归 `selftest_monitor.py`**（本轮 21/21 通过；含「槽位 0/1 互换、唯一身份不变→历史不串卡」用例）。`bootstrap.py --selftest` 现跑三套。
- **记账主链零改动**：`collector_proxy.py` 只改了文档注释和一行启动提示；转发契约、记账、看门狗、切换纪律全部未动。
- **同日工程复核后补修（11-16 二稿）**：①`GPU_QUERY` 编解码字段改驱动实证可用的 `utilization.encoder/utilization.decoder`（旧名 `encoder.utilization/decoder.utilization` 在 621.24 驱动下整条 nvidia-smi 查询 rc=2 失败、所有显卡消失——真 bug，真机复验新名 rc=0 双卡 14 列全解析）；②更正 11-12 段不存在的 `archive/` 回滚件说法；③README/SKILL/MANIFEST 补看门狗划界：本包 `ledger_watchdog.py` 只守护本包记账反代，与 Strata 官方引擎壳（`terminal/serve/server.py`）自带的引擎进程看护无关、不碰不依赖；④`ext.js` 本轮跨源 API 解析改动补登记进 MANIFEST 2.8；⑤`bootstrap.py` 自测口径「两套」改「三套」；⑥README 补旧注入页过渡期仍按槽位分桶可能串卡的提示、补 /monitor 自身故障的退回路径。
- **同日三稿：`/monitor` 升级为官方监视页完整复刻 + 硬件卡融合视图**（用户拍板终极形态，对应 `MANIFEST.md` 2.9 节）：视觉与之前寄宿官方页的形态一致，但页面、样式、图标、数据、渲染 100% 本包自有文件——新增 `monitor.css`（官方 st-* 令牌/组件/布局逐条移植，深浅色两套）与 `monitor-sprite.svg`（12 个图标 symbol 逐字拷自官方 sprite）；`monitor.html`/`monitor.js` 重写为融合视图（模型状态卡、Speed 双曲线、每 GPU 卡按 UUID 绑定、CPU、System RAM 含 swap、每物理盘、每已连接网卡+合计、Context fill 环表+三条进度、Recent requests 9 列+totals、Conversation cache）；每秒并发 fetch `/ext.json` 与 `/metrics`（反代原样转发引擎）两源独立容错；引擎 key 读写官方同键 `localStorage["strata.apikey"]`，401 时页面小输入框补填存回同键；页脚自报账本工具自持页面。`monitor_ext.py` 唯一 py 改动 = 加 `/monitor.css` 与 `/monitor-sprite.svg` 两条静态路由（上线需按切换纪律重启一次窗口，时机主理人定）；`bootstrap.py --check` 必需文件 13→15 项；三套回归扩断言后按当次实际输出全绿。GPU 采样/14 列契约、记账主链、看门狗、切换纪律、`ext.js` shim 未动；官方 `terminal/serve/web/` 未写一字。
- **同日四稿（含用户口径修订）：每卡 PCIe 链路字段（GPU 查询 14→18 列）+ 每卡多色实时线路波形**（对应 `MANIFEST.md` 2.10 节）：`/ext.json` 的 GPU 行新增 `pcie_gen / pcie_width / pcie_gen_max / pcie_width_max` 四个链路字段（621.24 驱动真机实证 rc=0）与每卡吞吐 `pcie_rx_mb / pcie_tx_mb`（该驱动无 `pcie.throughput.*` 查询字段，rc=2 实证；改走 `nvidia-smi dmon -s t` 同 tick 按枚举序配对 uuid）。监视页顶部 PCIe 卡升级为**每 GPU 一条彩色实时波形**，图例每卡一行「卡名 · Gen5 ×8 · 360 MB/s」，另并入引擎侧实测一条；GPU 卡副行加中性 `PCIe Gen5 ×8` 文字。**不做任何退化告警/红标**——用户口径：本机 ×8 就是稳态正常值（7950X 双卡各 8 lane），空闲降代显示 Gen1 也属正常；首版做过的退化徽章机制已全部移除并有回归断言防复活。旧 14 列形态整行丢弃规则保留。生产上线需要 8080 按切换纪律重启一次窗口。
- **生产待办（本包不代做）**：官方页面从 `index.html.orig` 恢复（README 6.1 给了命令）；8080 按切换纪律（先 `switch_proxy.py --check`）重启一次生效。本轮未启动 / 停止 / 重启 / 连接 / 占用任何生产服务端口。

---

## 2026-11-12（startup-example-fix）· 修正 Windows 自启示例 / 终版重打包

对应 `MANIFEST.md` 2.7 节。摘要：

- **修掉一个会静默失败的坑**：`service-examples/Strata ledger watchdog.vbs` 原注释让人「把 VBS 放进启动夹」，但脚本按自身目录找 `ledger_watchdog.py`；复制过去后目录变成启动夹，看门狗根本起不来且不报错。改为 **VBS 留在包目录、启动夹只放快捷方式**（快捷方式启动时脚本解析到的仍是自己的真实路径，所在目录不变）。
- **解释器可指定**：新增 `STRATA_PYTHON` 环境变量覆盖（Python 不在 PATH 时指向 `python.exe` 全路径），不再经额外的命令处理器中转、直接运行解释器；用 `Chr(34)` 拼引号避免转义出错；`--lock-wait 86400` 与纯 ASCII + CRLF 保持不变。
- **文档同步**：`README.md` 第二节表格与说明、第九节第 7 条，`SKILL.md` 第 6 步表格与说明，全部改成「启动夹放快捷方式」并写清原因与 `STRATA_PYTHON`。
- **重打包**：`strata-ledger-proxy-2026-11-12.zip` 覆盖为终版（24 文件）。回滚件即 dist 下现存的 `strata-ledger-proxy-2026-11-12.zip` 与更早的 `strata-ledger-proxy-2026-11-11.zip`（当时另存于 `archive/` 的说法不实，2026-11-16 已更正——该文件从未存在）。
- **未动任何运行主链**：包内 `.py` / 配置模板 / `start.bat` / `start.sh` 一字未改；未启动或停止任何生产进程。

---
## 2026-11-12（watchdog-align）· 看门狗对齐 / 自启接管 / 重打包

对应 `MANIFEST.md` 2.6 节。摘要：

- **生产看门狗对齐**：`usage/ledger_watchdog.py` 新增自包含 `ports_from_config()`（不 `import paths`）、`--port` / `--lock-port` 默认跟随 `config.json`、`launch_ledger()` 的 POSIX 分支加 `start_new_session=True`；`resolve_collector()` 默认路径与 `--lock-wait` 候补锁循环未动。
- **开机自启接管**：两个 Windows 启动夹 VBS 追加 `--lock-wait 86400`，登录副本改为热备候补、旧看门狗退出后零缝隙接管；注释改纯 ASCII、CRLF（清掉 P3-5）。
- **回归自测**：`usage/selftest_watchdog.py` 新增端口解析 / 显式参数优先 / 候补接管用例，原有回归用例逐字保留，按当次实际用例数报出；`bootstrap.py --selftest` 两套回归全绿。
- **文档与工程化**：`bootstrap.py` 加 `sys.path` 兜底（P3-2）；`README.md` 补畸形 `Bearer ` 边界（P3-1）与 VBS 候补说明；`MANIFEST.md` 清掉写死用例数（P3-4）、文件总数口径改 24；新增本记录。
- **重打包**：`strata-ledger-proxy-2026-11-12.zip`（24 文件），保留 11-09 / 11-11 两个旧 ZIP。
- **生产进程状态（如实）**：生产 `8080` 已于 2026-11-12 20:19 切换到 11-11 归因修复版并实证生效；**看门狗磁盘代码已对齐但进程待主理人交接**。本轮只改磁盘文件，未启动 / 停止 / 重启 / 连接 / 占用任何生产服务端口。

---

## 2026-11-12（docs-r2）· 文档层重构

- 新增 `SKILL.md`：宿主 Agent 的部署工序入口（模式判定表、前置自检、必问人类拍板项、编号工序、验收判据、运维与故障、边界与债、每日投递工序）。
- 新增 `CHANGELOG.md`：本文件。
- `README.md`：顶部插入「Agent 部署入口」短小节（指引宿主 Agent 直接按 `SKILL.md` 执行；README 其余内容一字未动）。
- `MANIFEST.md`：文件清单登记两个新文件；改动登记新增 2.5 docs-r2 小节；发行版本修订日期更新为 2026-11-12。

**本次未改任何 `.py` / `.bat` / `.sh` / 配置模板，契约不变量全部未动。**

---

## 2026-11-11（rev）· 按 key 归因修复轮

对应 `MANIFEST.md` 2.4 节。摘要：

- `collector_proxy.py`：新增 `key_identity()`——先 `strip()` 再按 RFC 7235 大小写不敏感剥 `Bearer ` 前缀，`Bearer` / `bearer` / `BEARER` 归一；账本每行新增 `fp` 字段（原始 8 位指纹永久留存，便于事后拆分合并、追查撞码）。
- `selftest_proxy.py`：新增归因用例（大小写归合同 `key`+`fp`、`x-api-key` 记录合法 `fp`、全量账本行 `fp` 格式校验），用例数按当次实际输出报出。
- `bootstrap.py --check`：新增 `key_labels` 纯读取校验（键须 8 位小写 hex、值须非空、同姓名合并仅 warn、空配置 warn）；`lock_port == watchdog_lock_port` 改为不合格。
- `README.md`：第三节补三个坑（裸 key 不带 `Bearer `、空 `key_labels` 看似撞车、同姓名合并不可从历史拆开）；第九节新增「8 位指纹可能撞码、不做自动检测」边界。
- `daily_report.py` / `html_report.py`：已核查未改（按 `key` 分组，`fp` 不影响出表）。
- 回归自测：两套均按当次实际用例数报出且全绿。
- 生产母本同步改磁盘但**未重启任何进程**（磁盘代码已更新 ≠ 进程已生效）。

---

## 2026-11-09（v1）· 首版发行

给另一台机器（代号 5090）替换旧「旁路边读引擎日志」账本链的独立工具包。首发内容：

- **反代逐块流式修复**：响应头立即发出、每个上游数据块到达即 `flush()`（首字节约 0.01 秒）；源母本的 `resp.read()` 整包缓冲会原样复现 502，本包版本已修正。
- **按 key 指纹归人**：SHA-256 前 8 位十六进制指纹映射姓名，配置不存原始 key，`python collector_proxy.py --fp <key>` 算指纹。
- **看门狗**：5 秒巡检、掉了自动补岗、配置热更新、立即补岗标记、脱离会话拉起服务。
- **切换纪律**：`switch_proxy.py` 唯一切换入口，有客户端会话硬拒绝且 `--force` 不覆盖，判忙窗口 5 分钟。
- **两套回归自测**：`selftest_proxy.py`（假上游 + 临时端口）+ `selftest_watchdog.py`，不碰正式服务。
- **三平台启动件**：Windows 启动夹 VBS / Linux systemd（`Restart=always`）/ macOS launchd（`KeepAlive`）。
- **legacy 兼容件**：旧读日志采集器 + 排程（可选，主链不依赖）。
- 交付前修复轮（同日）：路径相对化（`@here`/`@pkg`/`~`）、端口自动跟随（`ports_from_config`）、脱会话子进程（`start_new_session`）、去硬编码、指纹/姓名脱敏、日报与网页报表口径如实化——逐项见 `MANIFEST.md` 2.1–2.3 节。
