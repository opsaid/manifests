# secrets

敏感应用配置（API Key、密码、证书等）。推荐通过根 kustomization 的 `secretGenerator`
从 `.env` 或文件生成，Deployment 侧以 `envFrom.secretRef` 或 `secretKeyRef` 引用。
