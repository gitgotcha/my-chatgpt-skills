# Algorithm Profile System Implementation Plan

**Goal:** 为 algorithm-learning 增加身份隔离的事件镜像和每日题单协议。

**Architecture:** Skill 保持答疑入口；引用文件定义身份、事件、快照、Drive 提交与日程协议。静态契约测试防止后续维护删除关键规则。

## Tasks

1. [x] 先写 `tests/test_skill_contract.py`，运行并确认因 Skill/协议文件缺失而失败。
2. [x] 新建 `SKILL.md`：保留先诊断用户代码，再给最小修改版和渐进提示；仅在身份确认后写学习事件。
3. [x] 新建画像契约、Drive 运行约定和每日协议，定义 userId/username 锁、事件幂等、快照乐观锁、3～5 题和失败中止。
4. [x] 新建已绑定用户的独立任务模板（每日 09:00 Asia/Shanghai）。
5. [x] 运行全部静态契约测试；创建 Drive 用户目录、种子文件与自动化；上传 GitHub 分支并创建草稿 PR。
