# AGENTS.md

本仓库是 opsaid 的 Kubernetes kustomize 清单仓库。AI 代理在本仓库工作时必须遵守以下约定。

## 变更边界（重要）

对每个应用目录 `addons/<appname>/`（按 `template/appname/` 骨架生成）：

**仅允许修改：**

| 路径 | 职责 |
| --- | --- |
| `kustomization.yaml` | 入口配置：namespace、labels、generator、replicas、resources 引用、images 替换与版本固定、patches（Ingress host 等字段替换） |
| `configuration/` | 应用配置：`configmaps/`、`secrets/` 下的配置文件（如 `*.env`） |

**其余路径一律只读，不允许变更**，包括：

- `clusters/`、`gateway/`、`network/`、`security/`、`storage/`、`workloads/` 下的功能清单
- `README.md` 等文档

这些清单由模版按上游 chart 生成并对齐，保持稳定。日常变更全部收敛到允许修改的两处完成：

- 升级 / 替换镜像：改 `kustomization.yaml` 的 `images`（`newName` / `newTag`）
- 调整副本数：改 `kustomization.yaml` 的 `replicas`
- 增改环境变量：改 `configuration/configmaps/*.env` 或 `configuration/secrets/*.env`
- 替换 Ingress host：改 `kustomization.yaml` 的 `patches`（Ingress 默认 host 为占位值
  `appname.example.com`，实际域名一律在 patches 中替换，私有域名不得写入功能清单）

新增功能清单（如 `resources` 引用的新文件）、调整现有清单结构均属越界，按下一节处理。

## 越界处理

若确需修改只读路径（功能清单重构、上游 chart 大版本升级、新增资源文件等），
不要直接改动：先说明原因与方案，征得维护者明确同意后再执行。

## 其他约定

1. 提交前对改动的应用目录执行 `kustomize build addons/<appname>` 验证可渲染、资源数量与内容符合预期。
2. 敏感信息（密码、API Key、client secret 等）不得写入 git：`configuration/secrets/` 中使用
   `CHANGE_ME` 等占位符，部署前线下填写真实值。TLS 证书文件（`tls.crt`/`tls.key`）是唯一例外，
   允许提交在 overlay 的 `configuration/secrets/` 下通过 files 型 secretGenerator 交付；
   公共仓库示例只保留默认关闭的注释配置，不放真实证书。
3. 镜像版本统一在 `kustomization.yaml` 的 `images` 中固定，清单内不写死 tag；清单中的镜像保持
   官方值，替换到私有 registry 通过 `images` 的 `newName` 实现。
4. 目录划分、占位约定与使用规则见 `template/appname/README.md`。

## 应用商店维护入口

制作、修改、升级或评审应用与 overlay 时，读取
[addon-maintenance 技能](.agents/skills/addon-maintenance/SKILL.md)，并按其引用读取公共规范。
公共规范只保存在 [docs/spec/addon-store.md](docs/spec/addon-store.md)，技能引用该唯一正文；
本文件保留全局编辑权限约束，不重复规范正文。
现有 addon 按计划逐步迁移，不因技能建立而自动成为已发布的商店应用。

## Agent 兼容入口

本文件是共享仓库规则的唯一来源，`CLAUDE.md` 通过 `@AGENTS.md` 导入，不复制规则。
技能正文仅保存在 `.agents/skills/`；Claude Code 的 `.claude/skills/addon-maintenance`
为指向共享技能的符号链接，不单独编辑。其他 agent 若不自动发现技能，按上方链接读取。
