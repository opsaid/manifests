# Addon Store 仓库内执行记录

状态：本地实施完成，公开发布前置（全仓净化、历史改写、推送）已完成；集群验收与仓库可见性切换待完成。实施计划是进度入口，本文记录本次证据及后续推进。

## 已完成

- 规范迁入 `.agents/skills/addon-maintenance/references/addon-store.md`，新增短 SKILL.md，删除 spec 副本。
- 技能位于 `.agents/skills/`，Claude 技能入口为指向它的符号链接。AGENTS.md 保留共享规则，CLAUDE.md 仅导入 AGENTS.md。
- open-webui 仅修改入口和 configuration，功能资源及 addon README 均未改动。
- 提供完整虚构 overlay、应用输入说明、私有临时构建工具、固定版本校验器及 CI 工作流。
- catalog 保持空列表，changelogs/open-webui.md 使用 Unreleased，不伪造上架状态或发布 tag。

## 验证结果

- `scripts/validate.sh --app open-webui`：6 个入口通过（模板 4、argo-cd 48、argo-events 17、argo-workflows 26、base 9、overlay 9 个资源）。
- `python3 -m unittest discover -s scripts/tests -v`：18 项通过；含 merge、files 整键替换、namespace、TLS、固定 Git SHA、私有注入、输出权限及负向用例。
- `kubectl kustomize`（内置 Kustomize v4.5.7）：修改后的 base/overlay 均为 9 个资源。
- skill-creator `quick_validate.py`：通过；本次 Markdown 链接、代码块和空白检查通过。
- CI YAML 与 shell 语法通过，固定 Kustomize 官方 checksum 文件可读取；尚未执行 GitHub Actions 远程作业。
- 改动前后哈希核对：原有其他应用、功能清单及用户预先修改的模板文件未改变。
- 待批准的 README 补丁通过 `git apply --check`，尚未应用。

## 迁移差异

改动前后资源身份相同（9 个），以下只记录变化字段，不记录原环境值或 Secret 内容。
身份 UUID 的 labels/annotations 移除；域名恢复占位；Ingress class 从 base 移除；镜像改为官方地址。
配置改动包括证书校验、OAuth 默认关闭、端点中性化及增加稳定会话签名密钥，详情见 CHANGELOG/open-webui/CHANGELOG-v0.md。
其余资源、探针、权限和存储字段未发生变更，但官方镜像的运行兼容性仍需独立验证。

```text
Namespace/open-webui/metadata/annotations
Namespace/open-webui/metadata/labels/opsaid.net/pm2-uuid
ServiceAccount/open-webui-sa/metadata/annotations
ServiceAccount/open-webui-sa/metadata/labels/opsaid.net/pm2-uuid
ConfigMap/open-webui/data/ENABLE_FORWARD_USER_INFO_HEADERS
ConfigMap/open-webui/data/ENABLE_OAUTH_GROUP_CREATION
ConfigMap/open-webui/data/ENABLE_OAUTH_GROUP_MANAGEMENT
ConfigMap/open-webui/data/ENABLE_OAUTH_ROLE_MANAGEMENT
ConfigMap/open-webui/data/ENABLE_OAUTH_SIGNUP
ConfigMap/open-webui/data/ENABLE_OAUTH_TOKEN_EXCHANGE
ConfigMap/open-webui/data/OAUTH_ALLOWED_ROLES
ConfigMap/open-webui/data/OAUTH_CLIENT_ID
ConfigMap/open-webui/data/OAUTH_MERGE_ACCOUNTS_BY_EMAIL
ConfigMap/open-webui/data/OAUTH_PROVIDER_NAME
ConfigMap/open-webui/data/OPENID_PROVIDER_URL
ConfigMap/open-webui/data/OPENID_REDIRECT_URI
ConfigMap/open-webui/data/OTEL_EXPORTER_OTLP_ENDPOINT
ConfigMap/open-webui/data/OTEL_LOGS_EXPORTER_OTLP_ENDPOINT
ConfigMap/open-webui/data/OTEL_METRICS_EXPORTER_OTLP_ENDPOINT
ConfigMap/open-webui/data/REQUESTS_VERIFY
ConfigMap/open-webui/data/S3_BUCKET_NAME
ConfigMap/open-webui/data/WEBUI_URL
ConfigMap/open-webui/metadata/annotations
ConfigMap/open-webui/metadata/labels/opsaid.net/pm2-uuid
Secret/open-webui/data/DATABASE_URL
Secret/open-webui/data/WEBUI_SECRET_KEY
Secret/open-webui/metadata/annotations
Secret/open-webui/metadata/labels/opsaid.net/pm2-uuid
Service/open-webui/metadata/annotations
Service/open-webui/metadata/labels/opsaid.net/pm2-uuid
Service/open-webui-redis/metadata/annotations
Service/open-webui-redis/metadata/labels/opsaid.net/pm2-uuid
Deployment/open-webui/metadata/annotations
Deployment/open-webui/metadata/labels/opsaid.net/pm2-uuid
Deployment/open-webui/spec/template/metadata/annotations
Deployment/open-webui/spec/template/metadata/labels/opsaid.net/pm2-uuid
Deployment/open-webui/spec/template/spec/containers/0/image
Deployment/open-webui-redis/metadata/annotations
Deployment/open-webui-redis/metadata/labels/opsaid.net/pm2-uuid
Deployment/open-webui-redis/spec/template/metadata/annotations
Deployment/open-webui-redis/spec/template/metadata/labels/opsaid.net/pm2-uuid
Deployment/open-webui-redis/spec/template/spec/containers/0/image
Ingress/open-webui/metadata/annotations
Ingress/open-webui/metadata/labels/opsaid.net/pm2-uuid
Ingress/open-webui/spec/ingressClassName
Ingress/open-webui/spec/rules/0/host
```

## 尚未完成的门槛

> 注：本节为实施当时的快照。工作区环境值、旧应用中性化决策、open-webui README 清理及
> 提交推送已由下方「后续推进」在同日解决，其余仍为实际待办。

- 未获得私有配置仓库、测试集群 context/namespace 和可用密钥来源，因此未执行真实 apply、rollout、登录或数据恢复测试。
- 全仓工作区扫描发现 13 处已知环境值，分布在旧 addon、模板及只读 README；此计数不是所有敏感信息的完整清单。
- 对当前本地可见的全部 Git 提交执行已知值模式搜索，确认 3 个提交（模板重构、argo-cd 与
  argo-events 引入时）存在匹配。该搜索只输出提交和路径，不输出内容；没有声称已完成凭据全量
  或远端不可见历史审查。
- 全仓旧应用中性化和历史处理涉及其他应用/文件，需单独确定公共发布使用本仓库还是净化快照仓库。
- open-webui README 需要清理 4 处环境信息并同步已过时的接入/default 说明。已准备私有临时补丁，未修改只读文件。
  根 AGENTS.md 明确要求只读路径先获维护者同意；当前执行授权未逐项确认这些只读清理内容。
- 未创建或推送提交/tag，未切换部署入口。CI 已落盘，本地执行同等 Python/构建检查，GitHub Actions 实际运行仍待推送后确认。

## 后续推进（2026-09-06 同日）

- 旧 addon（argo-cd、argo-events、argo-workflows）、模板及 open-webui README 完成最小中性化；
  前述 13 处工作区发现与黑名单补充后的额外命中已全部清除，`--audit-public` 为 0 发现。
- 组织专属私有值模式从校验器代码外置到不入库的 `scripts/private-patterns.local`
  （占位模板见 `private-patterns.example`），避免公开仓库经检测器正则再泄露被净化的标识；
  合同测试增至 21 项。
- Git 历史经 git-filter-repo 两次 replace-text 改写（域名/内网地址/registry 一轮、组织标识一轮），
  全历史组织专属标识扫描零残留；剩余命中仅为校验器通用模式与测试夹具（RFC1918）。
- origin 重建并强推 main；仓库可见性切换与 GitHub Actions 首次远程运行待确认。
- 仍未完成：真实集群运行验收、发布 tag 与 catalog 登记、私有环境仓库建设；pre-rewrite 备份
  bundle 含原始真实值，仅存于本机临时目录，确认公开状态后由维护者删除或转存离线。

## 后续推进（2026-09-07 整改）

- 删除 `addons/argo-workflows/install.yaml`：该文件未被任何 kustomization 引用（死文件），
  且残留真实内网 S3 端点与桶名——该值不在已知模式黑名单内，此前 `--audit-public` 的 0 发现
  未覆盖它（manual_review=REQUIRED 的真实案例）。删除后渲染资源数不变。
- 第三轮历史改写（同日）：经 git-filter-repo replace-text 将历史中该内网端点替换为保留域
  占位（维护者本轮仅授权该端点，旧内部命名按决定保留在历史中），origin 重建并强推 main。
  全历史复扫该端点零残留；六个入口构建、合同测试与公开审计结果不变。改写前备份
  bundle 位于本机 /tmp/manifests-pre-rewrite-20260907.bundle，与 20260906 备份一并待
  确认公开状态后删除；其余机器上的旧克隆需重新克隆，不能继续在被改写历史上开发。
- 模板占位值中性化：namespace 与应用名统一为 `appname` / `demo-v1`，移除部署身份 UUID 标签
  （与 open-webui 中性化口径一致），修正示例 env 拼写并补齐空示例配置；argo-cd README 制作
  命令同步文件名并修正失效路径。渲染仍为 4 个资源。
- `private-patterns.local` 补充内网子域、旧环境命名与身份标签值的模式防止回归（仅本地生效，
  不入库）。
- 维护者明确公开口径：组织公共镜像仓库（registry.cn-hangzhou.aliyuncs.com/opsaid）与应用
  namespace（open-webui）属公开标识，可出现在公共内容中；私密配置与主机 IP 仍是禁入项。
  据此 open-webui 公共示例改用真实 registry 与真实 namespace（仅换 newName 继承 base tag，
  REDIS_URL 随 namespace 与 base 一致回归继承），校验器移除内置的公共云 registry 私有模式
  （RFC1918 内网地址模式保留），规范、接入说明、示例 README、patterns 注释与合同测试同步。
- 示例 overlay 精简（渲染等价性逐项验证）：删除与 base 重复的镜像 newTag 与 generator
  options（merge 时继承 base）；按维护者决定移除资源 patch 中的
  `opsaid.net/config-revision` 注解，配置变更传播依赖部署流程既有的 rollout restart，
  不再要求人工维护修订标识。namespace 保留显式设置：kustomize 只为当前层级生成的资源
  打 namespace，overlay 本地生成的资源（如 TLS Secret）依赖该字段落位。
- 新增 TLS 证书例外口径（维护者决定）：`tls.crt`/`tls.key` 允许提交在 overlay
  `configuration/secrets/` 下经 files 型 secretGenerator 交付，示例仅保留默认关闭的注释配置。
  校验器同步：`kubernetes.io/tls` Secret 的证书材料不做占位符/凭据签名检查（仍要求非空、
  禁私网值），open-webui 资源合同接受可选第 10 个资源 `open-webui-tls`（类型与键名必须正确，
  负向用例验证）；合同测试增至 22 项。AGENTS.md、规范 §1/§5、接入说明与示例 README 同步。
- 参照 Kubernetes CHANGELOG 目录规范建设 `CHANGELOG/`（目录大小写一并对齐）：每应用一个子目录，每条版本线一个
  `CHANGELOG-v<major>.md`（新版本在前，`git mv` 保留历史），条目按 Changes by Kind 分类
  （API Change/Feature/Bug or Regression/Deprecation/Dependencies/Other）并附提交引用；
  `Unreleased` 段承载未发布条目。规范 §6 更新为该结构的权威描述，`CHANGELOG/README.md`
  作纯索引并指向规范。
- argo-cd kustomization 移除无引用的 dex 与 ECR redis 镜像条目，前后渲染哈希一致。
- 移除被追踪的 .DS_Store 并补 .gitignore；CI 新增 `--audit-public` 步骤（不含组织专属模式
  与 Git 历史）；修正根 README、应用接入说明与公共规范中停留在净化完成前的过时表述。
- 文档目录按应用重组（维护者指示）：`docs/apps/open-webui.md` 经 `git mv` 迁至
  `docs/open-webui/README.md`（后续应用各自建 `docs/<app>/` 目录，专项文档同目录）；
  新增 `docs/open-webui/postgres.md` 操作手册（建库与账号、pgvector 扩展、连接串对接、
  网络访问、备份与升级、验收清单，全部使用占位值），接入说明顶部链接与依赖表指向该文档。
  根 README、catalog.yaml、addon README、规范 §2/§3、SKILL.md、示例 README 与计划文档中的
  `docs/apps` 路径引用全部同步；验证（--app 6 入口、22 项合同测试、--audit-public 0 发现）通过。
