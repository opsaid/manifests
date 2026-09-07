# argo-cd 制作说明

资源整理来源：[Argo CD v3.1.7 manifests](https://github.com/argoproj/argo-cd/tree/v3.1.7/manifests)。
当前镜像以本目录 `kustomization.yaml` 的 images 为准，模板骨架见
[应用模板](../../template/appname/README.md)，目录归属见
[公共规范](../../docs/spec/addon-store.md)。

## 上游适配

沿用既有清单行为：移除内置 Dex；argocd-server 使用 HTTP（`--insecure=true`），
Service 未开放 443，TLS 接入由环境入口设计。此处记录包结构，不表示已经完成商店运行验收。

CRD 保留上游分文件及 `clusters/crds/kustomization.yaml` 聚合入口。
RBAC 位于 `security/` 下按 Kind 分类，`security/kustomization.yaml` 聚合；ConfigMap 与
Secret 分目录，原错置的 argocd-secret 已迁入 `configuration/secrets/`。
部分网络/配置清单尚未由入口启用，不因文件存在推断功能已经启用。

## 制作与升级

从固定的上游版本取得 manifests，对照根入口引用的对象更新公共包，再按实际 Kind 归类。
保留资源名、容器名和配置语义，逐项说明与上游的差异。配置既有完整 ConfigMap/Secret 清单，
不能把它们当作 files generator 的原始输入；后续 overlay 必须单独验证合并粒度。

本轮只迁移目录和更新引用，渲染的 48 个对象内容与迁移前一致。全仓命令及以下命令可检查
目录、selector、镜像固定和构建；`--build-only` 明确不执行专属应用合同。

```bash
scripts/validate.sh --app argo-cd --build-only
```

## 商店接入尚缺

尚未提供完整公开 overlay、应用输入合同和目标环境运行证据，未登记 catalog。
接入前须盘点 files/完整清单的配置覆盖方式、CRD/ClusterRole 所有权、权限、Ingress/TLS、
配置更新和升级回退行为，编写 `docs/apps/argo-cd/README.md` 并注册专属检查。

功能资源调整遵循 [AGENTS.md](../../AGENTS.md)。现有源文件内镜像 tag 等上游遗留写法
仍需在后续上架审查中对齐，目录合规不等于已满足全部商店合同。
