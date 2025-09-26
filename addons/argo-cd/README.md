# argo-cd

## 来源

https://github.com/argoproj/argo-cd/tree/v3.1.7/manifests

## 制作方式

### 获取源文件

```shell
mkdir build

git clone --branch v3.1.7 --depth 1 https://github.com/argoproj/argo-cd.git
```

### 生成目录

```shell
cp -rp ../../../template/appname/* ./

rm -rf clusters/namespaces/biz-dev-uptime.yaml
rm -rf clusters/nodes/192.168.0.2.yaml
rm -rf clusters/roles/demo.yaml

rm -rf configuration/configmaps/app.yaml
rm -rf configuration/secrets/app.yaml

rm -rf workloads/deployments/oneops-demo-v1.yaml
rm -rf configuration/configmaps/app.yaml
```

### 制作部署

```shell
cp -rp argo-cd/manifests/crds/* clusters/crds

cp argo-cd/manifests/base/application-controller/argocd-application-controller-statefulset.yaml workloads/statefulsets/argocd-application-controller.yaml
cp argo-cd/manifests/base/application-controller/argocd-application-controller-network-policy.yaml network/policies/argocd-application-controller.yaml
cp argo-cd/manifests/base/application-controller/argocd-metrics.yaml network/services
cp -rp argo-cd/manifests/base/application-controller-roles/ security/roles/

cp argo-cd/manifests/base/applicationset-controller/argocd-applicationset-controller-deployment.yaml workloads/deployments/argocd-applicationset-controller.yaml
cp argo-cd/manifests/base/applicationset-controller/argocd-applicationset-controller-network-policy.yaml network/policies/argocd-applicationset-controller.yaml
cp argo-cd/manifests/base/applicationset-controller/argocd-applicationset-controller-service.yaml network/services/argocd-applicationset-controller.yaml

cp argo-cd/manifests/base/applicationset-controller/argocd-applicationset-controller-role.yaml security/roles/
cp argo-cd/manifests/base/applicationset-controller/argocd-applicationset-controller-rolebinding.yaml security/roles/
cp argo-cd/manifests/base/applicationset-controller/argocd-applicationset-controller-sa.yaml security/roles/
cp -rp argo-cd/manifests/base/config/*.yaml configuration/configmaps/
```

```shell
cp argo-cd/manifests/base/notification/argocd-notifications-cm.yaml configuration/configmaps
cp argo-cd/manifests/base/notification/argocd-notifications-controller-deployment.yaml workloads/deployments/argocd-notifications-controller.yaml
cp argo-cd/manifests/base/notification/argocd-notifications-controller-metrics-service.yaml network/services/argocd-notifications-controller.yaml
cp argo-cd/manifests/base/notification/argocd-notifications-secret.yaml configuration/secrets/argocd-notifications.yaml
cp argo-cd/manifests/base/notification/argocd-notifications-controller-role.yaml security/roles
cp argo-cd/manifests/base/notification/argocd-notifications-controller-rolebinding.yaml security/roles
cp argo-cd/manifests/base/notification/argocd-notifications-controller-sa.yaml security/roles
```

```shell
cp argo-cd/manifests/base/repo-server/argocd-repo-server-deployment.yaml workloads/deployments/argocd-repo-server.yaml
cp argo-cd/manifests/base/repo-server/argocd-repo-server-network-policy.yaml network/policies/argocd-repo-server.yaml
cp argo-cd/manifests/base/repo-server/argocd-repo-server-sa.yaml security/roles
cp argo-cd/manifests/base/repo-server/argocd-repo-server-service.yaml network/services/argocd-repo-server.yaml
```

```shell
cp argo-cd/manifests/base/server/argocd-server-deployment.yaml workloads/deployments/argocd-server.yaml
cp argo-cd/manifests/base/server/argocd-server-metrics.yaml network/services
cp argo-cd/manifests/base/server/argocd-server-network-policy.yaml network/policies
cp argo-cd/manifests/base/server/argocd-server-role.yaml security/roles
cp argo-cd/manifests/base/server/argocd-server-rolebinding.yaml security/roles
cp argo-cd/manifests/base/server/argocd-server-sa.yaml security/roles
cp argo-cd/manifests/base/server/argocd-server-service.yaml network/services
```

```shell
cp argo-cd/manifests/base/redis/argocd-redis-deployment.yaml workloads/deployments/argocd-redis.yaml
cp argo-cd/manifests/base/redis/argocd-redis-network-policy.yaml network/policies
cp argo-cd/manifests/base/redis/argocd-redis-role.yaml security/roles
cp argo-cd/manifests/base/redis/argocd-redis-rolebinding.yaml security/roles
cp argo-cd/manifests/base/redis/argocd-redis-sa.yaml security/roles
cp argo-cd/manifests/base/redis/argocd-redis-service.yaml network/services
```

```shell
cp argo-cd/manifests/cluster-rbac/application-controller/argocd-application-controller-clusterrole* security/roles
cp argo-cd/manifests/cluster-rbac/applicationset-controller/argocd-applicationset-controller-clusterrole* security/roles
cp argo-cd/manifests/cluster-rbac/server/argocd-server-clusterrole* security/roles
```

## 相关特性

### 移除 dex 组件

1. 移除内置 dex 服务，不支持 "dex.config" 配置；

### 默认 http 访问

workloads/deployments/argocd-server.yaml

```text
      - args:
        - /usr/local/bin/argocd-server
        - --insecure=true
```

network/services/argocd-server-service.yaml

关闭 443 端口。

