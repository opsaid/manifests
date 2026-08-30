# configmaps

非敏感应用配置。推荐通过根 kustomization 的 `configMapGenerator` 生成后引用
（`disableNameSuffixHash: true` 保持资源名稳定），Deployment 侧以 `envFrom` 或 volume 挂载使用。

`app.yaml` 为模版自带占位（已被 configMapGenerator 引用），替换为实际配置即可。
