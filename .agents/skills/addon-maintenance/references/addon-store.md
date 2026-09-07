# Addon Store 公共规范

状态：首期试点规范；本地工具和 open-webui overlay 已落实，运行及发布门槛尚未完成。
适用于准备上架的应用，当前不声明全部 addon 已符合。
本文中的“必须”表示上架或部署验收条件；不会覆盖 [AGENTS.md](../../../../AGENTS.md) 的修改权限约束。

## 1. 范围与边界

应用商店首期提供：应用索引、版本化的 Kustomize base、安装输入说明、完整 overlay 示例及校验。
安装动作由部署工具完成。商店不负责租户账号、业务授权、集群安全隔离或依赖自动编排。

- 公共仓库的 addon、template、example、文档和可访问历史中不得包含真实租户私有配置或凭据。
  公共上游域名、组织公共镜像仓库、namespace 等项目身份不是租户秘密，可出现在公共内容中；
  其余环境标识使用 `example.com` 等保留示例域和明确占位符。
- 真实域名、内网地址等非凭据环境值放在独立私有仓库；密码、Token、带凭据的
  URL 在公共及私有 Git 中均不得明文提交，Secret.data 的 Base64 编码也不视为加密保护。
  TLS 证书与私钥文件是唯一例外（见第 5 节）。
- 引用 `addons/<app>` 子目录、按应用打 tag、将文件放到 `secrets/` 都不提供 Git 访问隔离。
- 存量 addon（argo-cd、argo-events、argo-workflows）按商店标准分批迁移，迁移完成前不登记上架；
  其最小中性化与历史改写已完成，公开内容与可访问历史仍须持续满足上一条的真实值禁入要求。

## 2. 应用包与商店索引

应用 ID 使用稳定的目录名 `addons/<id>/`。包保留当前模板分类，环境差异集中于
`kustomization.yaml` 与 `configuration/`；功能资源不复制到租户仓库再各自维护。
base 必须可独立渲染，不保证占位配置可以启动。存在依赖的应用必须附安装前提。

应用版本发布验收通过后，在根 `catalog.yaml` 登记最小条目，示意结构如下：

```yaml
apiVersion: opsaid.net/addon-store/v1alpha1
kind: AddonCatalog
items:
  - id: open-webui
    name: Open WebUI
    description: 基于外部数据库和对象存储的对话界面
    path: addons/open-webui
    docs: docs/apps/open-webui.md
    upstream: https://github.com/open-webui/open-webui
```

这是仓库元数据，不能提交给 Kubernetes API，也不引入 CRD。
`id` 必须唯一，`path` 与 `docs` 必须存在且位于仓库内；未完成验收的目录不列入索引。
应用 ID 一旦发布应保持稳定；版本来自 `<id>-v*` 发布 tag 和 `changelogs/<id>.md`，镜像版本来自对应 ref
中的 kustomization。不重复维护 `latestVersion`、镜像版本或安装参数的多份数据。
`v1alpha1` 仅标识索引格式；将来已有消费者后，破坏格式时才另立版本。

## 3. 应用接入文档

每个登记应用必须提供 `docs/apps/<id>.md`，至少包含以下内容：

| 项目 | 必须说明 |
| --- | --- |
| 来源 | 上游仓库、chart/生成依据版本、许可证及再分发注意事项 |
| 支持环境 | 实测的 Kustomize、Kubernetes、架构；未测试的范围不承诺 |
| 安装依赖 | 数据库/扩展、对象存储、Ingress Controller、CRD、API 服务及准备责任人 |
| 输入表 | 键、位置、默认值、必填或条件必填、敏感性；URL/namespace/TLS 等联动 |
| 可变接口 | generator、资源及容器逻辑名；支持的域名、镜像、namespace、副本和资源调整 |
| 状态与运维 | 数据位置、备份、配置更新方式、健康检查、安装和卸载影响 |
| 升级 | 配置迁移、应用/数据库兼容性、回退前提和已知限制 |

应用特例写在应用文档，不扩张为所有应用必须实现的通用配置项。
不将 OAuth 合并账号、放宽角色、关闭 TLS 校验等租户策略直接作为通用默认。
更换官方/镜像仓库地址前，必须确认镜像内容与所需权限、目录和功能的兼容性。

## 4. Overlay 接口

私有 overlay 最小结构为 `kustomization.yaml` + `configuration/`；公共完整示例位于
`examples/overlays/<id>/`，包含所有被引用文件，使用占位凭据与虚构域名/主机；
组织公共镜像仓库、namespace 等公开标识可直接使用真实值。
示例的差异键集合对照真实租户的实际差异维护，保证覆盖常见接入差异；除已公开组织标识外数值保持虚构。

### 4.1 Base 引用和镜像

- 公共示例为测试当前代码可引用本地 base；真实环境引用必须固定发布 tag 或完整 commit SHA，
  不允许省略 ref 或使用浮动分支。引用格式示意：
  `https://github.com/opsaid/manifests.git//addons/open-webui?ref=<已发布tag或完整SHA>`。
- 消费者必须能访问 Git；远程构建以真实执行环境验证，不能将本地路径构建视为远程验证。
- 镜像在 base `images` 中固定 `newTag`，或按已验证需求使用 digest；功能清单保留官方镜像名。
- overlay 的 `images.name` 匹配 base 声明的镜像。仅换 registry 时可只写 `newName` 并验证
  渲染结果继承 base tag；此约定不自动推广到多层重命名或 digest 覆盖场景。
- 私有镜像必须已提供兼容内容；改变应用版本需显式覆盖版本并由私有 CI 验证，不再声称等同商店测试版本。

### 4.2 ConfigMap 和 Secret

- 对 `envs:`，使用相同 generator 逻辑名与匹配的资源身份，并设置 `behavior: merge`；只写差异键。
  修改 namespace 的示例必须验证最终资源及引用，不能仅凭同名假设任意显式 namespace 都能合并。
- 合并粒度是 ConfigMap/Secret 的 `data` 键。对于 `files:`，整个文件通常对应一个 data key，
  不会递归合并该文件内部的 YAML/JSON；后续 argo-cd 接入必须单独设计并验证。
- 省略 overlay 键会继承 base；空字符串会覆盖值，不能代替删除。删除键需明确 patch 或完整
  replace，并验证未丢失其他必需键。不建立通用“删除语法”。
- namespace transformer 不会重写 env 内 URL 字符串。包含 namespace 的连接地址必须联动覆盖；
  同 namespace 服务可以使用经过运行验证的短 Service DNS 名减少联动。
- 敏感键只由 Secret 来源提供，不在 ConfigMap 中再定义同名键来依赖 envFrom 顺序解决冲突。

### 4.3 Patches 与资源归属

- base 可以有与所有用户相关的通用适配 patches；环境域名、TLS、资源需求等放 overlay。
- patch 尽量按资源名、容器名定位；能按名称合并的列表不依赖数字下标。必须使用 JSON Pointer
  数字下标时，文档声明目标结构，测试验证命中对象和值；仅 build 成功不能证明改对了对象。
- Ingress host、TLS hosts、WEBUI_URL、OIDC 回调等相关输入必须一致；Ingress class 由环境选择。
- 首期一个应用对应一个专用 namespace。Namespace 若由 base 创建，须说明部署工具的 prune/卸载行为；
  namespace 共用、同 namespace 多实例不在默认支持范围。
- CRD、ClusterRole、Ingress Controller 等共享集群能力需说明归属；应用不能默认接管或删除平台资源。
  需要新功能资源时优先通过维护者更新公共包，仍按仓库规则审批只读路径变更。

## 5. 私有配置交付和配置更新

首期采用不依赖额外控制器的交付方式：私有仓库跟踪非凭据配置与 Secret 占位样例，部署执行方
在权限受控的临时副本中，用既有秘密存储提供的值填充 generator 输入，完成校验、构建、应用后清理。
禁止把真实值写回被 Git 跟踪的源文件；禁止将含 Secret 的渲染 YAML 作为普通 CI 日志/制品上传。
TLS 证书与私钥文件是唯一例外：允许提交在 overlay 的 `configuration/secrets/` 下，用 files 型
secretGenerator（`type: kubernetes.io/tls`）交付；此时同名 Secret 不得再由平台或其他来源并行
管理，公共仓库示例只保留默认关闭的注释配置，不放真实证书。

公共 build 允许约定占位符；真实 deploy 必须检查启用功能的必填值不是缺失、空值或占位值。
禁用功能的占位符不应导致无意义的部署失败，必填条件来自应用输入表。

使用 Argo CD 等持续调谐工具时，必须明确它如何取得 Secret：例如受控的解密插件或外部 Secret
控制器。选择一种适配并验证后再声明支持；Secret 必须只有一个管理来源，不能同时由占位 generator
和外部控制器争夺同名对象。本地临时 env 文件不会自动传递到 GitOps 渲染端。

现有模板使用 `disableNameSuffixHash: true`，首期为避免扩大变更继续保留。
通过 env/envFrom 注入的配置不会在 ConfigMap 更新后自动刷新现有进程；部署执行方必须在配置变化后
触发相关工作负载滚动更新并等待就绪。GitOps 可通过显式配置修订注解更新 Pod template；具体方式写入
应用部署说明，修订标识不得包含秘密。不能以 Secret/ConfigMap apply 成功代替配置生效验收。
此更新行为见 [Kubernetes ConfigMap 文档](https://kubernetes.io/docs/concepts/configuration/configmap/)。

未来若启用 generator hash，必须一起验证资源引用、滚动更新和旧配置清理，不在首期混用两套默认机制。

## 6. 发布、升级和回退

- 模板版本采用 `<id>-v<semver>`，与应用镜像版本分开。Git tag 指向整个仓库提交，命名粒度不是内容隔离。
- 发布 tag 不可移动、复用或覆盖；仓库侧保护该约定。需要更强固定性时使用完整 commit SHA。
- 1.x 起，不兼容修改 generator/资源名、受支持 patch 目标、配置语义或运行前提须升 major；
  兼容的新能力升 minor，兼容修复升 patch。镜像升级按实际影响分类，不能统一当成 minor。
- 0.x 阶段仍必须标注破坏性变更、升 minor 并提供迁移说明，不利用“未到 1.0”省略兼容性评估。
- `changelogs/<id>.md` 每次发布记录模板版本、应用版本、重要默认值变化、输入变化、数据迁移和已验证环境。
- 发布前通过本地/CI 合同与运行检查，发布后用实际远程 ref 从干净目录复验；未完成远程复验不宣布可用。
- 升级在私有仓库修改 ref，执行输入校验、脱敏渲染 diff、必要备份与运行检查，再部署。
  回退 ref 只回退期望清单，不能撤销数据库迁移；必须先确认数据向后兼容或有可执行恢复方案。

远程 ref 格式依据 [Kustomize 远程构建说明](https://github.com/kubernetes-sigs/kustomize/blob/master/examples/remoteBuild.md)。

## 7. 验收分层

| 层次 | 通过条件 | 不能据此声称 |
| --- | --- | --- |
| 公共包 | base/完整示例可渲染；结构及接口用例正确；公开信息检查通过 | 真实配置完整或应用已经启动 |
| 私有配置 | 真实依赖和输入就绪；必填无占位；版本固定；diff 已审查 | 镜像、数据访问和登录路径已运行验证 |
| 可安装发布 | 目标环境启动、健康、关键功能、配置更新及数据边界验证通过 | 任意集群或未声明配置均受支持 |

CI 必须固定构建工具版本，并校验源文件与解析后的渲染结果。Secret.data 在内存解码检查，
只输出路径/对象/键名/规则；已知值黑名单仅作补充，不证明不存在其他秘密或环境信息。
公开审查需覆盖计划、README、其他 addon 和可访问历史，不能仅对已登记应用执行构建扫描。

合同用例至少包含：env merge 覆盖和保留、files 按 key 替换（使用时）、镜像替换保留版本、
namespace/连接字符串联动、patch 目标、关键资源身份与引用；同时验证错误配置确实失败。
不同工具的兼容范围必须来自实际验证；本地可用的 kubectl 不自动成为 CI 标准。

规范对应的实施顺序与当前证据见 [实施计划](../../../../docs/2026-09-06-addon-store-plan.md)。
