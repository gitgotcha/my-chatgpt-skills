# submit_event 授权契约

账户网关与业务技能共享一个入口：`submit_event`。账户和查询请求使用 `storageVersion: 2`、`operation`、`params`；个人查询和业务写入额外携带顶层 `bindingContext`。上下文仅用于版本比较，不是凭据，也不能用于查找另一位用户。

`account.current` 返回 `authenticated`、`unbound`、`reauth_required` 或 `verification_unavailable`。只有 `authenticated` 才能授权个人请求。每次绑定变化会生成新的 `bindingEpoch` 并递增 `bindingRevision`；旧上下文必须得到稳定的 `binding_changed` 拒绝。

业务技能应按以下顺序工作：

1. 调用 `account.current`。
2. 仅在状态为 `authenticated` 时，把完整上下文放入下一次个人请求。
3. 只处理该请求返回的用户数据；不把旧聊天中的内容自动归给新账户。
4. 失败时保留原始错误类别，不泄露 SQL、路径、秘密或其他用户信息。

