# V2 存储运行约定

本文件入口保留以兼容现有引用。当前有效规则全部见 [RDS V2 运行契约](rds-v2-runtime.md)。唯一远端入口为 submit_event；读取 D1 物化画像，事件先落本机 V2 Outbox，云端异步归档。

不使用旧 Drive 路径、注册事件或历史全扫描。面试 JSON/DOCX 继续保存在 outputs/interview/<userId>/ 下作为本地派生输出，不能作为画像数据源。写回执不能推断 Drive 完成。
