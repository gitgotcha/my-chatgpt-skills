---
name: account-gateway
description: 通过统一 submit_event 管理当前 Windows 用户的默认账户与授权上下文。
---

# 账户网关

本技能只负责账户授权，不读取个人内容，也不替其他技能判断学习事实。

所有操作都通过唯一的 `submit_event` 工具完成，使用 `storageVersion: 2`：

- 先调用 `account.current`，读取 `state` 与完整 `bindingContext`。
- 新用户使用 `account.register`；设备迁移使用 `account.transfer.redeem`。
- 已有本机账户使用 `account.find`、`account.bind`、`account.switch` 或 `account.unbind`。
- 已认证设备可使用 `account.transfer.create`，配对码只在安全界面显示。

不要在聊天中索取、复述或保存秘密、配对码或凭据。不要依据姓名猜测账户；同名账户必须由安全界面和服务端返回的 UUID 区分。除非用户明确要求切换账户，否则沿用当前设备绑定。

个人内容操作必须携带最近一次 `account.current` 返回的完整 `bindingContext`。遇到 `binding_changed`、`reauth_required` 或 `verification_unavailable` 时停止后续个人操作并重新获取状态；不得自动换人、自动注册或重试旧上下文。

普通不涉及个人内容的解释可以继续，不应为了加载本技能而读取或上传任何个人数据。

