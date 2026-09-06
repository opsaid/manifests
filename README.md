# manifests

对各开源服务经过整理编排后，在结合 [deploy-k8s](https://github.com/opsaid/deploy-k8s) 项目，实现一键部署。

## 应用商店（试点）

采用 Kustomize base + overlay：公共应用在 `addons/`，真实环境配置在独立私有仓库。
目前 open-webui 已完成本地构建与合同测试，尚未完成运行和公开发布验收，`catalog.yaml` 暂无上架条目。

- [open-webui 接入说明](docs/apps/open-webui.md)与[完整公开示例](examples/overlays/open-webui/README.md)
- [AI 应用维护技能](.agents/skills/addon-maintenance/SKILL.md)与[公共规范](.agents/skills/addon-maintenance/references/addon-store.md)
- [实施计划](docs/2026-09-06-addon-store-plan.md)与[执行记录](docs/2026-09-06-addon-store-execution.md)

安装 `scripts/requirements.txt` 中的 Python 依赖及 `scripts/kustomize-version.txt` 指定的工具后，执行：

```bash
scripts/validate.sh --app open-webui
python3 -m unittest discover -s scripts/tests -v
```

全仓公开检查另运行 `scripts/validate.sh --audit-public`；当前旧应用、模板和历史仍有待清理内容，
构建通过不代表整个仓库已经完成公开审查。
