# 子文件模板(struct.rs / impl.rs / fn.rs / etc.)

> **第一行** 必须是 `use super::*;`
> (const.rs 因为只放顶层常量,惯例上**也保留** `use super::*;`)

## struct.rs

```rust
use super::*;

/// User account information.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
#[derive(Data, New, CustomDebug)]
pub struct User {
    /// Unique user identifier.
    id: u64,
    /// Display name shown in UI.
    name: String,
    /// Email address, validated on creation.
    email: String,
}
```

## impl.rs

```rust
use super::*;

/// Default and constructor implementations for [`User`].
impl User {
    /// Returns whether this user has admin privileges.
    #[inline(always)]
    #[must_use]
    pub fn is_admin(&self) -> bool {
        // ...
    }
}
```

## fn.rs

```rust
use super::*;

/// Parse a user-supplied string into a [`User`].
///
/// # Arguments
///
/// - `input: &str` - Raw input string in the format `id|name|email`.
///
/// # Returns
///
/// - `Result<User, ParseError>`: Parsed user or validation error.
pub fn parse_user(input: &str) -> Result<User, ParseError> {
    // ...
}
```

## const.rs

```rust
use super::*;

/// Maximum length of a user name.
pub const MAX_USER_NAME_LEN: usize = 64;
```

## enum.rs

```rust
use super::*;

/// Connection lifecycle states.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Hash)]
pub enum ConnectionState {
    /// Initial state, not yet connected.
    #[default]
    Idle,
    /// Handshake in progress.
    Connecting,
    /// Active connection.
    Connected,
    /// Connection closed cleanly.
    Closed,
}
```

## trait.rs

```rust
use super::*;

/// Capability to serialize for storage.
pub trait Persistable {
    /// Output type when persisted.
    type Output;

    /// Persist `self` into the output form.
    fn persist(&self) -> Self::Output;
}
```

## type.rs

```rust
use super::*;

/// A boxed future returning `Result<T, E>`.
pub type BoxedResult<T, E = Box<dyn std::error::Error + Send + Sync>> = Result<T, E>;
```
