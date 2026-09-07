# Open WebUI 接入说明

状态：本地试点，尚未完成目标集群运行验收和商店版本发布；全仓净化与历史改写已完成，
人工公开复核与仓库可见性切换仍待完成。`catalog.yaml` 暂无上架条目，不要将本说明中的版本号视为已有商店 tag。

维护入口：[addon-maintenance](../../../.agents/skills/addon-maintenance/SKILL.md)。
公共合同：[Addon Store 规范](../../spec/addon-store.md)。
完整示例：[examples/overlays/open-webui](../../../examples/overlays/open-webui/kustomization.yaml)。
依赖操作：[PostgreSQL 准备](./postgres.md)（建库、账号、pgvector 扩展、备份与验收）。

## 来源与实测范围

资源整理依据为上游 chart `open-webui-16.1.0`（沿用现有清单记录）。应用镜像由
[base 入口](../../../addons/open-webui/kustomization.yaml) 固定为 Open WebUI `v0.11.3` 和
Redis `7.4.2-alpine3.21`；版本以入口为权威来源，文档不负责镜像替换。
本次从私有镜像地址恢复官方地址，不能假设两个地址下的内容完全相同。

目前仅验证独立 Kustomize v5.0.0 的构建和合同用例；kubectl 内置 v4.5.7 另做本地渲染兼容检查。
Kubernetes 版本、CPU 架构和运行环境尚未实测，不声明支持范围。官方镜像默认以 root 构建，
启动时会改写自带静态资源，镜像内静态目录按“属组 0 + g=u”交付（任意 UID 需属于 GID 0）。
实测原 GID 1001 触发启动 EACCES 后，base 改为 `runAsUser: 1001` + `runAsGroup: 0`，
保持非 root 与最低能力集，不放宽到 root；集群重启复验与 `HOME=/root` 缓存写入行为仍待验收。
依据：[上游 Dockerfile](https://github.com/open-webui/open-webui/blob/v0.11.3/Dockerfile)。

上游许可证见 [Open WebUI LICENSE](https://github.com/open-webui/open-webui/blob/v0.11.3/LICENSE)。
本项目不替换上游品牌；公开分发前需结合实际用途核对其归属和品牌要求，并核对 chart/Redis 各自许可证。
此处记录来源，不宣称已完成再分发审查。

## 安装前提和资源归属

此试点支持外部 PostgreSQL + pgvector、S3、OpenAI 兼容 API、内置 Redis 的组合；
不是可以任意切换所有存储/模型后端的通用包。

| 依赖 | 准备方与条件 |
| --- | --- |
| [PostgreSQL](./postgres.md) | 平台提供库、账号与网络访问，准备 vector 扩展；应用启动会涉及数据迁移，升级前备份 |
| S3 | 平台准备桶、区域、访问权限和凭据；自建兼容服务额外指定 endpoint |
| 模型 API | 提供可用的 API 基址、凭据和 embedding 模型；默认使用外部 embedding，不下载本地模型 |
| Ingress Controller | 平台安装并提供 ingressClassName；base 未选择 controller |
| TLS Secret | 启用 TLS 时二选一：平台在应用 namespace 预置，或 overlay 用 files 型 secretGenerator 从 `configuration/secrets/` 证书文件生成（示例默认关闭）；两个来源不得并存 |
| 官方或镜像仓库 | 执行方确认镜像可拉取、目标架构匹配；镜像仓库应已同步相同版本 |
| OIDC / OTEL | 可选；启用前准备服务端配置、回调和网络访问 |

共 9 个资源：Namespace、ServiceAccount、ConfigMap、Secret、两个 Service、一个 Ingress、两个 Deployment。
应用工作负载不访问 Kubernetes API。首期独占 namespace，不支持同 namespace 多实例；
不能对共享 namespace 执行整包删除或启用无审查的 prune。数据库、桶、TLS Secret 和集群控制器均由平台管理。

## 输入和默认行为

非凭据值在 overlay `configuration/configmaps/open-webui.env`；凭据由
`configuration/secrets/open-webui.env` 的同名 generator 合并。未列出的键继承 base，
具体调优默认值以 [base env](../../../addons/open-webui/configuration/configmaps/open-webui.env) 为准。
下表中的运行参数经 env/envFrom 注入，更新后都需要替换 Pod 才能保证生效。

| 输入 | 位置 | 必填条件 / 默认行为 |
| --- | --- | --- |
| namespace | kustomization | 默认 open-webui，示例显式同名（overlay 本地生成的资源依赖它落位）；改名时必须同步 REDIS_URL |
| Ingress host/class/TLS | kustomization patches | 部署必须指定实际域名和 class；TLS hosts 与 WEBUI_URL 一致 |
| WEBUI_URL | ConfigMap | 部署必填，包含 scheme；base 是占位示例域 |
| DATABASE_URL | Secret | 必填 PostgreSQL 连接串，包含凭据，不得进入 ConfigMap |
| WEBUI_SECRET_KEY | Secret | 必填，部署策略要求至少 32 字符随机值，所有 worker/Pod 共享且稳定保存 |
| OPENAI_API_BASE_URL / OPENAI_API_KEY | ConfigMap / Secret | 该试点必填；默认公共 API 基址，key 是占位；当前检查不覆盖无鉴权 API 变体 |
| RAG_EMBEDDING_ENGINE / MODEL | ConfigMap | 默认 openai / text-embedding-3-small；更换模型要核对向量维度与已有数据 |
| STORAGE_PROVIDER | ConfigMap | 首期固定 s3，切换 local 会改变持久化需求，不在当前合同检查范围 |
| S3_BUCKET_NAME / S3_REGION_NAME | ConfigMap | 必填；base 不填写实际桶和区域 |
| S3_ENDPOINT_URL | ConfigMap | 自建 S3 必填；AWS 原生可省略，不用空字符串冒充省略 |
| S3_KEY_PREFIX | ConfigMap | 可选，默认空 |
| S3_ACCESS_KEY_ID / S3_SECRET_ACCESS_KEY | Secret | 当前凭据模式必填；工作负载身份认证需另验证后扩展检查 |
| REDIS_URL | ConfigMap | 必须指向包内 Redis，使用当前 namespace 的 FQDN 或经过验证的短名；外部 Redis 另行适配 |
| OAUTH_CLIENT_ID / OPENID_PROVIDER_URL | ConfigMap | 默认空，OIDC 未注册；任一填写后要求整组输入完整 |
| OAUTH_CLIENT_SECRET | Secret | 启用 OIDC 时必填；此试点未覆盖 public client/PKCE 变体 |
| OPENID_REDIRECT_URI | ConfigMap | 启用 OIDC 时必须等于 WEBUI_URL + /oauth/oidc/callback，并在身份提供方登记 |
| OAUTH_PROVIDER_NAME / OAUTH_SCOPES | ConfigMap | 默认 OpenID / openid email profile |
| ENABLE_OAUTH_SIGNUP、TOKEN_EXCHANGE、ROLE_MANAGEMENT、GROUP_MANAGEMENT、GROUP_CREATION | ConfigMap | 对应完整键名以 base 为准，默认均 False，启用前核对身份提供方语义 |
| OAUTH_MERGE_ACCOUNTS_BY_EMAIL / OAUTH_AUTO_REDIRECT | ConfigMap | 默认 False；不继承原私有环境的账号关联策略 |
| ENABLE_OTEL / TRACES / METRICS / LOGS | ConfigMap | 对应 ENABLE_OTEL_*，默认关闭；启用时对应 OTLP endpoint 必填 |
| REQUESTS_VERIFY | ConfigMap | 默认 True；私有 CA 应提供受信任证书，具体挂载方案需单独评审 |
| ENABLE_FORWARD_USER_INFO_HEADERS | ConfigMap | 默认 False；按实际模型服务接入策略调整 |
| ENABLE_PERSISTENT_CONFIG | ConfigMap | 默认 False，配置以 env 为主；不能据此推断应用数据没有持久化需求 |
| replicas、资源请求/限制、images | kustomization | 继承 base；资源 patch 按容器名合并，镜像仅换 newName 时继承 tag |

OIDC 注册条件与会话密钥依据 [上游 config.py](https://github.com/open-webui/open-webui/blob/v0.11.3/backend/open_webui/config.py)
和 [env.py](https://github.com/open-webui/open-webui/blob/v0.11.3/backend/open_webui/env.py)。
输入校验不会测试连接可达、凭据正确性或权限，部署方必须实际验证这些条件。

## 从公开示例接入私有仓库

1. 将整个 `examples/overlays/open-webui/` 复制到私有仓库，例如 `environments/test/open-webui/`。
2. 将 resources 的本地路径替换为实际公共仓库固定 tag/SHA 的引用。格式：
   `https://github.com/opsaid/manifests.git//addons/open-webui?ref=<已发布tag或完整SHA>`。
   当前尚无商店发布版本；不能照抄不存在的 tag。
3. 按需修改 namespace、域名、Ingress class/TLS、非凭据配置；示例镜像仓库为组织公共仓库
   （registry.cn-hangzhou.aliyuncs.com/opsaid），确认已同步所需版本后可直接保留。
4. 由秘密存储在 Git 工作区外生成权限为 `0600` 的 dotenv 文件，包含表中的必填 Secret 键，
   OIDC 启用时再加 OAUTH_CLIENT_SECRET。不要把秘密通过命令行参数传递，不要启用 shell tracing。
5. 在具有固定 Kustomize、Git 和 PyYAML 的受控执行环境运行下面的构建及部署步骤。

以下仓库工具命令从 manifests 仓库根目录执行。独立 Kustomize 版本见 `scripts/kustomize-version.txt`，
Python 3.9+，`python3 -m pip install -r scripts/requirements.txt`。

```bash
# 先由执行方设置这些变量：
# PRIVATE_OVERLAY_DIR：私有 overlay 目录（远程 base 固定 ref）
# PRIVATE_SECRET_ENV：秘密存储生成的 dotenv 文件，权限 0600
# TARGET_CONTEXT / TARGET_NAMESPACE：已确认可操作的目标
(
  set -euo pipefail
  : "${PRIVATE_OVERLAY_DIR:?}" "${PRIVATE_SECRET_ENV:?}"
  : "${TARGET_CONTEXT:?}" "${TARGET_NAMESPACE:?}"
  umask 077
  render_dir="$(mktemp -d)"
  trap 'rm -rf "$render_dir"' EXIT
  python3 scripts/render-private.py \
    --overlay "$PRIVATE_OVERLAY_DIR" \
    --secrets-file "$PRIVATE_SECRET_ENV" \
    --output "$render_dir/manifests.yaml"

  # 在受控环境完成脱敏结构 diff，确认 namespace 与实际目标一致后再应用。
  kubectl --context "$TARGET_CONTEXT" apply -f "$render_dir/manifests.yaml"
  # 稳定 generator 名下，单独更改 env 不会自动滚动 Pod。
  kubectl --context "$TARGET_CONTEXT" -n "$TARGET_NAMESPACE" rollout restart deployment/open-webui
  kubectl --context "$TARGET_CONTEXT" -n "$TARGET_NAMESPACE" rollout status deployment/open-webui --timeout=300s
  kubectl --context "$TARGET_CONTEXT" -n "$TARGET_NAMESPACE" rollout status deployment/redis --timeout=300s
)
```

工具只构建与校验，不执行 apply；拒绝浮动 ref、缺失/占位必填项、覆盖已有输出和写入 Git 目录。
原 overlay 保持占位值，输出文件为 `0600`。执行方负责清理秘密存储产生的输入文件。
不要在普通日志中使用 `kubectl diff` 打印含 Secret 的完整差异。

该流程不等同于 Argo CD 接入。持续调谐场景必须落实 GitOps 渲染端可用的解密/Secret 来源，
并移除会与外部 Secret 控制器争夺同名对象的 generator；在完成适配前不声明支持。

## 数据、升级与发布验收

主应用 `/app/backend/data` 与 Redis `/data` 都是 emptyDir。PostgreSQL、S3 和固定签名密钥由
平台保留；本地缓存、中转文件、未外置的数据会随 Pod 删除。尚未运行验证，不宣称“完全无状态”。
需测试上传后重建再读取、会话行为和 Redis 重建影响；新增 PVC 或变更功能资源须按仓库规则处理。

旧入口切换前，比较资源身份、镜像内容、env 键、权限/UID、探针、存储与 namespace。
本次明确变化见 [CHANGELOG/open-webui/CHANGELOG-v0.md](../../../CHANGELOG/open-webui/CHANGELOG-v0.md)：尤其是官方镜像、证书校验、OIDC 默认行为和新签名密钥。
仅修改 Git ref 不能恢复数据库版本，备份和迁移兼容性须先验证。

上架前完成：目标架构镜像拉取、非 root 启动/写目录、探针、数据库/pgvector、上传与读取、模型调用，
以及所启用的 OIDC/OTEL；仅修改 env 后滚动更新，确认新值生效；验证需要保留的数据不丢失。
卸载前先确认 namespace 没有其他应用/TLS 等平台资源，数据库和对象存储不随包自动删除。

## 校验命令和边界

```bash
scripts/validate.sh --app open-webui
python3 -m unittest discover -s scripts/tests -v
scripts/validate.sh --audit-public
```

前两项验证构建与试点合同。最后一项扫描整个工作区：通用模式（内网地址等）内置于
脚本，组织专属模式由不入库的 `scripts/private-patterns.local` 提供（从 `private-patterns.example`
复制填写），缺失时该部分检查不生效。结果仅输出文件/行/规则，不输出值。它没有扫描 Git 历史，
也不是完整凭据识别器，公开前还需要人工审查与全历史扫描。
`--deploy <overlay>` 用于已在受控临时副本填好配置的部署输入检查，不访问集群。
`--local-test` 只允许本地合同测试使用本地 base，不能作为正式发布验证。
