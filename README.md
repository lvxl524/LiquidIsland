# Liquid Island（灵动岛液态玻璃）

> 灵动岛「液态玻璃」效果插件。
> 本仓库是 **Meka 原作 Liquid Island 1.5.0** 的重打包：修复「点进设置就闪退」、完整汉化设置面板，并按越狱形态拆成 **隐根（RootHide）** 与 **无根（rootless）** 两个包。
> **不包含任何上游新版本**，功能与原作 1.5.0 完全一致。

## 下载

到 [Releases](https://github.com/lvxl524/LiquidIsland/releases) 按你的越狱选一个装：

| 文件 | 适用 | Depends |
|---|---|---|
| `…_1.6.0_roothide_iphoneos-arm64.deb` | **隐根**（RootHide） | `firmware (>= 16.0)` |
| `…_1.6.0_rootless_iphoneos-arm64.deb` | **无根**（Dopamine / palera1n rootless） | `mobilesubstrate, preferenceloader, firmware (>= 16.0)` |

两个包都是 **arm64 + arm64e 双架构**。`Preferences` 是 arm64e 进程，dyld 会拒绝纯 arm64 的 bundle（`have 'arm64', need 'arm64e'`），所以不能只留 arm64。包 ID 保持 `com.mekabrine.liquidisland`，可直接覆盖已装的 1.5.0，装完建议注销。

## 1.6.0 变更

### ① 修复「点进设置就闪退」（SIGBUS / `EXC_ARM_PAC_FAIL`）

崩溃现场（iPhone 15 Pro Max / iOS 17.2.1）：`Preferences` 加载 `LiquidIslandPrefs` 时，`libobjc readClass` 内 `EXC_BAD_ACCESS (SIGBUS)`，异常码 `0x105`。

**根因**：上游二进制被安装期补丁改写过 load command（install name、rpath）却**没有重新签名**——arm64 slice 的 CodeDirectory 第 0 页哈希失配；同时它的 arm64e slice 用 `LC_DYLD_CHAINED_FIXUPS`（指针认证 fixup）声明重定位，而 RootHide 的安装期补丁只按 `LC_DYLD_INFO` 形态处理。结果 arm64e slice 的指针认证 fixup 没被正确套用，`class_ro_t::baseMethods` 这类 PAC 指针带着签名被当普通地址解引用 → 非规范地址 → `readClass` 崩。

**修法**（三条一起做）：

1. **arm64e slice 的重定位形态改为 `LC_DYLD_INFO`** —— 与设备上能正常工作的同工具链产物（`SplitJumpPrefs`）完全同构：`rebase=0/0`，`bind` 流用 `THREADED_BIND`（`0xD0 <表大小>` → 逐符号 `SET_SYMBOL_TRAILING_FLAGS_IMM` + `DO_BIND` → `SET_SEGMENT_AND_OFFSET_ULEB` + `THREADED_BIND 0x01` → `DONE`）。数据区里的 ARM64E 链式编码**原样保留**，由 dyld 沿链套用。
2. **补齐/修正 load command**：`LC_FUNCTION_STARTS` 恢复 `LC_REQ_DYLD`（上游写成 `0x26`）；`Info.plist` 补 `NSPrincipalClass`。
3. **两个 slice 全部重签**：按 CodeDirectory 口径逐页重算哈希，arm64 与 arm64e 各 17/17、26/26 页全部匹配（上游原本第 0 页就是失配的）。

### ② 设置面板完整汉化

入口与面板标题「Liquid Island 灵动岛」，全部开关/分组/滑块中文化；并去掉上游 `Root.plist` 的重复项（`CornerRadius` 两次、两个分组重复），25 → 22 项。

### ③ 打包修正

- `data.tar.gz` 取代上游 `data.tar.lzma`（Sileo / Zebra 兼容）
- 隐根包 `Depends` 只留 `firmware (>= 16.0)`，任何 rootless 环境都能装

### ④ 隐根包为 RootHide 原生形态

对照本账号 `SplitJump` 1.5.0 的 rootless / roothide 两个官方变体逐字节比对得出的差异，全部套上：

| | rootless | **roothide 原生** |
|---|---|---|
| data 路径 | `./var/jb/Library/…` | **`./Library/…`**（RootHide 的 dpkg 把 `/` 映射进 jbroot） |
| Architecture | `iphoneos-arm64` | **`iphoneos-arm64e`** |
| 二进制内 `/var/jb` | 保留 | **0 处**（install name / rpath 原位改写为根相对路径） |

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

本仓库不含上游源码（上游只发了二进制 deb），`tools/repack.py` 从任意一份 Liquid Island deb 确定性地重打包出上述两个变体（双架构、汉化、架构与签名修正、隐根形态转换）：

```bash
python tools/repack.py --in LiquidIsland_1.5.0.deb --out-dir out --version 1.6.0
```

仅依赖 Python 3 标准库，Windows / macOS / Linux 均可运行。

## 归属

- 原作：**Meka**（Liquid Island 1.5.0）
- 本仓库：崩溃修复、汉化、重打包（lvxl524），未改动任何功能逻辑
