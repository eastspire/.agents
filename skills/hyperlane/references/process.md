---
synced_from: docs-pages/src/hyperlane/usage-introduction/process.md@f972247
sync_method: scripts/sync-references.sh
sync_date: 2026-08-14
---

<!--
This file is auto-synced from the upstream docs-pages repo.
Manual edits will be overwritten on the next sync. To pin a custom version
of this reference, add "# manual override:" to its mapping line and the
script will leave it alone.
-->


<Share colorful />

> [!tip]
>
> `hyperlane` 框架时序图如下

```mermaid
sequenceDiagram
    participant Client as "客户端"
    participant TcpListener as "TcpListener"
    participant Server as "Server"
    participant Stream as "Stream"
    participant Context as "Context"
    participant ReqMW as "Request Middleware"
    participant RouteMatcher as "Route Matcher"
    participant RouteHandler as "Route Handler"
    participant RespMW as "Response Middleware"

    Client->>TcpListener: "TCP 连接请求"
    TcpListener-->>Server: "accept() → TcpStream"

    Server->>Server: "configure_stream() 设置 TCP_NODELAY / TTL"
    Server->>Stream: "Stream::new(stream, request_config, false)"
    Server->>Context: "Context::default()"
    Server->>Server: "spawn(task_handler)"

    Note over Server: "Tokio 异步任务启动"

    Server->>Stream: "try_get_http_request()"

    alt "解析成功"
        Stream-->>Server: "Ok(request)"
        Server->>Server: "handle_http_requests(stream, ctx, request)"
        Server->>Server: "request_hook(stream, ctx, request)"

        Server->>Context: "重置 Context（request / response / route_params / attributes）"
        Note over Context: "keep_alive = request.is_enable_keep_alive()"

        Server->>ReqMW: "handle_request_middleware(stream, ctx)"
        ReqMW->>Context: "处理请求 / 可调用 stream.set_closed(true)"
        ReqMW-->>Server: "返回 Status"

        alt "Status = Reject"
            Server->>Stream: "is_keep_alive(keep_alive)"
            Stream-->>Server: "返回 keep_alive 状态"
        else "Status = Continue"
            Server->>RouteMatcher: "handle_route_matcher(stream, ctx, path)"
            RouteMatcher->>RouteHandler: "执行匹配的路由处理器"
            RouteHandler->>Context: "构建响应数据"
            RouteHandler-->>Server: "返回 Status"

            alt "Status = Reject"
                Server->>Stream: "is_keep_alive(keep_alive)"
            else "Status = Continue"
                Server->>RespMW: "handle_response_middleware(stream, ctx)"
                RespMW->>Stream: "stream.try_send(data) 发送响应"
                RespMW->>Client: "HTTP 响应"
                RespMW-->>Server: "返回 Status"
                Server->>Stream: "is_keep_alive(keep_alive)"
            end
        end

        alt "keep_alive = true && !closed"
            loop "Keep-Alive 循环"
                Server->>Stream: "try_get_http_request()"
                alt "读取成功"
                    Stream-->>Server: "Ok(new_request)"
                    Server->>Server: "request_hook(stream, ctx, new_request)"
                else "读取失败"
                    Stream-->>Server: "Err(error)"
                    Server->>Server: "handle_request_error(stream, ctx, error)"
                    Note over Server: "退出循环，回收 Context / Stream"
                end
            end
        else "keep_alive = false || closed = true"
            Note over Server: "退出循环，回收 Context / Stream"
        end

    else "解析失败"
        Stream-->>Server: "Err(RequestError)"
        Server->>Context: "set_request_error_data(error)"
        Server->>Server: "handle_request_error(stream, ctx, error)"
        Note over Server: "执行 request_error hooks 后回收 Context / Stream"
    end

    Note over Stream: "Box::from_raw 回收堆上内存"
```

<Bottom />
