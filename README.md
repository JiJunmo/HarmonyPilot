# HarmonyPilot

让 AI 操作鸿蒙真机，完成截图、交互与界面验证。

An AI agent skill for HarmonyOS device interaction and UI verification, powered by HDC and UITest.

HarmonyPilot 为支持本地命令执行和图片查看的 AI Agent 提供操作流程与 Python 脚本：观察页面 → 定位控件 → 执行操作 → 再次观察验证。适用于纯血鸿蒙 HarmonyOS 真机或模拟器的开发调试。

## 功能

- 发现设备并明确选择目标，避免多设备时误操作。
- 截图并取回电脑，返回原始图像宽高。
- 导出页面控件树与文本摘要，按文字、组件标识、类型或描述查找、点击和输入，适配纯文本模型。
- 模拟点击、滑动。
- 向已聚焦输入框输入，或指定坐标后输入。
- hilog 缓冲快照、限时日志采集，支持 PID、Tag、级别及正则过滤。
- 以 JSON 返回结果，便于 Agent 或其他程序处理。

## 环境准备

1. 安装 Python 3.8+，脚本仅使用标准库。
2. 安装 DevEco Studio / 对应 SDK，确保可以执行 `hdc`。
3. 手机开启开发者模式及设备支持的调试选项，连接电脑并完成授权。
4. 确认 `hdc list targets` 能列出设备，`hdc -t <设备ID> shell uitest help` 可运行。

HDC 优先从 `--hdc`、`HDC_PATH`、PATH 查找，并兼容 macOS 常见 DevEco Studio SDK 路径。自定义 SDK 可显式指定可执行文件。不同设备和系统版本的 UITest 能力可能不同，以设备帮助为准。

## 安装为 Codex Skill

克隆到个人 Skills 目录，目录名与 Skill 名称保持一致：

```bash
git clone https://github.com/JiJunmo/HarmonyPilot.git "${CODEX_HOME:-$HOME/.codex}/skills/harmony-pilot"
```

如果目标目录已存在，请先检查已有内容。安装后在新对话中调用：

```text
使用 $harmony-pilot，打开阅读，点击书架第一本书并截图。
```

```text
使用 $harmony-pilot，在搜索框输入“三国”，截图确认输入结果，不提交搜索。
```

其他支持本地 Skills 的 Agent 可按其目录约定安装；核心入口为 [SKILL.md](SKILL.md)。Agent 需要具备执行命令、读取文件和查看图片的能力。

## 直接使用脚本

在仓库目录执行。全局参数必须放在子命令之前：

```bash
# 发现设备
python3 scripts/device.py devices

# 替换 DEVICE_ID 为实际设备 ID；同时获取截图和控件树
python3 scripts/device.py --device DEVICE_ID observe --out-dir ./artifacts

# 单独截图或导出控件树
python3 scripts/device.py --device DEVICE_ID screenshot --out-dir ./artifacts
python3 scripts/device.py --device DEVICE_ID layout --out-dir ./artifacts

# 点击与滑动，坐标为原始屏幕像素
python3 scripts/device.py --device DEVICE_ID tap 300 600
python3 scripts/device.py --device DEVICE_ID swipe 500 1500 500 500

# 输入：当前焦点 / 指定坐标
python3 scripts/device.py --device DEVICE_ID text '三国 hello'
python3 scripts/device.py --device DEVICE_ID text '三国 hello' --at 300 600

# 查看设备支持的命令
python3 scripts/device.py --device DEVICE_ID help
```

可选全局参数：`--hdc /path/to/hdc`、`--timeout 30`（每条 HDC 命令的超时秒数）。脚本不自动重试点击或输入。

`observe` 的输出示例：

```json
{
  "device": "DEVICE_ID",
  "screenshot": "/absolute/artifacts/harmony-<unique-id>.png",
  "width": 2240,
  "height": 2440,
  "layout": "/absolute/artifacts/harmony-<unique-id>.json"
}
```

截图与控件树依次采集，并非同一时刻的原子快照。成功取回文件后，脚本尝试删除本次在设备 `/data/local/tmp/` 下生成的临时文件；电脑上的文件保留。

## 定位与验证

优先根据控件树中的 `attributes.text`、`id`、`bounds` 定位；自绘内容缺少节点时使用截图。若原始 W×H 截图在查看工具中缩放为 w×h，按以下公式换回设备坐标：

```text
设备 x = 显示 x × W / w
设备 y = 显示 y × H / h
```

旋转、折叠或窗口变化后重新观察。命令返回成功只表示操作命令执行完成，必须用新截图或控件树确认页面结果。

文本输入底层使用 `uiInput text <内容>` 或 `uiInput inputText X Y <内容>`。当前仅支持非空单行文本，不自动清空原文、不保证追加或替换行为，也不自动提交。中文、特殊符号和 Web 输入框的实际效果需在目标设备验证。脚本会进行设备端 shell 转义；从程序调用时推荐用 `subprocess.run([...])` 参数数组传参，避免调用方 shell 展开文本。

## 验证状态

- 已在 HarmonyOS 真机上完成打开“阅读”、点击书架第一本书并截图的交互演示。
- 封装脚本的截图、控件树读取已通过真机验证。
- 已根据真机帮助确认文本输入语法，并通过中文、空格和 shell 特殊字符的参数转义测试；尚未验证真实输入框中的输入效果。
- hilog 缓冲快照、两秒限时采集及 PID / Tag / 正则组合过滤已通过真机验证；快照超时和非法时长拒绝已通过本地检查。
- 尚未验证 Windows、Linux 及全部 HarmonyOS 版本。

## 常见问题

**HDC 无法访问设备**：检查连接授权、开发者选项和 SDK 的 HDC 版本。Agent 运行环境有沙箱限制时，使用该环境提供的权限申请机制。

**UITest 提示需要启用测试能力**：参考对应版本官方文档，必要时执行以下命令。不要在每次操作前重复设置：

```bash
hdc -t DEVICE_ID shell param set persist.ace.testmode.enabled 1
```

**操作超时**：超时不代表设备没有执行操作，先重新观察再决定是否重试。

## 项目结构

```text
SKILL.md             Agent 工作流程与约束
agents/openai.yaml   Skill 展示信息
scripts/device.py    HDC / UITest 命令封装
```

## 官方参考

- [HarmonyOS UI 测试框架](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/uitest-guidelines)
- [DevEco Studio 真机 UI 测试](https://developer.huawei.com/consumer/cn/doc/HarmonyOS-Guides/ide-hmos-instrument-test)
- [OpenHarmony UITest 使用指导](https://github.com/openharmony/docs/blob/master/zh-cn/application-dev/application-test/uitest-guidelines.md)

本项目是社区工具，与华为官方无隶属关系。

## 日志采集

```bash
# 获取当前缓冲区日志并退出
python3 scripts/device.py --device DEVICE_ID logs --out-dir ./artifacts

# 采集 10 秒，按已确认的应用 PID 和精确级别集合过滤
python3 scripts/device.py --device DEVICE_ID logs --seconds 10 --pid 1234 --levels E,F --out-dir ./artifacts

# Tag / 正则过滤
python3 scripts/device.py --device DEVICE_ID logs --tag MyTag --regex 'error|timeout' --out-dir ./artifacts
```

`--seconds` 默认 0（缓冲快照），最大 60。`--levels` 是精确集合，例如 `E,F`；不是最低级别。PID 需要确认，应用重启后可能改变。过滤参数可以组合。不同系统以 `hdc -t DEVICE_ID shell hilog --help` 为准。

输出包含 `.log` 和 `.stderr.log` 的绝对路径、字节数、采集时长、退出码、结束原因及最多 4 KiB 尾部。默认 `--max-mb 10`，允许 1–100；轮询检测大小，文件可能略超过阈值。`duration` 为正常限时停止，`size_limit` 表示日志不完整，`timeout` 或非零自然退出需要检查诊断。部分 HDC 错误可能输出到日志文件，即使退出码为 0 也应检查内容。

采集可能先输出历史缓冲日志；分析时结合时间、PID、截图，不能把所有日志归因于当前操作。需要边操作边采集时，在宿主后台会话运行限时命令，执行交互后等待其结束。终止本地采集客户端，不修改设备日志配置，不自动清空缓冲、关闭隐私脱敏或开启持久日志任务。真机日志仅保存到本地，不应上传仓库。

## 纯文本模型定位

无需识别截图。`layout` 和 `observe` 额外返回 `ui_text` 文本摘要路径、前 50 个节点以及总数；完整摘要保存为 JSON Lines 格式的 `.txt`。每个节点包含 text、id、type、description、bounds、center、clickable、path 与 actionable。摘要优先保留有文字、标识、描述或可点击的节点，减少容器噪声。

```bash
python3 scripts/device.py --device DEVICE_ID find --text '搜索'
python3 scripts/device.py --device DEVICE_ID find --text '变形记' --contains
python3 scripts/device.py --device DEVICE_ID click --id searchButton
python3 scripts/device.py --device DEVICE_ID click --text '搜索' --type Button
python3 scripts/device.py --device DEVICE_ID fill '变形记' --id searchInput
```

选择器支持 `--text`、`--id`、`--type`、`--description`，多个条件按 AND 匹配，默认精确相等；`--contains` 对所有给出的条件使用包含匹配。`find` 返回最多 50 个候选、总数及截断标记。`click` / `fill` 每次读取最新控件树，仅在匹配恰好一个可见、启用且有有效边界的节点时注入操作；零个或多个匹配时返回候选及非零退出码，不操作。父级隐藏或禁用的节点也排除。

`actionable` 表示节点可作为坐标目标，并不保证该点未被遮挡，也不保证节点声明 clickable。文字节点可能借助父控件响应点击。重复文字可增加 ID 或类型条件；不要默认选第一个。`path` 用于理解层级，不是跨页面稳定标识。操作后重新读取控件树验证结果；fill 不自动清空或提交。

Canvas、自绘与未暴露无障碍节点的内容可能无法定位，离屏控件需滚动后重新查找。对于自己的 ArkUI 应用，给关键交互组件添加稳定 `.id()` 和无障碍描述可提高可靠性。纯文本模式不推断节点树之外的视觉内容。


运行选择器测试：`python3 -m unittest discover -s tests -v`。已验证精确/包含匹配、组合条件、隐藏/禁用节点排除和歧义匹配不注入操作；真机验证了文本摘要导出及无匹配查询。
