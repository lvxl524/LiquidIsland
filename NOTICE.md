# NOTICE / 归属与说明

**上游作品**

- 名称：Liquid Island（灵动岛液态玻璃）
- 作者：**Meka**（`com.mekabrine.liquidisland`）
- 版本：1.5.0（本仓库所基于的唯一上游版本，仅有二进制 deb 发布）

**本仓库的改动**

- 修复 `Preferences` 加载设置面板时的 `SIGBUS` 崩溃（二进制改为纯 arm64，去除指针认证 fixup）
- 设置面板简体中文化
- 按 RootHide（隐根）/ rootless（无根）拆分为两个包，`data.tar.gz` 重打包
- 未改动任何功能逻辑，未新增任何 hook 点

**声明**

- 本仓库不包含上游源码（上游未公开），也不声称拥有上游作品的任何权利。
- 若原作者要求下架，请提 issue，会立即处理。
- 仅供学习与个人使用，请支持原作者。
