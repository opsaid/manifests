# Kustomize 应用商店目录与命名改进实施计划

日期：2026-09-07  
状态：三个批次的本地改进已实施；集群验收按维护者要求暂不纳入本轮。本轮未执行部署或发布。

## 1. 目标与文档职责

保留现有公共 base、私有 overlay、公开示例和应用发布机制，统一应用目录分类、命名、模板与校验规则，使后续应用能够按相同方式制作、审查和接入商店。

本文记录本次结构改进的实施顺序、验收条件与文件迁移映射；长期规则已经落实到公共规范，后续以规范正文为准。

- [AGENTS.md](../../AGENTS.md) 是编辑权限的唯一依据。
- [Addon Store 公共规范](../spec/addon-store.md) 是长期合同的权威来源。
- [Addon Store 状态](../addon-store-status.md) 继续作为商店整体建设与发布进度的唯一入口；实施时只在那里汇总里程碑，本文不重复维护发布待办。
- 应用发布影响写入 `CHANGELOG/<id>/CHANGELOG-v<major>.md`，不以实施计划代替发布说明。

## 2. 现状基线

以下为编写计划时的文件检查结果，实施前需重新确认工作区和应用状态。

| 范围 | 当前情况 | 改进目的 |
| --- | --- | --- |
| 应用与索引 | 4 个 addon；open-webui 为唯一商店试点，`catalog.yaml` 的 `items` 为空 | 区分目录存在、结构合规和正式上架 |
| 顶层布局 | 已有 `addons/`、`examples/overlays/`、`docs/`、`CHANGELOG/`、`template/`、`scripts/` | 保留职责边界，避免无收益的路径改名 |
| 存量分类 | argo-events、argo-workflows 使用 `cluster/`、`service/`；argo-events 还有 `config/configmap/` | 对齐现有模板分类 |
| RBAC | argo-cd 的 `security/roles/` 混放 ServiceAccount、Role、RoleBinding、ClusterRole、ClusterRoleBinding | 按资源 Kind 明确归属 |
| 配置归属 | argo-cd 的 `configuration/configmaps/argocd-secret.yaml` 实际为 Secret | 使文件位置与对象类型一致 |
| 多对象文件 | open-webui 的 `network/services/open-webui.yaml` 包含主服务和 Redis 两个 Service | 提高定位和变更审查效率 |
| 模板 | 混用 `appname`、`app`、`demo-v1`；包含 Node 示例和多处占位 README；Namespace 文件未加入默认入口 | 减少复制后的清理工作，明确默认构建范围 |
| 文档 | 应用制作 README 与接入文档存在运行说明重叠；open-webui 制作 README 仍提到 `REQUESTS_VERIFY=False`，当前配置为 `True` | 明确权威来源并修复漂移 |
| 校验器 | `scripts/validate.py` 对命中 catalog 或 `--app` 的应用调用 `check_openwebui()` | 支持按应用分派合同检查 |

## 3. 范围和实施边界

本次计划覆盖目录规范、模板、应用文档职责、校验器扩展及存量应用结构迁移。

计划存在不代表已经批准其中的功能清单调整。根据 AGENTS.md，修改 `addons/<id>/` 的功能资源、应用 README，或新增资源文件前，应提交具体文件范围、理由及预期渲染差异，取得维护者明确同意后执行。维护者已明确批准对应阶段和范围时，执行时沿用该授权。本轮已获授权按三个批次实施模板、校验器、文档和应用目录迁移，包括对应功能资源路径与引用调整。维护者明确暂不考虑集群验收，运行环境及远程发布不在本轮实施范围。

结构迁移以保持渲染对象语义不变为默认验收目标。镜像升级、运行配置调整、资源增删和依赖变化应另列变更，不能夹带在目录整理中。模板收敛可能改变模板自身的资源名或默认资源集合，须明确记录预期变化，不直接套用到存量应用。

本计划不安排集群部署、私有仓库建设、catalog 上架、Git tag 创建、推送或仓库可见性调整；这些继续按现行商店发布流程处理。

## 4. 目标结构与命名

### 4.1 顶层结构

```text
manifests/
├── addons/<id>/                 # 公共应用 base，应用根目录即构建入口
├── catalog.yaml                 # 完成上架门槛的应用索引
├── examples/overlays/<id>/      # 完整、可构建的虚构环境示例
├── docs/README.md              # 文档导航
├── docs/apps/<id>/             # 安装、输入、依赖、升级和运维说明
├── docs/spec/                  # 长期规范的唯一正文
├── docs/plan/                  # 有边界的实施方案
├── docs/addon-store-status.md   # 商店整体状态和待办
├── CHANGELOG/<id>/             # 按应用和版本线记录发布影响
├── template/appname/           # 新应用最小制作骨架
├── scripts/                    # 通用工具及应用专属检查
└── .agents/skills/             # Agent 工作流，引用 docs/spec 中的规范
```

- 保留 `addons/`，不改名为 `apps/`；保留 `template/`、`CHANGELOG/` 的现有拼写。
- 保留 `addons/<id>/kustomization.yaml`，不增加无实际用途的 `base/` 层级。
- 应用类别将来按商店消费需求进入 catalog 元数据，不增加 `addons/ai/` 等分类路径。
- 应用版本继续使用 `<id>-v<semver>` tag，不复制 `v1/`、`v2/` 目录，不重复维护镜像版本和 `latestVersion`。
- 私有环境沿用独立仓库中的 `environments/<environment>/<id>/` 规划；出现实际多集群需求后再评估扩展层级。

文档按职责划分：`docs/apps/` 覆盖应用完整使用周期；`docs/spec/` 保存长期规则；
`docs/plan/` 保存实施方案。商店整体状态继续使用现有单一文件，应用发布历史继续放在根
`CHANGELOG/`。不预建空的应用文档目录或尚无实际内容的 guides、design 等分类。

### 4.2 已采纳的应用目录规则

Kind 到目录映射、命名及文件粒度已进入 [公共规范 §2](../spec/addon-store.md)。
其中补充了存量 argo-workflows 实际使用的 PriorityClass 归属；保留上游 CRD 同 Kind
多对象文件，RBAC 按 Kind 拆分。本计划不再复制维护规范表格。

## 5. 三个执行批次与原阶段对应

| 批次 | 实施内容 | 对应原阶段 | 本轮结果 |
| --- | --- | --- | --- |
| 一：基础正确性 | 模板 selector、失败用例、open-webui 错误运行说明、状态措辞 | 阶段一、二、三的优先修复 | 本地完成 |
| 二：可重复制作 | 正式目录规范、最小模板、合同分派、目录/catalog/链接检查及 CI | 阶段一、二、三 | 本地完成 |
| 三：应用接入准备 | 4 个 addon 目录迁移、渲染等价比较、维护说明及 open-webui 验收步骤 | 阶段四、五 | 本地完成；集群验收暂缓 |

以下保留各阶段的工作范围和验收标准，整体进度只在状态文档中汇总。


### 阶段一：确定规范与文档职责

依赖：无。优先级：高。

工作项：

- 将应用接入文档统一到 `docs/apps/<id>/`，保持应用 ID 与 addon 一致；专项依赖文档随应用移动。
- 将公共规范唯一正文迁入 `docs/spec/addon-store.md`，同步 AGENTS.md 和技能引用，移除旧位置正文。
- 新增 `docs/README.md` 导航；同步 catalog 文档路径示例、根 README、应用 README、公开示例、CHANGELOG 索引和状态文档中的链接。
- 在公共规范的唯一正文中落实目标目录映射、命名、文件粒度和例外规则。
- 对齐 `template/appname/README.md` 的分类说明，修复 RBAC 归属描述冲突。
- 明确应用制作 README 负责上游来源、制作过程和结构差异；`docs/apps/<id>/README.md` 负责当前安装与运行合同。接入文档仍保留规范要求的来源摘要和链接。
- 明确示例 README 仅解释示例使用方式；发布历史由 CHANGELOG 负责。
- 核对并修复 open-webui 的陈旧运行说明，链接到当前接入文档；制作说明保留结构依据，当前输入表只有一个维护来源。

涉及范围：公共规范、AGENTS.md、技能入口、catalog 文档路径、文档导航、模板 README、相关应用文档及经批准的应用 README。

验收：目录映射无同一种 Kind 的冲突归属；示例、制作说明和接入文档链接有效；当前配置描述一致；未改变应用渲染结果。长期规范仍只有一个权威正文。

前序文档迁移评估结论：

- 校验器按 catalog 的 `docs` 字段解析仓库内路径，没有写死应用文档父目录；当前 catalog 为空，迁移只更新注释和规范示例，不创建上架条目。
- 公开审查递归扫描工作区 Markdown，规范迁入 `docs/spec/` 后仍在扫描范围内。
- `CLAUDE.md` 继续导入 AGENTS.md，Claude 技能符号链接继续指向共享技能，均不建立第二份规则。
- 应用文档和规范移动后修正相对链接；应用说明补充仓库命令的执行目录。
- 前序文档迁移不改变应用资源；本轮已继续完成资源目录词表、模板收敛、陈旧运行说明修订和校验器拆分。
- 迁移完成后的整体进度以 [Addon Store 状态](../addon-store-status.md) 为准；Git 历史中的旧路径和带提交链接的历史变更记录不作改写。

### 阶段二：收敛新应用模板

依赖：阶段一。优先级：高。

工作项：

- 统一应用占位名称为 `appname`，清理 `app`、`demo-v1` 等混用；应用实际配置键不机械替换。
- 选定一个最小默认构建集合，明确 Namespace 是否由包创建并保持入口与文档一致。
- 从默认应用骨架移除 Node 示例；将按需资源的说明集中到模板文档，减少仅用于占位的 README。
- 清理未被入口引用且不属于必要 generator 输入的演示文件；保留可用的最小配置注入示例。
- 更新制作步骤，使用从仓库根目录或明确工作目录可执行的路径。

涉及范围：`template/` 及引用其制作步骤的文档；不直接批量覆盖现有 addon。

验收：`kustomize build template/appname` 成功；默认对象集合符合说明；替换应用 ID 后的临时副本可构建；无残留旧占位名称、未解释的演示对象或悬空引用。模板对象变化有明确清单。

### 阶段三：通用校验与应用合同分离

依赖：阶段一；可与阶段二分别实施。优先级：高，第二个应用上架前完成。

建议工具结构：

```text
scripts/
├── validate.sh                 # 保持现有命令入口
├── validate.py                 # 调度、通用检查与应用合同分派
├── checks/
│   ├── open_webui.py           # 迁出现有 open-webui 专属检查
│   └── ...                    # 随应用接入增加检查模块
├── render-private.py
└── tests/
```

工作项：

- 用显式应用 ID 到检查函数的映射替代统一调用 `check_openwebui()`。
- 检查 `--deploy` 和 `render-private.py` 等调用链：未具备相应应用合同的交付入口继续明确限制支持范围，不能因模块拆分就声明通用支持。
- 保持全仓构建、公开审查和应用合同检查的边界；文档明确 `--app` 的选择语义。
- 对已登记或显式请求合同验收的应用，缺少合同检查时明确失败，避免跳过后误报合规。
- 新增目录映射、应用 ID、入口、引用与文档路径校验；检查实际资源 Kind，不只根据文件名推断。
- 区分 Kubernetes 清单和 generator 原始输入；不把应用配置 YAML 的字段当成 Kubernetes Kind 校验。
- 为旧应用记录明确的迁移例外，在对应应用迁移时移除；例外不能豁免凭据及公开信息规则，也不能自动授予上架资格。
- 增加有意义的正反用例：错误归属、无效引用、缺失合同必须失败；generator 输入和已声明例外正确通过。

涉及范围：`scripts/`、必要的 CI 配置及使用说明。

验收：现有 open-webui 合同用例保持有效；新分派行为和失败分支有测试覆盖；旧应用仍可接受通用构建检查；CLI 与 CI 行为一致且有文档说明。

### 阶段四：逐个应用迁移

依赖：阶段一、三；本轮对应的应用目录迁移已获维护者授权。优先级：中。

建议顺序与范围：

| 顺序 | 应用 | 结构工作 |
| --- | --- | --- |
| 1 | open-webui | 将两个 Service 分文件，核对资源文件命名，修复制作文档漂移，作为迁移示范 |
| 2 | argo-cd | 按 Kind 拆分 RBAC 目录，移动错置 Secret，更新子级和根级引用，核对 ConfigMap/Secret 清单与 files generator 输入的不同语义 |
| 3 | argo-events | `cluster/`、`service/`、`config/configmap/` 对齐目标目录；多对象文件先盘点 Kind，再决定拆分 |
| 4 | argo-workflows | 对齐集群和网络目录；盘点 CRD、RBAC、多对象清单与配置入口 |

每个应用分别完成：

1. 保存修改前的资源身份、数量和规范化构建基线；若原有构建失败，先记录原因并单独处理。
2. 列出旧路径到新路径映射、资源拆分清单和引用更新范围。
3. 保留必要的目录聚合入口，检查本地示例、文档和已知外部消费者是否引用子路径。
4. 执行文件迁移及引用更新，保留对象名称、镜像、配置内容和运行参数。
5. 对比渲染语义并运行检查，移除该应用对应的结构例外。
6. 记录实际兼容性影响；原 tag 保持不变，若后续发布则按合同判断版本变更类型。

验收：单纯目录迁移的对象集合与对象内容不变；所有入口和引用有效；具备专属合同的应用通过合同检查。未完成应用合同及运行验收的旧应用仍不上架。

### 阶段五：收尾与后续接入

依赖：对应应用完成阶段四。优先级：中。

- 在 `docs/addon-store-status.md` 汇总已完成的结构里程碑和剩余迁移项。
- 检查根 README、模板说明、应用文档、示例、CHANGELOG 索引中的路径与职责一致性。
- 清理完成迁移后不再使用的结构例外和陈旧目录说明。
- 以模板制作临时示例应用，验证文档指导、构建入口和通用结构检查形成完整流程；不将临时应用登记到 catalog。
- open-webui 的目录迁移记录到现有版本线 `Unreleased`，提交关联记录于 CHANGELOG；未上架的 Argo 应用以本计划迁移表和制作说明记录，不虚构发布版本。

## 6. 验证方式

| 变更类型 | 必需验证 |
| --- | --- |
| 仅计划或说明文档 | 相对链接、文件路径、Markdown 格式和事实一致性检查；确认无意外文件改动 |
| 模板变更 | 模板构建、临时实例构建、预期对象集合与占位名称检查、全仓校验 |
| 校验器变更 | `python3 -m unittest discover -s scripts/tests -v`、全仓校验、open-webui 合同检查、新增失败分支用例 |
| 应用结构迁移 | `kustomize build addons/<id>`、受影响示例构建、迁移前后语义比较、全仓与目标应用校验 |

使用 `scripts/kustomize-version.txt` 指定的工具版本和 `scripts/requirements.txt` 中的依赖。

```bash
scripts/validate.sh
scripts/validate.sh --app open-webui
python3 -m unittest discover -s scripts/tests -v
```

合同分派已实现；当前仅注册 open-webui。其他应用用 `scripts/validate.sh --app <id> --build-only` 验证本地结构和构建，缺少合同的 `--app <id>` 会失败，不以 open-webui 检查器替代。公开发布前仍执行现行 `scripts/validate.sh --audit-public` 及公共规范要求的其他门槛。

语义比较按 `apiVersion`、`kind`、`metadata.namespace`、`metadata.name` 识别对象；忽略 YAML 映射键顺序和无意义的文档排列，保留数组顺序语义。核对 selector、引用、RBAC、镜像、配置、探针和存储等对象内容，不以资源数量相同或 build 成功代替一致性证明。Secret 内容只在受控内存或临时文件中比较，不输出到普通日志或制品。

## 7. 回退与完成标准

每个阶段、每个应用保持可独立审查和撤销。结构迁移失败时，一并恢复文件路径和所有引用，重新构建核对；不恢复或覆盖工作区原有的无关改动。本次计划不触发部署，已部署环境的回退继续遵循应用的数据兼容性与恢复条件。

本项结构改进完成需要满足：

- 目录映射、命名和文档职责已进入权威规范，模板与实际实现一致。
- 通用校验和应用合同已分离，已登记应用缺少合同检查时会明确失败。
- 本轮约定迁移的应用全部通过对应结构、引用和渲染语义检查。
- 必要例外有明确对象与理由，已解决的旧规则不继续残留。
- 商店整体状态已更新，应用发布影响已记录，未混淆结构检查、集群验收和上架状态。

## 8. 暂缓项及触发条件

| 暂缓项 | 重新评估的触发条件 |
| --- | --- |
| `addons/` 改为 `apps/`、`template/` 改为 `templates/`、`CHANGELOG/` 改为小写 | 出现明确消费者约束，并能说明路径迁移收益 |
| 通用 Component | 第二个应用出现相同且已验证的可选功能需求 |
| 参数 schema、分类字段、商店 UI 元数据 | 存在具体消费者和稳定输入合同 |
| 模板生成脚本 | 手工制作步骤反复出现，已能定义稳定输入与输出 |
| 多集群目录和多层共享 overlay | 私有仓库实际环境结构与重复配置证明有必要 |

参考：[Kubernetes Kustomize base 与 overlay 说明](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/#bases-and-overlays)。目录命名与分层细节属于本仓库维护约定。

## 本轮应用文件迁移映射

以下映射保持应用根构建入口及 Kubernetes 对象身份不变；相对路径基于对应 addon。

| 应用 | 原路径 | 新路径 |
| --- | --- | --- |
| open-webui | `network/services/open-webui.yaml` | `network/services/open-webui.yaml`, `network/services/redis.yaml` |
| argo-cd | `security/roles/argocd-application-controller-clusterrole.yaml` | `security/clusterroles/argocd-application-controller.yaml` |
| argo-cd | `security/roles/argocd-application-controller-clusterrolebinding.yaml` | `security/clusterrolebindings/argocd-application-controller.yaml` |
| argo-cd | `security/roles/argocd-application-controller-role.yaml` | `security/roles/argocd-application-controller.yaml` |
| argo-cd | `security/roles/argocd-application-controller-rolebinding.yaml` | `security/rolebindings/argocd-application-controller.yaml` |
| argo-cd | `security/roles/argocd-application-controller-sa.yaml` | `security/serviceaccounts/argocd-application-controller.yaml` |
| argo-cd | `security/roles/argocd-applicationset-controller-clusterrole.yaml` | `security/clusterroles/argocd-applicationset-controller.yaml` |
| argo-cd | `security/roles/argocd-applicationset-controller-clusterrolebinding.yaml` | `security/clusterrolebindings/argocd-applicationset-controller.yaml` |
| argo-cd | `security/roles/argocd-applicationset-controller-role.yaml` | `security/roles/argocd-applicationset-controller.yaml` |
| argo-cd | `security/roles/argocd-applicationset-controller-rolebinding.yaml` | `security/rolebindings/argocd-applicationset-controller.yaml` |
| argo-cd | `security/roles/argocd-applicationset-controller-sa.yaml` | `security/serviceaccounts/argocd-applicationset-controller.yaml` |
| argo-cd | `security/roles/argocd-notifications-controller-role.yaml` | `security/roles/argocd-notifications-controller.yaml` |
| argo-cd | `security/roles/argocd-notifications-controller-rolebinding.yaml` | `security/rolebindings/argocd-notifications-controller.yaml` |
| argo-cd | `security/roles/argocd-notifications-controller-sa.yaml` | `security/serviceaccounts/argocd-notifications-controller.yaml` |
| argo-cd | `security/roles/argocd-redis-role.yaml` | `security/roles/argocd-redis.yaml` |
| argo-cd | `security/roles/argocd-redis-rolebinding.yaml` | `security/rolebindings/argocd-redis.yaml` |
| argo-cd | `security/roles/argocd-redis-sa.yaml` | `security/serviceaccounts/argocd-redis.yaml` |
| argo-cd | `security/roles/argocd-repo-server-sa.yaml` | `security/serviceaccounts/argocd-repo-server.yaml` |
| argo-cd | `security/roles/argocd-server-clusterrole.yaml` | `security/clusterroles/argocd-server.yaml` |
| argo-cd | `security/roles/argocd-server-clusterrolebinding.yaml` | `security/clusterrolebindings/argocd-server.yaml` |
| argo-cd | `security/roles/argocd-server-role.yaml` | `security/roles/argocd-server.yaml` |
| argo-cd | `security/roles/argocd-server-rolebinding.yaml` | `security/rolebindings/argocd-server.yaml` |
| argo-cd | `security/roles/argocd-server-sa.yaml` | `security/serviceaccounts/argocd-server.yaml` |
| argo-cd | `configuration/configmaps/argocd-secret.yaml` | `configuration/secrets/argocd-secret.yaml` |
| argo-events | `cluster/crds.yaml` | `clusters/crds/crds.yaml` |
| argo-events | `cluster/roles.yaml` | `security/serviceaccounts/argo-events-sa.yaml`, `security/clusterroles/argo-events-aggregate-to-admin.yaml`, `security/clusterroles/argo-events-aggregate-to-edit.yaml`, `security/clusterroles/argo-events-aggregate-to-view.yaml`, `security/clusterroles/argo-events-role.yaml`, `security/clusterrolebindings/argo-events-binding.yaml` |
| argo-events | `cluster/namespace.yaml` | `clusters/namespaces/argo-events.yaml` |
| argo-events | `cluster/events-webhook.yaml` | `security/serviceaccounts/argo-events-webhook-sa.yaml`, `security/clusterroles/argo-events-webhook.yaml`, `security/clusterrolebindings/argo-events-webhook-binding.yaml` |
| argo-events | `service/events-webhook.yaml` | `network/services/events-webhook.yaml` |
| argo-events | `config/configmap/controller-config.yaml` | `configuration/configmaps/controller-config.yaml` |
| argo-workflows | `cluster/crds.yaml` | `clusters/crds/crds.yaml` |
| argo-workflows | `cluster/roles.yaml` | `security/serviceaccounts/argo.yaml`, `security/serviceaccounts/argo-server.yaml`, `security/roles/argo-role.yaml`, `security/clusterroles/argo-aggregate-to-admin.yaml`, `security/clusterroles/argo-aggregate-to-edit.yaml`, `security/clusterroles/argo-aggregate-to-view.yaml`, `security/clusterroles/argo-cluster-role.yaml`, `security/clusterroles/argo-server-cluster-role.yaml`, `security/rolebindings/argo-binding.yaml`, `security/clusterrolebindings/argo-binding.yaml`, `security/clusterrolebindings/argo-server-binding.yaml` |
| argo-workflows | `cluster/namespace.yaml` | `clusters/namespaces/argo.yaml`, `clusters/priority-classes/workflow-controller.yaml` |
| argo-workflows | `service/services.yaml` | `network/services/argo-server.yaml` |
| argo-workflows | `service/ingresses.yaml` | `network/ingresses/workflows.yaml` |
| argo-cd | `security/roles/kustomization.yaml` | `security/kustomization.yaml` |
