# 变更记录索引

参考 [Kubernetes CHANGELOG](https://github.com/kubernetes/kubernetes/tree/master/CHANGELOG)
目录规范：每个应用一个子目录，每条版本线（major）一个 `CHANGELOG-v<major>.md`，
新版本段落在前；每段含发布元信息、`Changelog since 上一版本`、`Changes by Kind` 分类
与提交引用，空分类省略。未发布条目暂存于当前版本线的 `Unreleased` 段，发布时改为
版本头并补齐发布元信息。结构与维护规则以
[公共规范 §6](../.agents/skills/addon-maintenance/references/addon-store.md) 为权威来源。

## 索引

- [open-webui v0](./open-webui/CHANGELOG-v0.md)
