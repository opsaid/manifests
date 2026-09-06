# appname 目录模版

分类划分参考 [headlamp](https://github.com/kubernetes-sigs/headlamp) dashboard 的资源导航分组。

## 目录划分

```text
appname/
├── kustomization.yaml                     # 入口：namespace / labels / generator / resources / images
├── clusters/                              # Cluster：集群级资源
│   ├── crds/                              #   CustomResourceDefinition（按需）
│   ├── namespaces/                        #   Namespace + LimitRange / ResourceQuota
│   └── nodes/                             #   Node
├── configuration/                         # Configuration：应用配置
│   ├── configmaps/                        #   非敏感配置（配合 configMapGenerator）
│   └── secrets/                           #   敏感配置（配合 secretGenerator）
├── gateway/                               # Gateway：Gateway API（HTTPRoute 等，按需）
├── network/                               # Network：网络资源
│   ├── services/                          #   Service
│   ├── ingresses/                         #   Ingress
│   └── policies/                          #   NetworkPolicy
├── security/                              # Security：命名空间级 RBAC
│   ├── serviceaccounts/                   #   ServiceAccount
│   ├── roles/                             #   Role / RoleBinding
│   └── rolebindings/
├── storage/                               # Storage：存储资源
│   ├── persistent-volume-claims/          #   PersistentVolumeClaim
│   ├── persistent-volumes/                #   PersistentVolume（按需）
│   └── storage-classes/                   #   StorageClass（按需）
└── workloads/                             # Workloads：工作负载
    ├── cronjobs/                          #   CronJob（按需）
    ├── daemonsets/                        #   DaemonSet（按需）
    ├── deployments/                       #   Deployment
    └── statefulsets/                      #   StatefulSet
```

对应 headlamp 分组：`Cluster`、`Configuration`、`Gateway`、`Network`、`Security`、`Storage`、`Workloads`。
命名空间级 RBAC 与 ServiceAccount 放 `security/`；ClusterRole 等集群级 RBAC 与 CRD 属低频资源，
需要时在 `clusters/` 下自建（参考 argo-cd addon 的 `clusters/crds/`、`security/roles/`）。

## 使用规则

1. 复制骨架到 addon 目录：

   ```shell
   cp -rp ../../../template/appname/* ./
   ```

2. git 不追踪空目录：无示例内容的目录以 README.md 占位并说明用途 —— 复制骨架后
   不使用的删除 README.md，使用的替换为实际清单并加入 kustomization `resources`。

3. `resources` 中未引用的分类（security/、storage/、policies、statefulsets）启用时
   自行加入 kustomization；已引用的占位文件填充真实内容后即生效，无需改动 kustomization。

4. 配置注入优先使用 `configMapGenerator` / `secretGenerator`（`disableNameSuffixHash: true`
   保持资源名稳定），Deployment 侧以 `envFrom` 或 volume 挂载引用。

5. 镜像版本统一在 kustomization `images` 中用 `newTag` 固定，清单内不写死 tag。

## 最佳实践

不同环境的差异变更仅收敛到两处，其余路径尽量不做自定义：

| 路径 | 可变更内容 |
| --- | --- |
| `kustomization.yaml` | namespace、labels、generator、replicas、resources 引用、`images` 替换与版本固定、`patches`（Ingress host、ingressClassName 等字段替换） |
| `configuration/` | `configmaps/`、`secrets/` 下的配置文件（如 `*.env`） |

Ingress 默认 host 为占位值 `appname.example.com`（RFC 2606 保留域，不指向任何公司，且随应用名唯一）；
复制模版后在 kustomization `patches` 中替换为实际域名（JSON6902），
私有域名不得写入 `network/` 清单。

其余目录（`clusters/`、`gateway/`、`network/`、`security/`、`storage/`、`workloads/`）
存放按模版整理的功能清单，保持与模版一致，不做环境级自定义。确需调整时先说明原因与方案，
征得维护者同意后再执行。
