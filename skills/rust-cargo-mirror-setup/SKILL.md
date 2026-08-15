---
name: rust-cargo-mirror-setup
description: 配置 Rust 开发环境 + 国内高速 cargo 镜像源(cargo 1.97 sparse 协议兼容),安装 cargo install 工具
category: devops
---

# Rust 开发环境 + 国内 Cargo 镜像源配置

## 触发场景
- 在中国大陆服务器上配置 Rust 开发环境
- 使用 `cargo install` 安装工具但下载/更新极慢或失败
- 遇到 cargo 1.97 的 source-protocol check 报错
- 用户要求换源到国内 cargo 镜像

## 核心方案:cargo 1.97 + sparse 协议 + rsproxy 镜像

**关键发现**:cargo 1.97 默认启用 source-protocol check,旧的 mirror 配置方式(无 `sparse+` 协议)会报 `non-remote-registry source for registry 'xxx'` 错误。

**正确配置** `/root/.cargo/config.toml`:
```toml
[source.crates-io]
replace-with = "rsproxy-sparse"

[source.rsproxy-sparse]
registry = "sparse+https://rsproxy.cn/index/"

[registries.rsproxy-sparse]
index = "sparse+https://rsproxy.cn/index/"
```

## 完整步骤

### 1. 一键安装 Rust(非交互 root 环境)
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable --profile minimal
source $HOME/.cargo/env
```

### 2. 配置国内镜像(三选一,按速度)
| 优先级 | 镜像 | index URL |
|--------|------|-----------|
| 🥇 | 字节跳动 rsproxy | `sparse+https://rsproxy.cn/index/` |
| 🥈 | 中科大 ustc | `sparse+https://mirrors.ustc.edu.cn/crates.io-index/` |
| 🥉 | 清华 tuna | `sparse+https://mirrors.tuna.tsinghua.edu.cn/crates.io-index/` |

写入 `~/.cargo/config.toml`(参考上面的正确格式)。

### 3. 安装 cargo 工具
```bash
# 全局安装到 /root/.cargo/bin/
cargo install <crate-name>

# 验证
ls /root/.cargo/bin/
```

### 4. 持久化 PATH(已加到 ~/.bashrc 和 ~/.profile)
```bash
echo 'source $HOME/.cargo/env' >> ~/.bashrc
echo 'source $HOME/.cargo/env' >> ~/.profile
```

## 常见坑(必看)

### ❌ 坑 1: cargo 1.97 source-protocol 报错
```
error: non-remote-registry source for registry 'rsproxy'
```
**原因**:1.97 默认检查 source-protocol,镜像源必须用 `sparse+` 协议,且 `[registries.xxx]` 段必须显式声明 `index` URL。

### ❌ 坑 2: sparse 协议未启用
```bash
# 确认 sparse 协议
cargo --version  # 1.68+ 默认启用
# 或手动设置
export CARGO_REGISTRIES_CRATES_IO_PROTOCOL=sparse
```

### ❌ 坑 3: 镜像源地址写错
- `rsproxy.cn/index/` 末尾**必须**有斜杠
- 不要用 git 协议(`https://` 前不要 `git+`),1.97 默认 sparse

### ❌ 坑 4: 安装路径权限
非 root 用户安装时,`~/.cargo/bin` 需要在 PATH 中,否则 `cargo install` 成功但命令找不到。

## 验证

```bash
# 1. Rust 工具链
rustc --version
cargo --version

# 2. 镜像源生效
cargo search serde --limit 1   # 应秒回
cat ~/.cargo/config.toml

# 3. 安装的工具
ls ~/.cargo/bin/
hyperlane --version   # 类 hyper 框架
euv --help            # euv 类工具
```

## 实际验证结果
- **rustc/cargo**: 1.97.1
- **hyperlane-cli**: v0.1.25 安装成功,`/root/.cargo/bin/hyperlane`
- **euv-cli**: v0.13.3 安装成功,`/root/.cargo/bin/euv`
- **rsproxy sparse 实测速度**:秒级响应(对比 crates.io 直连几 KB/s)

## 相关工具
- `hyperlane`: 跨平台 Web 框架 CLI(`--version` 可用)
- `euv`: 子命令模式工具,`--version` 不可用,需用 `--help` 查看子命令
