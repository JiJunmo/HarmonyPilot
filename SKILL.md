---
name: harmony-pilot
description: 使用 HDC 与 UITest 调试纯血鸿蒙 HarmonyOS 真机或模拟器，截图、读取控件树、点击、滑动和文本输入、hilog 日志采集并验证页面变化。用于已连接鸿蒙设备的交互验证，不用于 Android ADB 或浏览器自动化。
---

# HarmonyPilot

使用 `scripts/device.py`，依赖 Python 3 和 HDC。脚本不重试输入操作，输出 JSON。

## 工作流程

1. 执行 `python3 <skill目录>/scripts/device.py devices`。明确选择设备，后续每次传 `--device <ID>`。多台设备而用户未指定时询问，不默认选第一台。
2. 执行 `... --device <ID> observe --out-dir <绝对目录>`，用图片查看工具实际查看返回的 PNG，并读取 JSON 控件树。
3. 根据 text、id 和 bounds 定位目标，点击原始屏幕坐标中的控件中心。自绘内容缺少节点时根据图像定位。
4. 每个有意义的交互后重新 observe，验证页面变化。等待页面稳定；连续两次相同操作无进展时停止盲目重试并报告现状。
5. 最终用绝对路径 Markdown 图片展示截图，说明实际结果。命令成功不等于页面符合预期。

## 命令

全局参数放在子命令前：

```bash
python3 <skill目录>/scripts/device.py devices
python3 <skill目录>/scripts/device.py --device <ID> observe --out-dir /absolute/artifacts
python3 <skill目录>/scripts/device.py --device <ID> screenshot --out-dir /absolute/artifacts
python3 <skill目录>/scripts/device.py --device <ID> layout --out-dir /absolute/artifacts
python3 <skill目录>/scripts/device.py --device <ID> tap 300 600
python3 <skill目录>/scripts/device.py --device <ID> swipe 500 1500 500 500
python3 <skill目录>/scripts/device.py --device <ID> text "三国 hello"
python3 <skill目录>/scripts/device.py --device <ID> text "三国 hello" --at 300 600
python3 <skill目录>/scripts/device.py --device <ID> help
```

observe 返回截图路径、原始宽高、控件树文件路径。两者依次采集，并非原子快照；动画或页面改变时重新观察。控件树较大时用 Python 遍历 attributes 的 text/id/bounds，而非输出整个文件。

## 文本输入

`text <内容>` 向已聚焦输入框输入，底层使用 `uitest uiInput text`。`text <内容> --at X Y` 使用 `uitest uiInput inputText X Y <内容>` 定位输入。先观察确认目标，再输入；输入后 observe，检查控件 text 或截图中的实际内容。不要假定追加或替换行为，也不自动清空原文或提交表单。中文、符号和 Web 输入框需以实际验证结果为准；命令成功不等于输入成功。当前脚本仅接收非空单行文本，拒绝控制字符。

注意：已验证的真机帮助确认 inputText 需要 X、Y、内容三个参数；不要使用缺少坐标的 inputText 命令。脚本处理设备端 shell 转义；调用脚本时仍应安全传参，包含美元符号、反引号等内容时优先使用 subprocess 参数数组。

## 日志采集

```bash
python3 <skill目录>/scripts/device.py --device <ID> logs --out-dir /absolute/artifacts
python3 <skill目录>/scripts/device.py --device <ID> logs --seconds 10 --pid 1234 --levels E,F --out-dir /absolute/artifacts
python3 <skill目录>/scripts/device.py --device <ID> logs --tag MyTag --regex 'error|timeout' --out-dir /absolute/artifacts
```

默认用 hilog -x 导出已有缓冲区；--seconds 1..60 限时采集，可能包含采集前缓冲日志。--levels 是精确级别集合，不是最低级别。--pid 使用确认过的实际 PID；重启应用后重新确认，不猜包名到 PID 的映射。输出 log、stderr 文件路径、有限尾部、退出原因及退出码。优先按目标 PID/Tag 过滤；只读相关片段，避免把全量日志灌入上下文。

需要关联操作时，通过宿主后台命令会话启动限时采集，确认启动后执行 UI 操作，最后等待采集结束并分析日志与截图。时间窗口包含设备缓冲日志，不能把每条日志都归因于该操作。--max-mb 默认 10，轮询达到阈值后停止，文件可能略超阈值。duration 是正常限时结束；size_limit 表示采集被截断；timeout/非零自然退出需检查 stderr 和日志中的 HDC/hilog 诊断。空文件不证明应用没有问题。未找到错误也不等于功能正常。

不要自动清空日志缓冲、关闭隐私脱敏、修改日志级别或开启持久采集。日志可能含个人信息，不将真机日志或截图提交到仓库。

## 关键约束

- 坐标使用原始像素。若 W×H 图片被显示为 w×h，换算 `x=X*W/w, y=Y*H/h`。折叠、旋转、窗口变化后重新观察。
- 用户已要求打开应用、点击和截图时，直接完成。Skill 不扩大用户授权范围。
- HDC 受沙箱限制时按宿主权限机制升级命令，不不断启动沙箱内 HDC。脚本超时不代表设备动作未执行，重新观察后再决定是否重试。
- HDC 从 `--hdc`、`HDC_PATH`、PATH、macOS 常见 DevEco SDK 路径定位。
- UITest 出错先读设备 help。明确需要开启测试能力时，说明原因并执行 `hdc -t <ID> shell param set persist.ace.testmode.enabled 1`，不要每次重设。
- 不默认解锁、安装或抓取所有日志。启动应用可点击桌面图标，或确认实际包名和 Ability 后启动，不猜包名。
- 固定回归用例可放在项目 ohosTest，使用 @kit.TestKit 的 Driver、ON 和断言。

## 官方参考

需要额外输入、按键或版本适配时，查设备帮助及对应 SDK 文档：
- https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/uitest-guidelines
- https://developer.huawei.com/consumer/cn/doc/HarmonyOS-Guides/ide-hmos-instrument-test
- https://github.com/openharmony/docs/blob/master/zh-cn/application-dev/application-test/uitest-guidelines.md
