---
name: gtl
description: gtl is a Git-based tool designed to simplify the management of multiple remote repositories. It extends Git's functionality by providing one-click initialization and pushing to multiple remote repositories, making it especially useful for developers who need to maintain multiple remote repositories simultaneously.
---

# gtl

- GitHub: <https://github.com/crates-dev/gtl.git>
- crates.io: <https://crates.io/crates/gtl>
- docs.rs: <https://docs.rs/gtl>

## Docs

> `gtl` is a Git-based tool designed to simplify the management of multiple remote repositories. It extends Git's functionality by providing one-click initialization and pushing to multiple remote repositories, making it especially useful for developers who need to maintain multiple remote repositories simultaneously.

## Features

- **Multi-remote repository management**: Supports configuring multiple remote repositories for a single local repository.
- **One-click remote repository initialization**: Allows you to initialize and configure multiple remote repositories in one command.
- **One-click push to multiple remote repositories**: You can push code to all configured remote repositories with a single command, saving time and effort.
- **Git command extensions**: Adds convenient operations to Git, improving work efficiency.

## Installation

Install `gtl` via `cargo`:

```bash
cargo install gtl
```

## Usage

### Configuration file

> Path: /home/.git_helper/config.json

```json
{
  "D:\\code\\gtl": [
    { "name": "gitee", "url": "git@gitee.com:eastspire/gtl.git" },
    { "name": "origin", "url": "git@github.com:eastspire/gtl.git" }
  ]
}
```

### Initialize multiple remote repositories

Assuming you already have a local Git repository and want to link it to multiple remote repositories, use the following command:

```bash
gtl init
```
