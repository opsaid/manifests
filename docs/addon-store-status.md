# Addon Store 状态与待办

本文是商店建设的唯一进度入口，随实际状态更新。长期规范只维护在
[Addon Store 公共规范](spec/addon-store.md)；
过程性实施决策与逐日证据不再作为活文档维护，历史内容见 Git 历史
（原 2026-09-06 计划与执行记录，已并入本文的活跃部分）。

## 当前状态

- 首期 open-webui 试点本地工具已实现；公开发布前置（全仓净化、历史改写、推送）已完成，
  人工公开复核与仓库可见性切换待确认。
- open-webui 为唯一试点：base、公开示例、校验器、[CHANGELOG](../CHANGELOG/README.md)
  与[应用文档](apps/open-webui/README.md)齐备；尚未集群验收，未上架（`catalog.yaml` 无条目，
  不通过文档存在推断发布状态）。
- 私有环境配置仓库尚未建设；真实环境差异维护在独立私有仓库 overlay。
- 文档分类已落实：应用接入位于 `docs/apps/<id>/`，公共规范位于 `docs/spec/`，
  [文档导航](README.md)提供统一入口。
- 三批本地改进已落实，范围和文件映射见
  [目录与命名改进计划](plan/2026-09-07-addon-store-structure-improvement.md)：
  模板补齐 selector 并收敛为 4 个默认对象；校验器增加目录、catalog、文档链接和工作负载
  selector 检查，按应用注册合同；4 个 addon 已完成目录迁移。
- 迁移前后对象内容等价：argo-cd 48、argo-events 17、argo-workflows 26、open-webui 9，
  公开 open-webui overlay 9。Argo 应用仍未接入专属合同，不能将结构检查等同上架验收。
- 本轮本地验证通过：34 项回归测试、65 个文档本地链接目标、全仓及逐应用检查，
  工作区公开扫描 0 发现；该扫描不覆盖 Git 历史，也不代表远程 CI 已执行。
  集群验收按维护者要求暂不纳入本轮，
  [open-webui 验收步骤](apps/open-webui/acceptance.md)已准备，待真实环境就绪后执行。

## 发布前门槛

### 运行验收（open-webui 试点）

- [ ] 测试环境验证：官方镜像拉取、固定 UID/GID 与可写目录、启动及探针、
  PostgreSQL/pgvector 连接、文件上传与读取、模型调用；启用 OAuth 时验证登录。
- [ ] 仅更新 env 后，滚动更新确实使新 Pod 使用新配置；Pod/Redis 重建后
  需保留的数据仍可用。
- [ ] 迁移后的私有 overlay 与旧入口做完整脱敏结构 diff，解释每项差异；
  据此准备并验证部署入口切换（含数据备份和回退条件）。

### 发布

- [ ] 运行验收通过后将 open-webui 加入 `catalog.yaml` 并登记模板版本。
- [ ] 在发布前检查全部通过的审查提交上创建并推送不可移动 tag；
  远程验证失败时不挪动 tag，标记不可用并修复后发布新版本。
- [ ] 发布后从干净临时目录用实际 URL + tag 构建 overlay，核对资源结果；
  先标为发布候选，远程验证通过后再宣布可用。
- [ ] 建设私有环境仓库（`environments/<environment>/<app>/`），并在其流水线
  验证生产配置。

### 平台与 CI

- [ ] 确认 GitHub Actions 首次远程运行通过。
- [ ] 确认部署系统不再直接引用 `addons/open-webui`，改用私有 overlay 固定
  公共仓库 tag/SHA；若由 Argo CD 等持续调谐，先落实它可用的凭据来源，
  不能用手工本地注入冒充 GitOps 闭环。
- [ ] 确认仓库公开状态后，删除或转存本机 `/tmp` 的两份 pre-rewrite 备份 bundle
  （含改写前原始真实值，仅存于维护者本机）。

## 后续扩展（需求触发）

| 实际需求 | 再增加的能力 |
| --- | --- |
| 第二个应用有相同可选功能 | 提取小型 component，保留单独测试与明确支持范围 |
| UI 需要读取应用配置项 | 从已稳定的输入文档提炼 schema，不提前设计通用配置引擎 |
| 受限网络无法访问公共 Git | vendor 固定提交并记录来源、许可证和更新 diff |
| 多环境反复复制公共差异 | 在私有仓库引入一层共享 overlay，避免预先堆叠公司/集群/地域层级 |
| GitOps 持续调谐密钥 | 选择已有 Secret 管理方案，定义资源 ownership 和更新方式 |
| 制作/升级步骤反复执行 | 按实际需要拆分 skill，统一引用 docs/spec 公共规范及根 scripts |
| argo-cd 等后续应用上架 | 单独盘点 files generator、CRD/ClusterRole 所有权、权限和升级行为 |
