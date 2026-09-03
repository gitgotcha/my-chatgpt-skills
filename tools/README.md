# Tools

`tools/` 保存供客户端本地运行的工具。当前唯一工具是 [Reliable Drive Sync local MCP](./reliable-drive-sync-mcp/README.md)。

## Reliable Drive Sync local MCP

这是 ChatGPT desktop Work、Codex 和 WorkBuddy 共用的本地 stdio MCP。它对上层只暴露一个工具：

```text
submit_event
```

## 本地职责

```mermaid
flowchart LR
    A["Skill"] --> B["submit_event"]
    B --> C["SQLite Outbox"]
    C -->|"网络可用时"| D["Worker /v1/jobs"]
    D --> E["D1 Outbox"]
```

- 在任何网络调用前把事件写入本地 SQLite。
- 将待发送记录交给 Worker `/v1/jobs`。
- 只有收到 HTTP 202 和非空 `jobId` 后，才从本地 Outbox 移除记录。
- 自动重试 `pending` 或被中断的 `sending` 记录。
- 为三类本地客户端生成或更新配置，避免把共享密钥写入客户端配置文件。

只读面试会话查询和 legacy migration dry-run 走 `/v1/query`，不进入本地或云端 Outbox。

## 回执

| `deliveryState` | 含义 |
| --- | --- |
| `cloud_accepted` | SQLite 已落盘，D1 已接收 durable job；Drive 仍为 `pending` |
| `pending` | SQLite 已安全持久排队，但尚未确认 D1 接收 |

客户端在 `pending` 状态下可以退出，记录会保留并在之后重试。两种回执都不表示 Google Drive 已完成。

## 配置与验证

Windows 配置步骤、环境变量和客户端导入方式见 [reliable-drive-sync-mcp/README.md](./reliable-drive-sync-mcp/README.md)。完成配置并重启客户端后，`tools/list` 应只返回：

```text
["submit_event"]
```

本架构没有公共 `/mcp` endpoint、capability URL、远程 OAuth flow 或 Secure MCP Tunnel。

从本地 MCP 目录运行：

```bash
cd tools/reliable-drive-sync-mcp
npm test
```

相关入口：

- 云端 Worker：[../services/reliable-drive-sync-worker/README.md](../services/reliable-drive-sync-worker/README.md)
- 仓库总览：[../README.md](../README.md)
