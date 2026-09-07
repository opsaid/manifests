# 文档导航

应用使用者从对应应用的接入说明开始；应用维护者先阅读公共规范和仓库编辑约定。
文档中的仓库工具命令默认从 manifests 仓库根目录执行，特殊工作目录由对应步骤注明。

## 应用接入

`apps/<id>/` 保存应用的安装、配置、依赖、升级和运维说明，`<id>` 与 `addons/<id>/` 一致。
应用文档存在不代表已上架；可安装发布须满足公共规范的验收门槛，并按发布流程登记到
[catalog.yaml](../catalog.yaml)。

| 应用 | 接入与依赖 | 公开示例 |
| --- | --- | --- |
| Open WebUI | [接入说明](apps/open-webui/README.md)、[PostgreSQL 准备](apps/open-webui/postgres.md) | [完整 overlay](../examples/overlays/open-webui/README.md) |

尚未提供商店接入文档的存量应用不在这里预建空目录；整体接入和发布状态见下方状态入口。

## 公共规范与维护入口

- [Addon Store 公共规范](spec/addon-store.md)：应用包、文档、overlay、发布与验收的唯一权威正文。
- [AGENTS.md](../AGENTS.md)：仓库编辑权限与维护约定。
- [addon-maintenance 技能](../.agents/skills/addon-maintenance/SKILL.md)：Agent 执行流程，引用公共规范。
- [应用模板说明](../template/appname/README.md)：资源分类及新应用制作骨架。

`spec/` 保存长期规则。应用制作依据保留在 `addons/<id>/README.md`，安装输入和运行要求
维护在 `apps/<id>/`，示例目录保存可构建配置及其用法。

## 实施计划、状态与发布历史

- [目录与命名改进计划](plan/2026-09-07-addon-store-structure-improvement.md)：本次改进的目标、阶段和验收方式。
- [Addon Store 状态与待办](addon-store-status.md)：商店整体建设及发布进度的唯一入口。
- [应用变更记录](../CHANGELOG/README.md)：按应用和版本线记录发布影响。

`plan/` 保存有明确范围的实施方案，计划中的目标规则在修订公共规范前不替代现行合同。
