---
name: certbot-letencrypt-txy-ssl
description: 腾讯云 certbot Let's Encrypt SSL 证书自动申请/部署脚本集合。使用 DNS-01 challenge 通过腾讯云 DNS API 申请免费 Let's Encrypt 证书并自动部署。触发关键词：certbot、Let's Encrypt、SSL、TLS、腾讯云 DNS、TXY certbot。
---

# certbot-letencrypt-txy-ssl

- GitHub: <https://github.com/ltpp-universe/certbot-letencrypt-txy-ssl>
- crates.io: <https://crates.io/crates/certbot_letencrypt_txy_ssl>
- docs.rs: <https://docs.rs/certbot_letencrypt_txy_ssl>

## Docs

# Certbot Let's Encrypt 腾讯云 DNS 自动签发

基于 Certbot 和腾讯云 DNSPod 的 SSL 证书自动签发工具，支持单域名、多域名和通配符证书签发。

## 功能特性

- 自动 DNS-01 挑战验证
- 支持单域名证书签发
- 支持通配符证书签发 (`*.example.com`)
- 支持自定义证书存储目录
- 支持证书自动续期
- 支持二级域名证书签发

## 环境要求

- Node.js >= 14.0.0
- Certbot 已安装
- 腾讯云 DNSPod 账号及 API 密钥

## 安装

```bash
npm install
```

## 使用方法

### 1. 签发单域名证书

```bash
node index.js -d example.com --secret-id YOUR_SECRET_ID --secret-key YOUR_SECRET_KEY
```

### 2. 签发通配符证书

```bash
node index.js -d "*.example.com" --secret-id YOUR_SECRET_ID --secret-key YOUR_SECRET_KEY --wildcard
```
