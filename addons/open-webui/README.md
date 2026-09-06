# open-webui

## 来源

<https://github.com/open-webui/helm-charts/tree/open-webui-16.1.0/charts/open-webui>

环境变量与功能开关对齐线上 docker compose 配置（外部 Postgres、GoChat OAuth、OTEL 等）；配置持久化策略、RAG embedding 模型等按本清单方案调整，差异见文末表格。

## 制作方式

### 获取源文件

```shell
git clone --branch open-webui-16.1.0 --depth 1 https://github.com/open-webui/helm-charts.git
```

### 生成目录

参考 chart 渲染结果，按 `../../../template/appname` 骨架整理：

```text
addons/open-webui/
├── kustomization.yaml
├── clusters/
│   └── namespaces/open-webui.yaml         # Namespace
├── configuration/
│   ├── configmaps/open-webui.env          # 非敏感环境变量
│   └── secrets/open-webui.env             # 敏感环境变量（API Key、S3 密钥）
├── network/
│   ├── ingresses/open-webui.yaml          # Ingress
│   └── services/open-webui.yaml           # open-webui / open-webui-redis Service
├── security/
│   └── serviceaccounts/open-webui-sa.yaml # ServiceAccount
└── workloads/
    └── deployments/
        ├── open-webui.yaml                # 主服务
        └── open-webui-redis.yaml          # websocket manager 依赖的 Redis
```

## 相关特性

### Deployment 工作负载

chart 在 persistence（local provider）+ PVC 场景默认 StatefulSet；数据对接 S3 后无 RWO 限制，
使用 Deployment 即可，数据卷为 `emptyDir`（挂载 `/app/backend/data`）。
资源基线（requests / limits）保留在 base 清单中，与探针、端口同属应用结构；按环境调整时取消
kustomization `patches` 中预留的资源块注释并修改数值，集群级默认可用 LimitRange / ResourceQuota
（模板 `clusters/namespaces/` 已预留）。

### 环境变量注入

env 不写死在 Deployment 中，通过 kustomization 的 `configMapGenerator` / `secretGenerator`
从 `configuration/` 下的 `.env` 文件生成（`disableNameSuffixHash` 保持资源名稳定），
Deployment 以 `envFrom` 注入。敏感项（`DATABASE_URL`、`OPENAI_API_KEY`、`OAUTH_CLIENT_SECRET`、
`S3_ACCESS_KEY_ID`、`S3_SECRET_ACCESS_KEY`）放 `configuration/secrets/`，其余放
`configuration/configmaps/`。敏感值一律以 `CHANGE_ME` 等占位符入库，部署前线下填写真实值。

### S3 对象存储

`persistence.provider: s3`：数据直存 S3，不创建 PVC。`configuration/` 下的
`S3_*` 环境变量需填写实际值（端点、桶、密钥等）。
注意 `S3_ENDPOINT_URL` / `S3_REGION_NAME` 不能以空值提交——空串会导致应用启动即崩溃
（botocore Invalid endpoint），接入前以注释占位；AWS 原生桶不要启用 `S3_ENDPOINT_URL`。

### copy-app-data 初始化（已移除）

chart 的 `copy-app-data` initContainer 用于从镜像内播种默认数据；实测镜像内 `/app/backend/data`
为空目录，播种无实际作用，本清单已移除。

### ServiceAccount

`open-webui-sa` 挂载到 Pod，`automountServiceAccountToken: false`（应用不访问 K8s API）。

### websocket 支持

`websocket.manager: redis`，配套部署 `open-webui-redis`（Deployment + Service），
连接地址通过 `REDIS_URL` 注入（`WEBSOCKET_REDIS_URL` 默认沿用 `REDIS_URL`，无需单独设置）。

### 外部 Postgres 与 pgvector

`DATABASE_URL`（secrets env，含密码）指向外部 Postgres（192.0.2.85:5432/openwebui），
`VECTOR_DB=pgvector` 复用同一实例（open-webui 的 pgvector 连接串默认回退 `DATABASE_URL`）。
SQLite 不再使用；`/app/backend/data`（emptyDir）仅承载缓存与 S3 上传中转，Pod 重建无状态损失。
配套 `ENABLE_PERSISTENT_CONFIG=False`：运行时配置只认 env，后台 UI 改动不持久化（不再产生 `config.json`）。

### pgvector 前置条件

- 目标库需安装 vector 扩展：`CREATE EXTENSION IF NOT EXISTS vector;`（192.0.2.85 的
  openwebui 库，部署前确认，否则启动建表失败）
- `PGVECTOR_DB_URL` 未设置时复用 `DATABASE_URL`
- 向量维度默认上限 `PGVECTOR_INITIALIZE_MAX_VECTOR_LENGTH=1536`，与 text-embedding-3-small
  匹配；更换更大维度模型（如 text-embedding-3-large 的 3072）需同步调大该值并启用
  `PGVECTOR_USE_HALFVEC`，且已有 collection 需删除重建

### 外部 embedding

`RAG_EMBEDDING_ENGINE=openai`，请求走 `OPENAI_API_BASE_URL` 的 `/embeddings`，密钥在 secrets env。
`RAG_EMBEDDING_MODEL` 必须显式指定：open-webui 默认值是本地 sentence-transformers 模型名
（`sentence-transformers/all-MiniLM-L6-v2`），外部引擎调用会直接报模型不存在。
embedding / reranking 均不使用本地模型，仅对本地模型生效的 `*_AUTO_UPDATE` 开关已移除；
`HF_HUB_OFFLINE=1` 兜底禁止 HuggingFace 下载。

### OAuth / OIDC 单点登录（GoChat）

OAuth 参数对齐线上 compose，`OAUTH_CLIENT_SECRET` 在 secrets env（占位符 `CHANGE_ME`）。
注意：`OPENID_REDIRECT_URI` 已按 k8s 域名改为 `http://open-webui.demo.example.com/oauth/oidc/callback`，
需在 GoChat 侧注册该回调地址。

### 域名替换

Ingress base 的 host 为占位值 `open-webui.example.com`，实际域名通过 `kustomization.yaml` 的
`patches`（JSON6902）替换，不改动只读的 `network/` 清单；与 configuration env 中 `WEBUI_URL`
的域名保持一致。

### OpenTelemetry 预留

OTEL 变量按 compose 原样保留但整体关闭（`ENABLE_OTEL=False`），接入时改开关即可。

### 音频与图片生成（预留，未启用）

音频转写 / 合成、图片绘制默认走本地模型引擎，与 `HF_HUB_OFFLINE=1` 冲突，启用前需在
configuration env 显式接入外部引擎（密钥复用 `OPENAI_API_KEY`）：

- STT / TTS：`AUDIO_STT_ENGINE=openai` / `AUDIO_TTS_ENGINE=openai`
- 图片：`ENABLE_IMAGE_GENERATION=True`（`IMAGE_GENERATION_ENGINE` 默认即 openai）

未配置时相关调用会报错，属预期行为。

### Ingress TLS（可选）

base 清单不启用 TLS；需要时取消 kustomization `patches` 中预留的 TLS 块注释即可生效
（secretName 对应的 TLS Secret 需预先存在或由 cert-manager 签发），并同步将 `WEBUI_URL`
的 scheme 改为 https。

### 与线上 compose 的差异

| 项 | compose | 本清单 | 说明 |
| --- | --- | --- | --- |
| 端口 | `PORT=3000` | 镜像默认 8080 | Service/Ingress 已按 8080 适配 |
| redis | 外部 192.0.2.85:6379（带密码） | 集群内 `open-webui-redis` | 改接外部 redis 时将 `REDIS_URL` 移入 secrets |
| nofile 65535 | ulimits | 未设置 | k8s 无直接等价（需特权 initContainer），暂不设置 |
| CA 证书挂载 | `/etc/ssl/certs/ca-certificates.crt` | 未挂载 | `REQUESTS_VERIFY=False` 下非必需；需严格校验时以 ConfigMap 挂载 |
| 资源 | 无限制 | limits 2C / 4Gi | `UVICORN_WORKERS=4` 对应提升 |
| `ENABLE_PERSISTENT_CONFIG` | True | `False` | 运行时配置只认 env，UI 改动不持久化，配合 emptyDir 完全无状态 |
| `RAG_EMBEDDING_MODEL` | 未设置 | `text-embedding-3-small` | openai 引擎必须显式指定，默认值为本地模型名会报错 |
| `ENABLE_OAUTH_PERSISTENT_CONFIG` | False | 已移除 | `ENABLE_PERSISTENT_CONFIG=False` 下该开关冗余 |
| copy-app-data initContainer | chart 默认包含 | 已移除 | 镜像内 `/app/backend/data` 为空，播种无实际作用 |
| securityContext | 未设置 | 非 root（主容器 1001 / redis 999）+ RuntimeDefault | 安全加固 |
| Ingress TLS | 无 | 预留 patch，按需开启 | 开启后 `WEBUI_URL` 同步改 https |
