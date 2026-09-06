# Kustomize 应用商店实施计划（评估修订版）

状态：2026-09-06 仓库内实现已完成并通过本地验收；集群验收与公开发布待完成。
执行证据及阻塞项见 [执行记录](2026-09-06-addon-store-execution.md)。
技能入口见 [addon-maintenance](../.agents/skills/addon-maintenance/SKILL.md)，公共规范仅保留在
[references/addon-store.md](../.agents/skills/addon-maintenance/references/addon-store.md)。
本计划记录实施顺序与验收，规范保存长期约定，避免两处复制完整配置后漂移。

## 1. 结论与范围

保留 Kustomize base + overlay、按应用发布版本、先试点 open-webui 的方向。
首期以 Git 仓库提供应用发现、公开模板、版本选择和私有配置接入；部署仍交给现有工具。
不引入商店后端、数据库、Operator、自定义配置语言、依赖自动安装或通用参数表单。

公共仓库保存中性 base、完整的虚构环境示例和公共规范；真实环境配置放独立私有仓库。
密码、Token、带凭据的连接串即使在私有仓库也不以明文提交。
首期支持每个应用在独立 namespace 安装一份，不承诺同 namespace 多实例或集群安全隔离。

本次按维护者指示迁入 `.agents/skills/` 并执行仓库内任务。完成状态以勾选及执行记录为准；
未提供私有仓库、测试环境或完成发布条件的事项保持待办，不创建虚假版本。

## 2. 原计划不足与修订

| 优先级 | 不足与影响 | 修订 |
| --- | --- | --- |
| P0 | 同仓 `tenants/` 保存真实配置，与公开仓库目标冲突；远程引用某子目录不会形成访问隔离 | 删除真实租户同仓方案，公共示例只用虚构值；发布前检查整个公开仓库及可访问历史 |
| P0 | 只净化 open-webui，其他 addon、模板、README、计划仍有环境信息 | 应用试点可逐个做，仓库公开审查必须覆盖全部路径；必要时从净化快照建立独立公共仓库 |
| P0 | “base 可独立部署”与数据库、S3、OAuth 等占位符矛盾 | 区分可渲染、配置完整、运行验证三个门槛；base 只承诺第一项 |
| P0 | 缺少实际 Secret 注入办法；手动修改被跟踪的 env 容易误提交 | 私有仓库跟踪占位样例，在临时工作目录注入凭据；GitOps 另明确凭据来源，不能假设 Argo CD 会读取本机文件 |
| P0 | 原 Task 8 直接改只读 addon README，违反 AGENTS.md | 迁移前列出所需只读路径及具体改动，由维护者明确批准；本次不改这些文件 |
| P1 | 缺少“商店可发现”的入口 | 新增最小 `catalog.yaml`，只登记完成验收的应用；不通过目录存在推断已上架 |
| P1 | `tenants/*/` 少一层；声称扫描 template 但实际只扫描登记 addon；渲染 grep 看不到 Secret.data 原文 | 按目录职责枚举入口，扫描源文件及解析后的渲染对象，Secret 在内存解码，输出只含位置和规则 |
| P1 | 黑名单只能发现几个已知组织值；构建错误被吞掉 | 黑名单仅作补充，增加凭据扫描、占位值策略和人工公开审查；错误保留经脱敏的诊断 |
| P1 | 固定 generator 名后，修改 env 不会自动替换 Pod | 首期保留仓库现有稳定名称约定，部署流程显式触发并验证工作负载滚动更新 |
| P1 | 仅删除 newName 就把私有镜像换成官方镜像，却未验证运行差异 | 验证镜像可拉取、架构、固定 UID/GID、写目录权限、探针及所需功能，失败则阻止发布 |
| P1 | 清除域名后仍有环境假设：Ingress class、身份 UUID、证书策略、OAuth 开关等 | 按“通用默认 / 必填 / 条件必填 / 环境差异”逐项盘点，不整文件照抄现有租户配置 |
| P1 | 所有镜像升级都升次版本，忽略数据库迁移和默认行为破坏；只改 ref 不保证数据可回滚 | 按模板兼容性定版本，单列应用版本与迁移要求；回退清单前确认数据兼容或恢复方案 |
| P1 | “本机已验证”没有工具版本和可复跑证据，且只验证本地 base | 固定 CI 工具版本，提交最小合同用例；发布后从干净目录验证真实远程 tag |
| P2 | docs 中嵌入大量整文件替换与逐步 commit 指令，容易与正在编辑的文件冲突 | 改为任务、文件边界和可检查验收；使用小范围修改与可独立审查的变更 |
| P2 | 提前引入 components、vendoring 机器人或专用 agent 工作流 | 有实际复用和交付需求再引入；实施不依赖当前未提供的 superpowers skill |

## 3. 最小目录布局

```text
公共仓库 manifests/
├── addons/<app>/                   # 中性 base，保留现有资源分类
├── template/appname/               # 新应用骨架
├── examples/overlays/<app>/         # 完整可渲染示例，仅虚构值，本地 base 引用
│   ├── kustomization.yaml
│   └── configuration/{configmaps,secrets}/
├── catalog.yaml                    # 应用索引，字段见 .agents/skills/addon-maintenance/references/addon-store.md
├── AGENTS.md                       # 共享仓库规则及技能入口
├── CLAUDE.md                       # 仅导入 AGENTS.md
├── .claude/skills/addon-maintenance # 符号链接到共享技能
├── .agents/skills/addon-maintenance/ # 技能正文唯一来源
│   ├── SKILL.md                     # 触发范围与维护流程
│   └── references/addon-store.md    # 公共规范的唯一来源
├── docs/apps/<app>.md               # 应用依赖、输入、运行和升级说明
├── docs/*-plan.md                   # 阶段计划，不作为规范入口
├── scripts/                        # 构建与校验程序
└── CHANGELOG.md                     # 按应用记录模板发布

独立私有仓库 environment-config/
└── environments/<environment>/<app>/
    ├── kustomization.yaml          # 公共 base 的固定 ref + 环境差异
    └── configuration/
        ├── configmaps/<app>.env    # 私有非凭据配置，可提交到私有 Git
        └── secrets/<app>.env       # Git 中仅占位，临时构建副本注入真实值
```

`.agents/skills/addon-maintenance/SKILL.md` 保存短流程，`references/addon-store.md` 保存规范全文；
删除 `spec/`，不留副本。`docs/apps/` 描述应用特例，`examples/` 保存受校验示例，
根 `scripts/` 供 AI 与 CI 共用。`AGENTS.md` 引用技能入口并保留全局编辑边界。
Codex 从 `.agents/skills/` 发现技能；Claude Code 通过 `.claude/skills/addon-maintenance`
符号链接读取同一份正文。根 `CLAUDE.md` 使用 `@AGENTS.md` 导入统一规则，其他 agent 可从
AGENTS.md 的链接读取技能。不同工具的入口可以不同，规则及技能正文均只维护一份。

## 4. 关键实施决策

| 决策 | 首期选择 | 扩展条件 |
| --- | --- | --- |
| 公私边界 | 公共内容与私有环境分仓，本组织也遵循相同接入方式 | 多公司各自维护私有仓库，不增加公共 tenants 层 |
| 配置接口 | `kustomization.yaml` + `configuration/`；env 用同名 generator merge | `files:` 的 YAML/JSON 只按整个 data key 替换，不承诺深度合并 |
| 密钥交付 | 部署端在临时副本注入后构建、应用并清理 | 已有 GitOps 场景选择 SOPS 或外部 Secret 控制器之一，单独提供适配 |
| 配置更新 | 保留稳定 generator 名，部署流程负责滚动更新 | 有自动更新需求再评估 hash 后缀及 GC，不为首个应用部署 reloader |
| 版本 | `<app>-v<semver>` 的受保护、不可移动发布 tag；生产也可固定完整 commit SHA | 不增加锁文件；镜像版本以该 ref 的 kustomization 为准 |
| 应用索引 | 一个简单 YAML 列表，文档保存依赖与输入 | 出现实际 UI 消费者后才增加输入 schema、图标和多版本索引 |
| 可选功能 | 少量 inline patches；按对象和容器名选取目标 | 多应用重复能力有相同语义和测试后才提取 components |
| 安装归属 | 一应用一 namespace；共享 CRD、Ingress Controller、数据库由平台提供 | 新应用涉及共享集群资源时单独制定 ownership，禁止默认随应用卸载 |

## 5. 实施任务与验收

### Task 1：明确发布边界，记录迁移基线

涉及：只读盘点现有目录、`AGENTS.md`、部署入口；在受控本地记录迁移依据。

- [ ] 确认公共发布使用本仓库还是净化后的独立仓库，不将“仅发布子目录”当作保密措施。
- [ ] 检查全部待公开文件、文档、样例及可访问历史；真实凭据若曾泄露，需撤销或轮换，删除当前行不够。
- [ ] 识别部署系统是否仍直接引用 `addons/open-webui`；在改 base 前准备私有 overlay 的迁移方案。
- [x] 保存资源身份、镜像、配置键、RBAC、探针、存储等基线；含密钥的渲染结果不得写入公共工作区或日志。
- [ ] 列出 `addons/open-webui/README.md` 等只读路径净化项，以及其他 addon/模板的公开阻塞项；按 AGENTS.md 取得具体修改授权。

验收：发布边界和迁移路径明确；未完成全仓净化时可以继续内部试点，但不能宣称仓库可安全公开。

### Task 2：固化公共规范与应用接入说明

涉及：`.agents/skills/addon-maintenance/`（规范迁入 references，SKILL.md 仅维护流程）、`docs/apps/open-webui.md`；后续按已落实范围更新 `AGENTS.md` 引用。

- [x] 按维护者本轮指示迁移至 `.agents/skills/`：规范只在 references 保存，SKILL.md 保存流程，AGENTS.md 引用入口。
- [x] 固定 CI Kustomize v5.0.0，定义部署执行方注入 Secret、一应用一 namespace 的首期方式。
- [x] 记录应用来源 chart/tag、镜像、许可证/再分发要求，以及已验证的 Kubernetes/架构/运行环境。
- [x] 为 open-webui 列出输入表：键、存放位置、默认值、必填条件、是否敏感、是否影响重启。
- [x] 写明 PostgreSQL + pgvector、S3、模型 API、Ingress Controller 的前置要求；OAuth/OTEL 按开关列条件输入。
- [x] 说明 emptyDir 数据边界、数据库备份及卸载保留项，撤回未经验证的“完全无状态”承诺。
- [ ] 在真实环境验证 Pod/Redis 重建及数据保留行为。

验收：读者能确定安装需要准备什么、哪些参数必须填写、安装和卸载分别影响什么。

### Task 3：open-webui base 中性化

仅修改：`addons/open-webui/kustomization.yaml` 与 `configuration/`。
已获具体授权的 README/功能清单改动另列，不夹带在此任务中。

- [x] 在当前文件上做小范围修改，不照抄原计划的整文件替换，以免覆盖正在进行的工作。
- [x] 移除真实 host、私有 registry、环境身份标签/UUID；保留通用标签、已固定的镜像版本和资源基线。
- [x] 区分通用默认与环境偏好：不要直接将禁用证书校验、OAuth 自动关联或授权规则当作商店默认。
- [x] 通过入口 patches 处理 Ingress class 等部署假设；允许 base 包含必要的通用适配 patch，不规定“base 无 patches”。
- [x] 将域名、基础设施地址和凭据中性化；禁用可选功能时明确哪些占位输入不参与运行校验。
- [x] 保留同 namespace 的 Redis 访问能力；使用短 Service 名需验证，若保留 FQDN 则在输入表标注 namespace 联动。
- [x] 渲染并按结构检查 9 个资源的身份及引用，确认差异都在预期范围。

验收：base 可独立渲染且不带租户值；不把 CHANGE_ME、空桶名或未验证的官方镜像视为可运行配置。

### Task 4：完整公开示例与私有部署接入

新增：`examples/overlays/open-webui/kustomization.yaml`、完整的 configmaps/secrets env 和使用说明。

- [x] 示例引用 `../../../addons/open-webui`，包含所有被引用文件；Secret 使用占位，其他值使用虚构示例域。
- [x] 示例至少覆盖改 namespace、域名、Ingress class、仅 newName 的镜像替换、同名 generator merge。
- [x] 说明 WEBUI_URL、OIDC 回调和 TLS 的联动；按需提供具体、经过渲染的 patch，而非只有注释占位。
- [x] 提供从示例复制到私有仓库的步骤，将 resources 改成实际公共仓库 URL + 已发布 tag/SHA。
- [x] 在临时副本注入秘密，部署前拒绝仍为占位/空值的启用功能必填项；不覆盖 Git 工作区的占位文件。
- [ ] 完成 apply、配置变更后的 rollout 和就绪检查；明确这一路径所需权限与执行方。
- [ ] 若实际部署由 Argo CD 等控制，先落实它可用的凭据来源与更新流程，不能用手工本地注入冒充 GitOps 闭环。

验收：公开示例可直接 build；私有环境在准备依赖与注入配置后通过运行检查。
私有仓库的访问/变更在后续实施时处理，本次不创建真实租户文件。

### Task 5：建立最小校验与回归用例

新增：`scripts/validate.sh`、`scripts/validate.py`、`scripts/render-private.py`、固定依赖和合同用例。
构建/试点合同检查与全仓公开扫描分开，后者为发布门槛，当前发现的旧文件问题不作隐藏豁免。

- [x] 固定一个独立 Kustomize 版本用于 CI；记录工具版本，其他部署工具仅在验证后声明兼容。
- [x] 明确枚举 `template/appname`、`addons/*`、`examples/overlays/*` 中有入口的目录，输出资源数量。
- [x] 商店合同校验针对登记应用及候选试点；旧 addon 仍做构建回归，公开前仍须完成全仓信息审查。
- [x] 源文件扫描覆盖 env、YAML、README、`.agents/skills/`、docs；渲染扫描解析 YAML，并在内存解码 Secret.data。
- [x] 验证目录引用、重复资源身份、镜像版本、关键资源数量/字段、generator/工作负载引用，不用 grep 命中几行代替正确性。
- [x] 正向用例验证 merge 覆盖与保留、镜像 tag 继承、namespace 及字符串联动、host/TLS patch。
- [x] 负向用例覆盖缺失 env 文件、未固定远程 ref、启用功能必填项仍占位、Secret 编码后含禁止值和失效 patch。
- [x] 区分 public 模式（允许声明的占位值）与 deploy 模式（启用功能的必填值必须完整）。日志只报位置/键名/规则，不打印数据值。
- [x] 新增 GitHub Actions 工作流；本地运行同等构建/测试，错误按规则脱敏，临时文件用私有权限并自动清理。
- [ ] 推送后确认 GitHub Actions 实际运行；在私有流水线验证生产配置。

验收：正向用例通过、负向用例确实失败，当前 5 个入口的渲染基线不发生意外变化。

### Task 6：运行验证、上架和版本发布

新增：`catalog.yaml`、`CHANGELOG.md`；按具体授权净化应用文档；更新规范入口引用。

- [ ] 在测试环境验证官方镜像拉取、UID/GID 和可写目录、启动及探针、数据库连接、文件上传/读取、模型调用；启用 OAuth 时验证登录。
- [ ] 验证仅更新 env 后，滚动更新确实使新 Pod 使用新配置；验证重建后需保留的数据仍可用。
- [ ] 将迁移后的私有 overlay 与旧入口做完整脱敏结构 diff，解释每项差异；不仅比较 host/image。
- [ ] 准备并验证部署入口切换，避免直接把在用的旧入口替换成占位 base；切换前确认数据备份和回退条件。
- [x] 新增空 catalog 与 Unreleased changelog，记录应用版本、默认行为变化及待验证的数据迁移条件。
- [ ] 实际运行和发布验收通过后，将应用加入 catalog 并登记正式模板版本。
- [ ] 在全部发布前检查通过的审查提交上创建并推送不可移动 tag；不将“每改一处就打 tag”作为规则。
- [ ] 发布后从干净临时目录用实际 URL + tag 构建 overlay，核对 tag 对应提交及资源结果；先标为发布候选，远程验证通过后再宣布可用。
- [ ] 远程验证失败时不挪动 tag，在发布说明标记不可用并修复后发布新版本。

验收：读者能从商店索引找到应用，用固定版本建立私有 overlay，完成安装与配置更新；公开仓库无真实私有配置。

## 6. 首期完成定义与后续扩展

仓库内实现已完成不等于首期可公开发布。首期完成需要同时满足：公共仓库可发布、一个应用可发现、base 和示例可渲染、私有配置可注入、
运行与配置更新已验证、版本可固定、升级/卸载的数据边界明确。仅文档齐套或 build 通过不算闭环。

后续以需求触发扩展：

| 实际需求 | 再增加的能力 |
| --- | --- |
| 第二个应用有相同可选功能 | 提取小型 component，保留单独测试与明确支持范围 |
| UI 需要读取应用配置项 | 从已稳定的输入文档提炼 schema，不提前设计通用配置引擎 |
| 受限网络无法访问公共 Git | vendor 固定提交并记录来源、许可证和更新 diff |
| 多环境反复复制公共差异 | 在私有仓库引入一层共享 overlay，避免预先堆叠公司/集群/地域层级 |
| GitOps 持续调谐密钥 | 选择已有 Secret 管理方案，定义资源 ownership 和更新方式 |
| 制作/升级步骤反复执行 | 按实际需要拆分 skill，统一引用现有 references 规范及根 scripts |
| argo-cd 等后续应用上架 | 单独盘点 files generator、CRD/ClusterRole 所有权、权限和升级行为 |

## 附录：本次核验记录与证据边界

2026-09-06 本机只读构建结果：

| 入口 | kustomize v5.0.0 | kubectl v1.26.1 / 内置 Kustomize v4.5.7 |
| --- | --- | --- |
| template/appname | 4 个资源 | 4 个资源 |
| addons/argo-cd | 48 个资源 | 48 个资源 |
| addons/argo-events | 17 个资源 | 17 个资源 |
| addons/argo-workflows | 26 个资源 | 26 个资源 |
| addons/open-webui | 9 个资源 | 9 个资源 |

使用临时的无真实值最小 base/overlay，在两套工具上均验证了：同名 ConfigMap/Secret generator
merge 覆盖与保留；仅 newName 时继承 base tag；namespace 修改资源命名空间及 Namespace 名称；
env URL 字符串保持原值；关闭 hash 时引用名称稳定。临时目录已自动清理。
评估阶段的检查没有验证远程 Git、集群安装、官方镜像运行或真实凭据注入。
本轮另增加了临时 Git 仓库固定 SHA 的读取和虚构凭据注入测试，仍不代替实际公共远程或集群验证。
原计划 `/tmp/store-test/` 的口头验证记录不作为新增验收证据；后续需提交可复跑用例。

技术依据：

- [Kustomize 官方用法](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/)：generator、images、patches 与 base/overlay。
- [Kustomize 远程构建说明](https://github.com/kubernetes-sigs/kustomize/blob/master/examples/remoteBuild.md)：远程 Git 子目录及 ref 格式。
- [Kubernetes ConfigMap 更新行为](https://kubernetes.io/docs/concepts/configuration/configmap/)：环境变量不会随 ConfigMap 更新自动刷新，需要替换 Pod。
- [Kustomize 配置生成示例](https://github.com/kubernetes-sigs/kustomize/blob/master/examples/configGeneration.md)：按 data key 合并及 hash 后缀更新机制。
