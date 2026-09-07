# argo-workflows 制作与迁移说明

上游项目：[argoproj/argo-workflows](https://github.com/argoproj/argo-workflows)。
当前镜像版本由根入口 `kustomization.yaml` 的 images 固定；原始生成依据与实测环境尚需补齐，
不能从镜像版本推断所有清单都已与相应上游版本核对。

本轮将旧 cluster、service、config 分类迁入公共规范的目录，保留应用根构建入口。
RBAC 已按 Kind 拆分；Namespace 与 PriorityClass 分别归位。当前 controller ConfigMap generator 为空，配置覆盖方式须在接入时设计。
`clusters/crds/crds.yaml` 保留同 Kind 的上游多对象 CRD 清单，避免无功能收益的格式重写。

迁移前后 26 个渲染对象内容一致；没有变更对象名称、镜像版本、权限、配置或存储行为。

```bash
scripts/validate.sh --app argo-workflows --build-only
```

该命令只证明本地结构和构建通过；专属应用合同、完整公开 overlay、输入说明、CRD 与集群权限
ownership、升级回退和运行验收尚未完成，未登记 catalog。制作规范见
[公共规范](../../docs/spec/addon-store.md)，功能资源变更遵循 [AGENTS.md](../../AGENTS.md)。
