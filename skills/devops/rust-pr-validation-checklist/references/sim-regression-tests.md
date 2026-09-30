# 物理 / 仿真类回归测试配方

> 适用于任何「给解算器加一项力/阻尼/约束」的回归测试。核心风险:测试可以**不进入被测代码路径**而依然 pass。

## 1. 必守的三条

1. **断言接触本身,不只是断言结果。** 先断言碰撞确实发生(`depth > 0`、接触回调被触发、法向速度符号翻转),再断言力的效果。只断言效果时,「没碰撞」和「碰撞了但力不够」给出同一个失败。
2. **不要每步重置初速度。** 步进循环里每帧重新 seed 速度,阻尼/摩擦永远衰减不到 0,测试只能写成「速度有变化」这种弱断言 —— 而弱断言恰好是 placebo 测试的温床。
3. **撒销修复后必须 FAIL**,且要确认是**断言失败**而不是编译/运行错误。完整验证见 SKILL.md §3.5 与 §3.4b。

## 2. 「passes without the fix」的两种根因

| 根因 | 症状 | 修法 |
|---|---|---|
| 摆放参数导致零接触 | 撒销修复后测试仍 pass | 收紧初始间隙到明显小于每步位移;断言 `depth > 0` |
| 每步重置初速度 | 只能断言「有变化」 | 只在循环外 seed 一次;断言单调衰减到 0 |

两者可以叠加 —— 同时存在时,测试对修复完全不敏感。

## 3. 加摩擦/阻尼的完整配方(以冲量解算器为例)

**两个改动缺一不可,这是最容易漏的地方:**

### 3.1 必须跑在「提前返回」之前

典型冲量解算器的法向分支长这样:

```rust
let velocity_along_normal = relative_velocity.dot(normal);
if velocity_along_normal > 0.0 { return; }   // ← 会把摩擦整段跳过
```

沿接触面**滑动的物体,法向是分离的**,所以 `velocity_along_normal > 0` 对滑动物体常态成立 —— 那个 guard 会让摩擦永远不被计算。正确做法是把摩擦算在 guard **之前**,guard 只用来短路法向冲量和位置修正:

```rust
let impulse_magnitude = if velocity_along_normal > 0.0 { 0.0 }
                        else { -(1.0 + restitution) * velocity_along_normal / inv_mass_sum };
// ... 摩擦在这里,独立于法向冲量 ...
if velocity_along_normal > 0.0 { return; }
```

### 3.2 夹紧上限不能用速度冲量

Coulomb 夹紧需要的是**法向载荷**。对滑动接触,速度冲量是 0,拿它当夹紧上限会让摩擦静默失效(代码能编译、能过 clippy、测试也能过 —— 如果测试是 placebo):

```rust
// 错:滑动接触下 impulse_magnitude 恒为 0 → 摩擦恒等于 0
let max_friction = friction * impulse_magnitude.abs();

// 对:法向载荷 = 穿透深度导出的位置修正冲量 + 速度冲量
let normal_load = (depth * POSITION_PERCENT / inv_mass_sum).max(0.0)
                + impulse_magnitude.abs();
let max_friction = friction * normal_load;
```

`normal_load` 用穿透深度是**务实近似,不是教科书解法**(物理上法向载荷应来自重力/约束力)。选它是因为它能让物体稳定停稳而不是振荡。接真接触约束求解器时这一项要换掉 —— **在代码里留注释标明**,否则下一个读代码的人会以为它是物理正确的。

### 3.3 切向是维数无关的

`v - n(v·n)` 一个表达式同时覆盖 2D 和 3D,不需要每轴构造切向基。

## 4. 测试断言模板

```rust
// 2D:滑动体在地面上滑行,应单调减速到静止
let mut body = /* 紧贴地面,间隙 0 */;
let before = body.get_velocity().magnitude();
for _ in 0..STEPS { world.step(dt); }   // 只在循环外 seed 一次速度
// 关键:先证明接触发生过
assert!(/* 至少发生过一次 depth > 0 */);
assert!(body.get_velocity().magnitude() < before * 0.1);
```

**已知不对称**:2D 和 3D 解算器可能重检接触的次数不同(2D 在迭代循环内重检,3D 每步只解一次),导致 3D 衰减明显更慢。所以 3D 测试断**单调性 + 净速度损失**,不要断「降到接近 0」—— 否则你会在写一条永远不稳定的测试,而不是在测 bug。
