# Google Drive 运行时存储约定

本项目已选择用户授权的 Google Drive 作为正式云端后端。运行时必须通过 Google Drive 连接器读写；`scripts/drive_protocol.py` 只生成经校验的路径与提交计划，不保存凭据、不直接调用 API，也不替代连接器。

## 根目录与读取边界

每次运行先从用户当前确认的 Drive 根目录取得 `root_folder_id`；不得把某个用户的文件 ID 写入 Skill。根目录下固定为 `system/`、`candidates/`、`exports/`：

- 仅从 `system/candidate_index.json` 读取候选人摘要。
- 展示候选人 ID、姓名、区分备注并取得二次确认后，才能访问 `candidates/<candidate_id>/`。
- 上传、更新或移动前必须重新读取目标目录或文件元数据；同名时先比较 ID 与用途，禁止盲目覆盖。

## 候选人初始化

使用 `build_candidate_tree_plan(root_folder_id, candidate_id, resume_id)`，按计划创建且仅创建候选人目录：`resumes/original`、`resumes/parsed`、`profile/history`、`events`、`sessions`。随后保存 `candidate.json`、`resume_index.json`、解析后的简历声明和 `profile/current_profile.json`。

原始简历、原始转写和 DOCX 均为二进制/原始文件上传；JSON 和 Markdown 采用 UTF-8。每次上传后读取返回的 Drive 文件 ID，并把该 ID 写入相应索引文件。简历声明只能用于出题，不能作为能力证据。

## 会话、复盘和画像提交

先上传不可变的 `session.json` 与 `raw_transcript.md`，状态为 `review_pending`。保存不可变的 `review_vN.json` 和 `review_report_vN.docx`；模拟复盘随即保存 `profile_update_event_vN.json`，真实复盘只在用户确认或拒绝时才首次写入对应的最终状态事件。只有模拟复盘或用户明确确认的真实复盘才可调用 `build_profile_commit_plan(...)`。

提交时按计划顺序执行：

1. 读取 `profile/current_profile.json`，核对 `candidate_id`、`profile_version` 和应用键；应用键已存在时直接返回现有画像。
2. 如果版本不等于 `expected_profile_version`，停止并返回 `profile_conflict`，不得覆盖任何文件。
3. 写入不可变 Review、事件和旧画像快照。
4. 在内存中构造并校验新画像，最后才以同一 Drive 文件 ID 替换 `current_profile.json`。

连接器不具备安全替换或读取能力时，返回 `cloud_persistence_pending`；不得把本地路径或测试替身称为成功保存。真实候选人不写入本地 Skill 目录，`D:\Interviews` 仅为用户下载后的可选备份。
