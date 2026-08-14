# 版本号匹配

## Cargo.toml vs Cargo.lock

- `Cargo.toml` 中的版本约束必须与实际查阅的 docs.rs 版本一致;记录并说明使用的是精确版本、兼容范围还是 workspace 继承版本。
- 注意 Cargo 的语义版本解析:`"1.2.3"` 通常表示兼容范围,而不是严格锁定到 `1.2.3`;需要严格固定时使用 `=1.2.3`,但先遵循项目既有约定。
- `Cargo.lock` 中的解析版本可能与 `Cargo.toml` 声明不同。**以 `Cargo.lock` 的实际版本和 docs.rs 对应版本核对最终构建结果**。

## docs.rs latest 的陷阱

- docs.rs 的 `latest` 可能已经超出项目使用版本。
- 旧版本 API、feature 或示例发生变化时,**必须**切换到匹配的版本页面(`https://docs.rs/<crate>/<version>/`)。
- 若 docs.rs 没有目标版本或构建失败,**明确说明无法完成官方文档核验**,再查 crates.io、仓库源码或发布包;**不得伪造已核验结论**。

## 决策树

```
1. 用户提到的 crate → 解析出实际导入名(连字符→下划线)
2. 查 Cargo.toml 看项目声明的版本约束
3. 查 Cargo.lock 看实际解析到的版本
4. 打开 https://docs.rs/<crate>/<lock-version>/ 核 API
   ├─ 该版本存在且有完整文档 → 用这版
   ├─ 该版本不存在 / 构建失败 → 降级到次新 stable,记录差异
   └─ 完全无法核验 → 拒绝伪造,明确告知用户
```
