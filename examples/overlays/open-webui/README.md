# open-webui overlay 示例

执行 `kustomize build examples/overlays/open-webui` 可渲染 9 个资源。
该示例演示 namespace、域名/TLS、Ingress class、镜像仓库、资源请求及配置差异合并。
镜像仓库、服务地址和凭据都是示例，尚不能直接安装。

复制到私有仓库后，替换远程 base 引用为实际发布 tag/SHA，填写非凭据环境配置；
使用部署端密钥来源填充临时构建副本，原仓库保留占位值。
TLS Secret `open-webui-tls` 由平台预先提供，namespace 必须匹配。

完整输入、构建与更新步骤见 [应用接入说明](../../../docs/apps/open-webui.md)。
