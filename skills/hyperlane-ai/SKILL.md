---
name: hyperlane-ai
description: Hyperlane 框架 AI 辅助工具集合。基于 hyperlane HTTP 框架的 AI/LLM API 转发、对话会话、流式响应集成示例。触发关键词：hyperlane-ai、LLM API、AI proxy、chat API、streaming response。
---

# hyperlane-ai

- GitHub: <https://github.com/hyperlane-dev/hyperlane-ai>
- crates.io: <https://crates.io/crates/hyperlane_ai>
- docs.rs: <https://docs.rs/hyperlane_ai>

## Docs

# Hyperlane AI

This project provides a complete pipeline for fine-tuning language models and converting them to GGUF format for efficient inference.

## Project Overview

The pipeline includes the following steps:

1. Environment setup with Python virtual environment
2. Dependency installation
3. Dataset generation
4. Model fine-tuning with LoRA adapters
5. Merging LoRA adapters with the base model
6. Converting the merged model to GGUF format
7. Analyzing training arguments

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Git

## Setup and Usage

### 1. Clone the Repository

```bash
git clone <repository-url>
cd hyperlane-ai-training
```

### 2. Run the Training Pipeline

Execute the main script to run the complete pipeline:

```bash
./run.sh
```
