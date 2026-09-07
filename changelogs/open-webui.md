# open-webui 变更记录

每个应用一个文件；版本标题对应发布 tag（`<id>-v<semver>`），未发布变更记录在 Unreleased。

## Unreleased

- 采用公共 Kustomize base + 私有 overlay；公共规范合并至 addon-maintenance 技能。
- 移除 base 中的私有域名、镜像仓库和部署身份，Ingress class 由 overlay 指定。
- 保留 Open WebUI v0.11.3、Redis 7.4.2-alpine3.21；现在使用官方镜像地址，运行兼容性待验收。
- 默认关闭 OIDC 注册/角色/分组管理及用户信息转发，恢复请求证书校验；原环境须审查这些行为变化。
- 新增必填 Secret `WEBUI_SECRET_KEY`，保持会话签名密钥跨 Pod/worker 一致。
- 提供完整 overlay、私有构建工具、结构校验和 CI；稳定 generator 名仍要求显式滚动更新。
- 明确公开口径：组织公共镜像仓库（registry.cn-hangzhou.aliyuncs.com/opsaid）与 namespace
  属公开标识，公共示例直接使用真实值；私密配置与主机 IP 仍禁止出现在公共内容中。
- 示例 overlay 精简：镜像 tag 与 generator options 继承 base（渲染等价），不使用配置修订注解，
  配置变更沿用部署流程中的 rollout restart；namespace 保留显式设置，overlay 本地生成的
  资源（如 TLS Secret）依赖它落到正确 namespace。
- 新增 TLS 证书例外口径：`tls.crt`/`tls.key` 允许提交在 overlay `configuration/secrets/` 下，
  经 files 型 secretGenerator（kubernetes.io/tls）交付；示例保留默认关闭的注释配置，
  校验器放行合法 TLS Secret（可选第 10 个资源，类型与键名必须正确）。

当前没有商店发布 tag。切换旧部署入口前必须先准备私有 overlay，并完成依赖、配置、权限、
数据备份和运行验证。未声明支持数据库降级或直接回退数据迁移。
