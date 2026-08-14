# 3. 架构设计原则

## 3.1 SOLID 原则

优先遵循 **SOLID** 设计原则:

- **S** - 单一职责(Single Responsibility Principle)
- **O** - 开闭原则(Open/Closed Principle)
- **L** - 里氏替换(Liskov Substitution Principle)
- **I** - 接口隔离(Interface Segregation Principle)
- **D** - 依赖倒置(Dependency Inversion Principle)

## 3.2 领域驱动设计(DDD)

使用 **领域驱动设计(DDD)** 组织模块:

- 分离核心域(domain)、应用服务(application)、基础设施(infrastructure)、接口适配器(adapter)

## 3.3 抽象与解耦

- 高层次抽象通过 `trait` 实现,解耦具体实现。
- **共享基础类型** 模式下,下游 crate 直接 `pub use 上游::*;` 把上游全部 re-export 出去,方便用户单点导入。

## 3.4 blanket impl 位置

trait 的 **blanket impl** 放在 `impl.rs` 顶部(即 `impl<T> SomeTrait for T where T: Bound {}` 这种"为所有满足约束的类型实现 trait"的 impl),优先于具体类型的 impl。
