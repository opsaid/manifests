# appname 应用模板

本模板提供新应用的最小公共 base。目录与命名以
[Addon Store 公共规范](../../docs/spec/addon-store.md)为权威来源。
模板镜像与配置是占位示例，可构建不代表可以启动或已经满足上架要求。

## 默认与可选资源

```text
appname/
├── kustomization.yaml
├── clusters/namespaces/
│   ├── appname.yaml             # 默认 Namespace
│   ├── limit-range.yaml         # 可选，不在默认入口引用
│   └── memory-quota.yaml        # 可选，不在默认入口引用
├── configuration/configmaps/
│   └── app.yaml                 # 挂载到 /etc/appname/app.yaml 的配置输入
├── network/
│   ├── services/appname.yaml    # 默认 Service
│   └── ingresses/appname.yaml   # 可选，不预设 Ingress class
└── workloads/deployments/
    └── appname.yaml             # 默认 Deployment
```

默认渲染 4 个对象：Namespace、ConfigMap、Deployment、Service。Namespace、LimitRange、
ResourceQuota 分文件交付，创建专用 namespace 不会同时施加配额。启用可选文件前需确定其
ownership、参数和运行影响，并在入口 resources 中显式引用。

## 制作步骤

从 manifests 仓库根目录复制：

```bash
mkdir -p addons/my-app
cp -R template/appname/. addons/my-app/
```

1. 将 YAML 内的 `appname` 替换为新应用 ID，并同步资源文件名及 resources 引用。对象、
   generator、selector、Pod labels 和 Service selector 必须一致。存量应用不按此步骤改名。
2. 将 Deployment 的示例镜像改为官方镜像名，在入口 `images` 中固定版本。示例 registry
   不是真实镜像来源；实际私有 registry 差异由 overlay 的 `images.newName` 提供。
3. 按实际应用校对监听端口、探针、配置文件格式/路径及启动方式。模板只演示 8080 端口和
   TCP 探针、只读配置挂载，不预设程序参数、UID/GID 或调度策略；制作时应按镜像验证权限、
   安全上下文、可写目录和健康检查，不能把未实测的默认值作为支持承诺。
4. 配置文件优先通过 configMapGenerator / secretGenerator 生成。需要凭据时按规范增加
   `configuration/secrets/` 占位输入，真实值在部署端受控临时副本中注入。当前 generator
   保留稳定名称，配置更新后的滚动生效方式必须写入应用说明。
5. 按需启用 Ingress、配额，或按规范增加 RBAC、存储等资源。真实环境域名、Ingress class、
   TLS 和资源差异放私有 overlay，公开示例放 `examples/overlays/<id>/`。
6. 编写制作说明与 `docs/apps/<id>/README.md`，提供可构建示例和应用合同检查，完成运行及
   发布验收后才加入 catalog。新增或调整 addon 功能资源仍遵循 AGENTS.md 的授权边界。

```bash
kustomize build template/appname
scripts/validate.sh
scripts/validate.sh --app my-app --build-only
```

最后一个命令用于尚未注册应用合同的新包，不代表完成商店验收；合同接入后去掉 `--build-only`。

## 维护边界

公共默认值在 addon 中维护，真实环境差异在私有 overlay 中维护。日常应用变更仍集中于
`kustomization.yaml` 与 `configuration/`；功能资源和应用 README 的调整按
[AGENTS.md](../../AGENTS.md) 执行。模板不再用空目录及占位 README 展示完整 Kubernetes 分类，
需要新 Kind 时在公共规范中明确归属及安装责任。
