# Kustomize 应用商店目录与命名改进实施计划

日期：2026-09-07  
状态：阶段一中的文档分类与规范正文迁移已实施；其余改进待实施。未执行 Git 提交或发布。

## 1. 目标与文档职责

保留现有公共 base、私有 overlay、公开示例和应用发布机制，统一应用目录分类、命名、模板与校验规则，使后续应用能够按相同方式制作、审查和接入商店。

本文记录本次结构改进的建议、实施顺序和验收条件；以下目标规则在完成相应规范修订前不替代现行约定。

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

计划存在不代表已经批准其中的功能清单调整。根据 AGENTS.md，修改 `addons/<id>/` 的功能资源、应用 README，或新增资源文件前，应提交具体文件范围、理由及预期渲染差异，取得维护者明确同意后执行。维护者已明确批准对应阶段和范围时，执行时沿用该授权。本轮已获授权实施文档分类方案，包括同步应用 README 的迁移链接；其余功能清单调整按后续阶段处理。

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

### 4.2 应用内部分类

保留现有功能分类框架，以固定的 Kind 到目录映射消除歧义。目录按需创建，不要求每个应用具备完整目录树。

| 目录 | 对象或内容 |
| --- | --- |
| `clusters/namespaces/` | Namespace 及与专用 namespace 配套的 LimitRange、ResourceQuota |
| `clusters/crds/` | 应用包负责管理的 CustomResourceDefinition |
| `configuration/configmaps/` | ConfigMap 清单或非凭据 generator 输入 |
| `configuration/secrets/` | Secret 清单或含占位凭据的 generator 输入 |
| `network/services/` | Service |
| `network/ingresses/` | Ingress |
| `network/policies/` | NetworkPolicy |
| `gateway/` | 应用负责的 Gateway API 资源；按实际使用的 Kind 补规则 |
| `security/serviceaccounts/` | ServiceAccount |
| `security/roles/`、`security/rolebindings/` | Role、RoleBinding |
| `security/clusterroles/`、`security/clusterrolebindings/` | ClusterRole、ClusterRoleBinding |
| `storage/persistent-volume-claims/` | PersistentVolumeClaim |
| `storage/persistent-volumes/` | 应用包明确负责的 PersistentVolume |
| `storage/storage-classes/` | 应用包明确负责的 StorageClass |
| `workloads/deployments/`、`statefulsets/`、`daemonsets/`、`cronjobs/` | 对应工作负载 Kind |

`security/` 按权限功能收纳所有 RBAC，不再定义为仅命名空间级资源；`clusters/` 也不代表全部集群作用域资源的集合。作用域、安装责任、升级及卸载所有权在应用文档中单独说明。将资源放入上述目录不表示应用可以接管共享平台资源。

新出现的 Kind 先补归属规则，不自动放入最相近目录。CR 实例不等同于 CRD，不统一塞入 `clusters/crds/`。

### 4.3 命名与文件粒度

- 应用 ID 使用稳定的小写 kebab-case；展示名采用上游正式名称，例如 `argo-cd` / `Argo CD`。
- 资源目录使用上表固定词表，保留已有 `serviceaccounts`、`persistent-volume-claims` 等约定。
- 单对象清单优先使用 `<metadata.name>.yaml`，不重复追加目录已表达的 Kind；现有上游文件名可在迁移中逐步对齐。
- 优先一对象一文件；大批上游生成资源可保留经说明的多对象文件，不强制为形式一致拆分全部 CRD。
- 资源名、容器名和 generator 逻辑名是应用接口。整理文件名和路径时保留这些名称，不为统一拼写改变 `argocd-server` 等既有接口。
- generator 输入按逻辑组件命名，例如 `configuration/configmaps/open-webui.env`；任意应用配置文件的扩展名遵循应用实际需要。
- 保留必要的子目录 `kustomization.yaml` 聚合入口；不要求每个分类目录都增加入口。

## 5. 分阶段实施

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
- 在获准修改应用 README 后，核对并修复 open-webui 的陈旧运行说明，链接到当前接入文档，避免维护两份输入表。

涉及范围：公共规范、AGENTS.md、技能入口、catalog 文档路径、文档导航、模板 README、相关应用文档及经批准的应用 README。

验收：目录映射无同一种 Kind 的冲突归属；示例、制作说明和接入文档链接有效；当前配置描述一致；未改变应用渲染结果。长期规范仍只有一个权威正文。

本轮文档迁移评估与实施范围：

- 校验器按 catalog 的 `docs` 字段解析仓库内路径，没有写死应用文档父目录；当前 catalog 为空，迁移只更新注释和规范示例，不创建上架条目。
- 公开审查递归扫描工作区 Markdown，规范迁入 `docs/spec/` 后仍在扫描范围内。
- `CLAUDE.md` 继续导入 AGENTS.md，Claude 技能符号链接继续指向共享技能，均不建立第二份规则。
- 应用文档和规范移动后修正相对链接；应用说明补充仓库命令的执行目录。
- 当前仅落实文档分类、文档职责与引用迁移；资源目录词表、模板收敛、陈旧运行说明修订及校验器拆分仍按本计划后续工作处理。
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

依赖：阶段一、三；每个应用迁移前确认具体只读路径变更已获批准。优先级：中。

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
- 将有实际发布影响的变更记录到对应版本线的 `Unreleased`，不把结构完成标记为运行验收或正式发布。

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

其他应用的 `scripts/validate.sh --app <id>` 合同验收依赖阶段三分派机制及对应应用检查实现；当前不能用 open-webui 检查器替代旧应用验收。公开发布前仍执行现行 `scripts/validate.sh --audit-public` 及公共规范要求的其他门槛。

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
