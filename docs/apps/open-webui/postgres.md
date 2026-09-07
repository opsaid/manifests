# PostgreSQL 依赖准备（open-webui）

为 open-webui 准备外部 PostgreSQL + pgvector 的操作手册。接入前提、整体依赖与
升级注意见 [应用接入说明](./README.md)。

## 适用范围与版本

- 适用 open-webui 默认存储组合（外部 PostgreSQL + pgvector）；更换存储组合不在本包支持范围
- 使用可安装 pgvector 扩展的 PostgreSQL 版本；版本与扩展兼容性以实际验收为准，本文档不承诺
- 自建实例与云托管数据库（RDS 等）均可，差异点在各节标注

## 1. 创建数据库与账号

密码由密钥管理流程生成与下发，不写入 Git（Git 中仅保留 `CHANGE_ME` 占位）。

```sql
-- 创建登录账号
CREATE ROLE openwebui WITH LOGIN PASSWORD 'CHANGE_ME';
-- 创建业务库，owner 即该账号（应用需要建表并执行 schema 迁移）
CREATE DATABASE openwebui OWNER openwebui;
```

平台限制无法使用 owner 方式时，改由管理员建库后授权：

```sql
CREATE DATABASE openwebui;
-- 连接到 openwebui 库执行
GRANT ALL PRIVILEGES ON SCHEMA public TO openwebui;
```

PostgreSQL 15+ 的 `public` schema 归 `pg_database_owner` 所有：库 owner 可正常建表；
非 owner 账号需显式 `GRANT CREATE ON SCHEMA public`。

## 2. 启用 pgvector 扩展

```sql
-- 连接到 openwebui 业务库执行
CREATE EXTENSION IF NOT EXISTS vector;
```

- 自建实例：先在实例层安装 pgvector 软件包（发行版包名如 `postgresql-16-pgvector`），再执行上述 SQL
- 云托管：确认实例规格支持 pgvector；扩展通常由特权账号或控制台安装，应用账号只需扩展在库内可用
- 验证：`SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';`

## 3. 连接串与配置对接

连接串格式（占位值示例）：

```text
postgresql://openwebui:CHANGE_ME@postgres.example.com:5432/openwebui
```

- 带密码的连接串是凭据：最终写入私有 overlay `configuration/secrets/open-webui.env` 的
  `DATABASE_URL`，Git 中保持 `CHANGE_ME` 占位；注入流程见接入说明「从公开示例接入私有仓库」
- 应用启动会执行 schema 迁移：账号需要目标库的建表/读写权限，不需要超级用户
- 连接串中的主机、端口、库名与账号对应第 1 节的创建结果，改名时同步更新

## 4. 网络访问

- 集群内 Pod 走内网访问数据库；白名单/安全组放通集群出口，实际地址不在公共文档记录
- 自建实例核对 `listen_addresses` 与 `pg_hba.conf`（按实际网段配置，不照抄示例）
- 云托管在控制台维护白名单，变更走平台审批流程；不得对公网开放

## 5. 备份与升级注意

- 应用启动涉及 schema 迁移：升级 open-webui 前先备份（自建用 `pg_dump`，云托管用快照/PITR）
- 回退应用版本不会自动回滚数据库迁移；先确认数据向后兼容或有可执行恢复方案
  （见接入说明「数据、升级与发布验收」）
- 实例或扩展版本升级后，验证向量检索功能正常

## 6. 验收清单

- [ ] 应用账号可连接目标库（用连接串跑 `psql` 验证）
- [ ] `vector` 扩展已在业务库启用且版本符合预期
- [ ] 账号具备建表与读写权限（试建并删除一张临时表）
- [ ] 网络白名单放通集群出口，且未对公网开放
- [ ] 备份任务已配置并演练过恢复
