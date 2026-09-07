<!-- 本文件遵循 CHANGELOG/README.md 索引与公共规范 §6 的结构约定，覆盖 open-webui v0 版本线；
新版本段落置于文件顶部，发布时将 Unreleased 改为版本头并补齐发布元信息。 -->

# Unreleased

发布元信息（发布时补齐）：

- 模板版本：待定（首个商店发布 tag）
- 应用版本：Open WebUI v0.11.3、Redis 7.4.2-alpine3.21，以 [base 入口](../../addons/open-webui/kustomization.yaml)为权威来源
- 已验证环境：独立 Kustomize v5.0.0 渲染与合同用例通过；目标集群运行验收未完成

## Changelog since 初始引入

## Changes by Kind

### API Change

- 采用公共 Kustomize base + 私有 overlay 架构；公共规范合并至 addon-maintenance 技能。
  ([8aeb3ce](https://github.com/opsaid/manifests/commit/8aeb3ce))
- 移除 base 中的私有域名、镜像仓库和部署身份，Ingress class 由 overlay 指定。
  ([8aeb3ce](https://github.com/opsaid/manifests/commit/8aeb3ce))
- 新增必填 Secret `WEBUI_SECRET_KEY`，保持会话签名密钥跨 Pod/worker 一致。
  ([8aeb3ce](https://github.com/opsaid/manifests/commit/8aeb3ce))
- 包内 Redis 组件资源去前缀命名：Service/Deployment `open-webui-redis` → `redis`，
  `REDIS_URL` 主机同步为 `redis.open-webui.svc.cluster.local`。引用旧资源名的脚本、
  监控或 overlay patch 需相应更新；两个资源改名后按重建应用，主应用需滚动重启。
  ([057494a](https://github.com/opsaid/manifests/commit/057494a))

### Feature

- 提供完整 overlay、私有构建工具、结构校验和 CI；稳定 generator 名下单独更改 env 不会自动滚动，
  需显式滚动更新。([8aeb3ce](https://github.com/opsaid/manifests/commit/8aeb3ce))
- 默认关闭 OIDC 注册/角色/分组管理及用户信息转发，恢复请求证书校验；原环境须审查这些行为变化。
  ([8aeb3ce](https://github.com/opsaid/manifests/commit/8aeb3ce))
- 新增 TLS 证书例外口径：`tls.crt`/`tls.key` 允许提交在 overlay `configuration/secrets/` 下，
  经 files 型 secretGenerator（`kubernetes.io/tls`）交付；示例保留默认关闭的注释配置，校验器放行
  合法 TLS Secret（可选第 10 个资源，类型与键名必须正确）。
  ([41c9c1f](https://github.com/opsaid/manifests/commit/41c9c1f))

### Bug or Regression

- 修复默认 securityContext 与官方镜像权限模型不兼容：镜像启动时改写 `open_webui/static`
  下自带静态资源，目录按属组 0 + `chmod g=u` 交付并要求进程属于 GID 0；原 `runAsGroup: 1001`
  导致启动阶段写入 EACCES。改为 `runAsUser: 1001` + `runAsGroup: 0`，非 root 与
  drop ALL capabilities 不变。
  ([8fd3b27](https://github.com/opsaid/manifests/commit/8fd3b27))

### Dependencies

- 保留 Open WebUI v0.11.3、Redis 7.4.2-alpine3.21；改用官方镜像地址，运行兼容性待验收。
  ([8aeb3ce](https://github.com/opsaid/manifests/commit/8aeb3ce))

### Other (Cleanup or Flake)

- 明确公开口径：组织公共镜像仓库（registry.cn-hangzhou.aliyuncs.com/opsaid）与 namespace 属公开
  标识，公共示例直接使用真实值；私密配置与主机 IP 仍禁止出现在公共内容中。
  ([9d71893](https://github.com/opsaid/manifests/commit/9d71893))
- 示例 overlay 精简：镜像 tag 与 generator options 继承 base（渲染等价），移除配置修订注解，
  配置变更沿用部署流程中的 rollout restart；namespace 保留显式设置，overlay 本地生成的资源
  （如 TLS Secret）依赖它落到正确 namespace。([e65e44d](https://github.com/opsaid/manifests/commit/e65e44d))

## Notes

当前没有商店发布 tag。切换旧部署入口前必须先准备私有 overlay，并完成依赖、配置、权限、
数据备份和运行验证。未声明支持数据库降级或直接回退数据迁移。
