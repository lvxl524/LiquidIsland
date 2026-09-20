# Liquid Island（灵动岛液态玻璃）

> 灵动岛「液态玻璃」效果插件。
> 本仓库是 **Meka 原作 Liquid Island 1.5.0** 的重打包：修复「点进设置就闪退」、完整汉化设置面板，并按越狱形态拆成 **隐根（RootHide）** 与 **无根（rootless）** 两个包。
> **不包含任何上游新版本**，功能与原作 1.5.0 完全一致。

## 下载

到 [Releases](https://github.com/lvxl524/LiquidIsland/releases) 按你的越狱选一个装：

| 文件 | 适用 | Depends | 说明 |
|---|---|---|---|
| `com.mekabrine.liquidisland_1.6.0_roothide_iphoneos-arm64.deb` | **隐根**（RootHide） | `firmware (>= 16.0)` | **RootHide 原生形态**：根相对路径 + `iphoneos-arm64e` + 二进制内 0 处 `/var/jb`，**装上即用，无需再做 rootless→roothide 转换** |
| `com.mekabrine.liquidisland_1.6.0_rootless_iphoneos-arm64.deb` | **无根**（Dopamine / palera1n rootless） | `mobilesubstrate, preferenceloader, firmware (>= 16.0)` | 标准 rootless 包 |

包 ID 保持 `com.mekabrine.liquidisland`，可直接覆盖已装的 1.5.0。安装后建议注销（respring）。

## 1.6.0 变更

### ① 修复「点进设置就闪退」（SIGBUS）

- 崩溃点：`Preferences` 加载 `LiquidIslandPrefs` 主类时，`libobjc` 的 `readClass` 触发 `EXC_BAD_ACCESS (SIGBUS)`，异常码 `0x105`（`EXC_ARM_PAC_FAIL`）。
- 根因：原包是 **arm64 + arm64e** 双架构，其 **arm64e slice** 的 `class_ro_t::baseMethods` 等指针带**指针认证（PAC）**，而该二进制并非标准工具链产物（`LC_FUNCTION_STARTS` 丢失 `LC_REQ_DYLD`、`__TEXT` 节区异常右对齐），PAC 订正不可靠 → 未认证的签名指针被当普通地址用 → 非规范地址 → 闪退。
- 修法：**改为纯 arm64**。arm64 slice 使用 `DYLD_CHAINED_PTR_64_OFFSET`，**指针认证 fixup 为 0 条**，这类崩溃从根上消失；arm64 slice 在 arm64e 进程照常加载。
- 顺带：`LC_FUNCTION_STARTS` 修正为 `0x80000026`，补上 `NSPrincipalClass`。
- 副作用：体积减半（`LiquidIslandPrefs` 165,920 → 67,616 B，`LiquidIsland.dylib` 238,016 → 106,944 B）。

### ② 设置面板完整汉化

- 入口与面板标题：**Liquid Island 灵动岛**
- 全部开关 / 分组 / 滑块说明汉化
- 去掉原包 `Root.plist` 的重复项（`CornerRadius` 出现两次、两个分组重复），25 → 22 项

### ③ 打包修正

- `data.tar.gz` 取代原来的 `data.tar.lzma`（Sileo / Zebra 兼容）
- 隐根包 `Depends` 只留 `firmware (>= 16.0)`，任何 rootless 环境都能装

### ④ 隐根包改为 RootHide 原生形态（v1.6.0 追加修正）

初版隐根包只是「改了 `Depends` 的 rootless 包」，装到 RootHide 上仍需手动转换。对照本账号 `SplitJump` 1.5.0 的两个官方变体逐字节比对后，已改为真正的原生形态：

| | rootless | **roothide 原生** |
|---|---|---|
| data 路径 | `./var/jb/Library/…` | **`./Library/…`**（RootHide 的 dpkg 把 `/` 映射进 jbroot） |
| Architecture | `iphoneos-arm64` | **`iphoneos-arm64e`** |
| 二进制内 `/var/jb` | 保留（rootless 语义正确） | **0 处**：install name 改为 `/Library/…`、`/var/jb` rpath 改为 `/Library/…` 与 `/usr/lib` |
| 代码签名 | — | 改写 `__TEXT` 后按 CodeDirectory 口径**整包重签**（`hashType=2` SHA-256，逐页哈希全部匹配） |

> 原包的代码签名在 arm64 slice 第 0 页本就失配（roothide 补丁改过 load command 未重签），本次重签后两个二进制均 100% 页匹配。

## 设置项（汉化对照）

| 原文 | 汉化 |
|---|---|
| Enabled | 启用 |
| Hide Black Background | 隐藏黑色背景 |
| Expanded Fade | 展开时淡出 |
| Glass When Idle | 空闲时玻璃化 |
| Specular Highlight | 高光反射 |
| Fade Length | 淡出长度 |
| Corner Radius | 圆角半径 |
| Background Removal Methods | 背景去除方案（A–D / 1–2） |
| Glass Opacity | 玻璃不透明度 |
| Debug Glass | 调试玻璃 |

## 复现构建

本仓库不含上游源码（上游只发布了二进制 deb），`tools/repack.py` 用于从任意一份
Liquid Island deb **确定性**地重打包出上述两个变体（含汉化、架构修正与隐根形态转换）：

```bash
python tools/repack.py --in LiquidIsland_1.5.0.deb --out-dir out --version 1.6.0
```

仅依赖 Python 3 标准库，Windows / macOS / Linux 均可运行。

## 归属

- 原作：**Meka**（Liquid Island 1.5.0）
- 本仓库：崩溃修复、汉化、重打包（lvxl524），未改动任何功能逻辑
