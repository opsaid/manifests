# Changelog

## Unreleased — open-webui

- 采用公共 Kustomize base + 私有 overlay；公共规范合并至 addon-maintenance 技能。
- 移除 base 中的私有域名、镜像仓库和部署身份，Ingress class 由 overlay 指定。
- 保留 Open WebUI v0.11.3、Redis 7.4.2-alpine3.21；现在使用官方镜像地址，运行兼容性待验收。
- 默认关闭 OIDC 注册/角色/分组管理及用户信息转发，恢复请求证书校验；原环境须审查这些行为变化。
- 新增必填 Secret `WEBUI_SECRET_KEY`，保持会话签名密钥跨 Pod/worker 一致。
- 提供完整 overlay、私有构建工具、结构校验和 CI；稳定 generator 名仍要求显式滚动更新。

当前没有商店发布 tag。切换旧部署入口前必须先准备私有 overlay，并完成依赖、配置、权限、
数据备份和运行验证。未声明支持数据库降级或直接回退数据迁移。
