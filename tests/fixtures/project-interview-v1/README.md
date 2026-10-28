# Project interview contract v1 fixtures

`scenario.json` 是**合成**验收场景，仅用于隔离本地测试：

- 外层 `fixtureOnly: true`，**不是** `submit_event` DTO，禁止发送到真实 RDS 或个人账号。
- `baseSession` / `baseReview` 是合法的 `projectContractVersion: 1` 事件，供跨语言合同测试使用。
- `sessions` / `revision` / `recap` / `expectedTransitions` 描述期望的派生状态变化，供 T3/T7 的归约与离线回放测试使用。
- 身份、项目、作答、分数全部为合成；`actual_user` 仅表示隔离模拟中的“用户角色”。

测试约定：

- Python（`tests/test_project_interview_contract_parity.py`）读取本文件并生成变体；JS 一侧通过
  `RDS2_RUNTIME_ROOT` 指向运行时仓库，调用 `test/helpers/project-contract-harness.mjs`；未设置时该用例
  跳过并记为环境依赖，不伪装成通过。
- 需要 D1 的用例不得直接使用本文件，必须在本地隔离库中由测试自行构造事件。
