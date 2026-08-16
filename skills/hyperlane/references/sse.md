---
synced_from: docs-pages/src/hyperlane/usage-introduction/sse.md@0c74235
sync_method: scripts/sync-references.sh
sync_date: 2026-08-16
---

<!--
This file is auto-synced from the upstream docs-pages repo.
Manual edits will be overwritten on the next sync. To pin a custom version
of this reference, add "# manual override:" to its mapping line and the
script will leave it alone.
-->


<Share colorful />

[GITHUB 地址](https://github.com/hyperlane-dev/hyperlane-quick-start/tree/sse)

> [!tip]
>
> `hyperlane` 框架支持 `sse`，服务端主动推送，下面是每隔 `1s` 完成一次推送，并在 `10` 次后关闭连接。

> [!tip]
>
> `sse` 规范: 服务器使用 `"content-type: text/event-stream"` 表示响应是一个 `sse` 事件流。
> 接着使用 `"data"` 字段来发送事件数据，每个事件以 `"data:"` 开头，后面跟着事件的内容和一个空行。
> 客户端收到这样的响应后，就可以解析其中的事件数据并进行相应的处理。
> 对于 `sse`，首次响应使用 `stream.try_send` 发送完整 HTTP 响应，非首次响应请统一使用 `stream.try_send` 方法直接发送数据。

### 原生写法

```rust
struct SseRoute;

impl ServerHook for SseRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        let data: Vec<u8> = ctx
            .get_mut_response()
            .set_header(CONTENT_TYPE, TEXT_EVENT_STREAM)
            .set_body(Vec::new())
            .build();
        if stream.try_send(data).await.is_err() {
            stream.set_closed(true);
            return Status::Reject;
        }
        for i in 0..10 {
            let body: String = format!("data:{i}{HTTP_DOUBLE_BR}");
            if stream.try_send(&body).await.is_err() {
                break;
            }
        }
        stream.set_closed(true);
        Status::Reject
    }
}
```

### 客户端代码

#### 断线重连

```js
const eventSource = new EventSource('http://127.0.0.1:60000');

eventSource.onopen = function (event) {
  console.log('Connection opened.');
};

eventSource.onmessage = function (event) {
  const eventData = JSON.parse(event.data);
  console.log('Received event data:', eventData);
};

eventSource.onerror = function (event) {
  if (event.eventPhase === EventSource.CLOSED) {
    console.log('Connection was closed.');
  } else {
    console.error('Error occurred:', event);
  }
};
```

#### 取消断线重连

```js
const eventSource = new EventSource('http://127.0.0.1:60000');

eventSource.onopen = function (event) {
  console.log('Connection opened.');
};

eventSource.onmessage = function (event) {
  const eventData = JSON.parse(event.data);
  console.log('Received event data:', eventData);
};

eventSource.onerror = function (event) {
  if (event.eventPhase === EventSource.CLOSED) {
    console.log('Connection was closed.');
    // 关闭连接，防止自动重连
    eventSource.close();
  } else {
    console.error('Error occurred:', event);
  }
};
```

<Bottom />
