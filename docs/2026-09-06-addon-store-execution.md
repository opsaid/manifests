# Addon Store 仓库内执行记录

状态：本地实施完成；公开发布和真实环境验收未完成。实施计划是进度入口，本文记录本次证据。

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
配置改动包括证书校验、OAuth 默认关闭、端点中性化及增加稳定会话签名密钥，详情见 changelogs/open-webui.md。
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

- 未获得私有配置仓库、测试集群 context/namespace 和可用密钥来源，因此未执行真实 apply、rollout、登录或数据恢复测试。
- 全仓工作区扫描发现 13 处已知环境值，分布在旧 addon、模板及只读 README；此计数不是所有敏感信息的完整清单。
- 对当前本地可见的全部 Git 提交执行已知值模式搜索，确认 3 个提交（模板重构、argo-cd 与
  argo-events 引入时）存在匹配。该搜索只输出提交和路径，不输出内容；没有声称已完成凭据全量
  或远端不可见历史审查。
- 全仓旧应用中性化和历史处理涉及其他应用/文件，需单独确定公共发布使用本仓库还是净化快照仓库。
- open-webui README 需要清理 4 处环境信息并同步已过时的接入/default 说明。已准备私有临时补丁，未修改只读文件。
  根 AGENTS.md 明确要求只读路径先获维护者同意；当前执行授权未逐项确认这些只读清理内容。
- 未创建或推送提交/tag，未切换部署入口。CI 已落盘，本地执行同等 Python/构建检查，GitHub Actions 实际运行仍待推送后确认。
