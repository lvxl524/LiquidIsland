#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""repack.py — 把一份 Liquid Island deb 确定性重打包为「无根 / 隐根」两个变体。

做了什么
  1. 双架构 (arm64+arm64e) 二进制 → 纯 arm64 thin，并修正 LC_FUNCTION_STARTS
     （去掉指针认证 fixup，修复 Preferences 加载设置面板时的 SIGBUS）
  2. Info.plist 补 NSPrincipalClass
  3. Root.plist / 入口 plist 简体中文化，并去掉重复项
  4. data.tar.gz 重打包（Sileo/Zebra 兼容）
  5. 产出：rootless（Version）与 roothide（Version+hidden，Depends 仅 firmware）

用法
  python tools/repack.py --in LiquidIsland_1.5.0.deb --out-dir out --version 1.6.0

仅依赖 Python 3 标准库；Windows / macOS / Linux 均可运行。
"""
import argparse, gzip, io, lzma, os, plistlib, struct, tarfile

ZH = {
    'Liquid Island': 'Liquid Island 灵动岛',
    'Enabled': '启用',
    'Hide Black Background': '隐藏黑色背景',
    'Expanded Fade': '展开时淡出',
    'Glass When Idle': '空闲时玻璃化',
    'Specular Highlight': '高光反射',
    'Fade Length (left = none, right = full black)': '淡出长度（最左 = 无淡出，最右 = 全黑）',
    'Corner Radius (0 = Auto)': '圆角半径（0 = 自动）',
    'Background Removal Methods (try any combination)': '背景去除方案（可任意组合尝试）',
    'Method A: Hide System Views': '方案 A：隐藏系统视图',
    'Method B: Force Alpha 0 on All Black Views': '方案 B：黑色视图透明度强制置 0',
    'Method C: Zero-Size Black Plate Frame': '方案 C：黑色底板尺寸置零',
    'Method D: Remove Plate From Superview': '方案 D：从父视图移除底板',
    'Background Removal Methods (test together)': '背景去除方案（可叠加测试）',
    'Method 1: Hide System Views': '方案 1：隐藏系统视图',
    'Method 2: Clear Aperture Window': '方案 2：清空 Aperture 窗口',
    'Glass Opacity (lower = less visible glass)': '玻璃不透明度（越低越透）',
    'Debug': '调试',
    'Debug Glass (oversized)': '调试玻璃（超大尺寸）',
}
FOOTER_ZH = '玻璃观感（折射、模糊、着色等）可在 Liquid Ass 设置的 Pill HUD 中自定义。'
PANEL_TITLE = 'Liquid Island 灵动岛'
BUNDLE = 'var/jb/Library/PreferenceBundles/LiquidIslandPrefs.bundle'
DYLIB = 'var/jb/Library/MobileSubstrate/DynamicLibraries/LiquidIsland.dylib'


# ---------------------------------------------------------------- deb / ar
def ar_split(data):
    assert data[:8] == b'!<arch>\n', '不是 ar 归档（deb）'
    off, mem = 8, {}
    while off + 60 <= len(data):
        name = data[off:off+16].decode('ascii', 'replace').strip()
        size = int(data[off+48:off+58].decode('ascii').strip())
        mem[name] = data[off+60:off+60+size]
        off += 60 + size + (size % 2)
    return mem


def ar_member(name, data):
    hdr = (name.ljust(16) + '0'.ljust(12) + '0'.ljust(6) + '0'.ljust(6)
           + '100644'.ljust(8) + str(len(data)).ljust(10) + '`\n').encode()
    return hdr + data + (b'\n' if len(data) % 2 else b'')


def payload(mem):
    for key, deco in (('data.tar.lzma', lzma.decompress), ('data.tar.xz', lzma.decompress),
                      ('data.tar.gz', gzip.decompress)):
        if key in mem:
            raw = deco(mem[key])
            return tarfile.open(fileobj=io.BytesIO(raw))
    raise SystemExit('data.tar.* 不存在')


# ---------------------------------------------------------------- mach-o
def thin_arm64(blob):
    """fat → thin arm64（slice0），并修正 LC_FUNCTION_STARTS 的 LC_REQ_DYLD。"""
    if struct.unpack_from('>I', blob, 0)[0] != 0xcafebabe:
        return blob, ['（已是 thin，跳过）']
    nfat = struct.unpack_from('>I', blob, 4)[0]
    ct, cs, of, sz, _align = struct.unpack_from('>iiIII', blob, 8)
    assert ct == 0x0100000c and (cs & 0xffffff) == 0, 'slice0 不是纯 arm64'
    sl = bytearray(blob[of:of+sz])
    notes = [f'取 arm64 slice @ {of:#x} ({sz:#x} bytes)']
    ncmds = struct.unpack_from('<I', sl, 16)[0]
    o = 32
    for _ in range(ncmds):
        cmd, cmdsize = struct.unpack_from('<II', sl, o)
        if cmd == 0x26:                       # LC_FUNCTION_STARTS 少了 LC_REQ_DYLD
            struct.pack_into('<I', sl, o, 0x80000026)
            notes.append('LC_FUNCTION_STARTS: 0x26 -> 0x80000026')
        o += cmdsize
    return bytes(sl), notes


# ---------------------------------------------------------------- plist
def localize(root_raw, entry_raws):
    root = plistlib.loads(root_raw)
    items, dropped, seen = [], [], set()
    for it in root.get('items', []):
        key, lab = it.get('key'), it.get('label')
        ident = ('key', key) if key else (('label', lab) if it.get('cell') == 'PSGroupCell' and lab else None)
        if ident:
            if ident in seen:
                dropped.append(str(ident)); continue
            seen.add(ident)
        if lab in ZH:
            it['label'] = ZH[lab]
        if 'footerText' in it:
            it['footerText'] = FOOTER_ZH
        items.append(it)
    root['items'] = items
    root['title'] = PANEL_TITLE
    print(f'  Root.plist: {len(items) + len(dropped)} -> {len(items)} 项（去重 + 汉化）')
    for d in dropped:
        print('    - 重复项:', d)
    out = {'Root.plist': plistlib.dumps(root, fmt=plistlib.FMT_BINARY)}
    for name, raw in entry_raws.items():
        d = plistlib.loads(raw)
        if isinstance(d, dict) and 'entry' in d and 'label' in d['entry']:
            d['entry']['label'] = PANEL_TITLE
        out[name] = plistlib.dumps(d, fmt=plistlib.FMT_BINARY)
    return out


# ---------------------------------------------------------------- build
def build_tar(tf, repl):
    buf = io.BytesIO()
    t = tarfile.open(fileobj=buf, mode='w', format=tarfile.PAX_FORMAT)
    for m in tf.getmembers():
        fm = tarfile.TarInfo(m.name)
        fm.mode, fm.uid, fm.gid = m.mode, m.uid, m.gid
        fm.mtime, fm.uname, fm.gname = m.mtime, m.uname, m.gname
        if m.isdir():
            fm.type = tarfile.DIRTYPE; t.addfile(fm); continue
        data = repl.get(m.name)
        if data is None:
            data = tf.extractfile(m).read()
        fm.size = len(data)
        t.addfile(fm, io.BytesIO(data))
    t.close()
    return buf.getvalue()


def make_deb(data_tar_bytes, version, depends, maintainer, out_path):
    control = (f'Package: com.mekabrine.liquidisland\nName: Liquid Island\nVersion: {version}\n'
               'Architecture: iphoneos-arm64\n'
               'Description: Liquid glass for active and expanded Dynamic Island states.\n'
               '  Repack: arm64-only (no ptrauth fixups) + zh-CN preference panel.\n'
               f'Maintainer: {maintainer}\nAuthor: Meka (original) / {maintainer} (repack)\n'
               f'Section: Tweaks\nDepends: {depends}\n')
    kb = max(1, (len(data_tar_bytes) + 1023) // 1024)
    control += f'Installed-Size: {kb}\n'
    cbuf = io.BytesIO()
    t = tarfile.open(fileobj=cbuf, mode='w', format=tarfile.PAX_FORMAT)
    d = tarfile.TarInfo('./control'); d.mode = 0o644; d.uid = 501; d.gid = 0; d.mtime = 0
    d.size = len(control.encode()); t.addfile(d, io.BytesIO(control.encode())); t.close()
    out = (b'!<arch>\n' + ar_member('debian-binary', b'2.0\n')
           + ar_member('control.tar.gz', gzip.compress(cbuf.getvalue(), 9, mtime=0))
           + ar_member('data.tar.gz', gzip.compress(data_tar_bytes, 9, mtime=0)))
    open(out_path, 'wb').write(out)
    return out_path, len(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='src', required=True, help='上游 Liquid Island deb')
    ap.add_argument('--out-dir', default='out')
    ap.add_argument('--version', default='1.6.0')
    ap.add_argument('--maintainer', default='lvxl524')
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)

    mem = ar_split(open(a.src, 'rb').read())
    tf = payload(mem)

    prefs_key = f'{BUNDLE}/LiquidIslandPrefs'
    info_key = f'{BUNDLE}/Info.plist'
    root_key = f'{BUNDLE}/Root.plist'
    entry_key = f'{BUNDLE}/entry.plist'
    pl_key = 'var/jb/Library/PreferenceLoader/Preferences/LiquidIsland.plist'

    newbin, notes = thin_arm64(tf.extractfile(prefs_key).read())
    dylib, dnotes = thin_arm64(tf.extractfile(DYLIB).read())
    for n in notes + dnotes:
        print('  ·', n)

    info = plistlib.loads(tf.extractfile(info_key).read())
    info['NSPrincipalClass'] = 'LIRootListController'

    loc = localize(tf.extractfile(root_key).read(),
                   {entry_key: tf.extractfile(entry_key).read(),
                    pl_key: tf.extractfile(pl_key).read()})

    repl = {prefs_key: newbin, DYLIB: dylib,
            info_key: plistlib.dumps(info, fmt=plistlib.FMT_BINARY),
            root_key: loc['Root.plist'], entry_key: loc[entry_key], pl_key: loc[pl_key]}

    data = build_tar(tf, repl)
    for scheme, ver, dep in (('rootless', a.version,
                              'mobilesubstrate, preferenceloader, firmware (>= 16.0)'),
                             ('roothide', a.version + '+hidden', 'firmware (>= 16.0)')):
        base = ver.split('+')[0]
        fn = os.path.join(a.out_dir, f'com.mekabrine.liquidisland_{base}_{scheme}_iphoneos-arm64.deb')
        p, n = make_deb(data, ver, dep, a.maintainer, fn)
        print(f'  ✓ {os.path.basename(p)}  {n} bytes  (Version={ver}, Depends={dep})')
    print('完成。')


if __name__ == '__main__':
    main()
