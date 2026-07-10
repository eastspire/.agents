---
name: server-manager
description: server-manager is a rust library for managing server processes. It encapsulates service startup, shutdown, and background daemon mode. Users can specify the PID file, log file paths, and other configurations through custom settings, while also passing in their own asynchronous server function for execution. The library supports both synchronous and asynchronous operations. On Unix and Windows platforms, it enables background daemon processes.
---

# server-manager

- GitHub: <https://github.com/crates-dev/server-manager.git>
- crates.io: <https://crates.io/crates/server-manager>
- docs.rs: <https://docs.rs/server-manager>

## Docs

[Api Docs](https://docs.rs/server-manager/latest/)

> server-manager is a rust library for managing server processes. It encapsulates service startup, shutdown, and background daemon mode. Users can specify the PID file, log file paths, and other configurations through custom settings, while also passing in their own asynchronous server function for execution. The library supports both synchronous and asynchronous operations. On Unix and Windows platforms, it enables background daemon processes.

## Installation

To use this crate, you can run cmd:

```shell
cargo add server-manager
```
