---
name: addon-maintenance
description: 在 manifests 仓库制作、修改、升级或评审 Kustomize 应用及私有 overlay 时使用，维护公共 base、接入示例和商店发布合同。
---

# 应用维护

本技能以 Kustomize base + overlay 实现公共应用与私有环境分离。

开始维护或评审前，读取根 [AGENTS.md](../../../AGENTS.md) 的编辑边界，以及
[Addon Store 公共规范](references/addon-store.md)。规范正文只维护在该引用文件中。
本技能不授予部署、发布或修改只读资源的额外权限，沿用用户在当前任务中的授权。

## 工作流程

1. 检查工作区已有改动，读取目标应用入口、被引用的配置与资源，以及 `docs/<app>/README.md`
   （存在时）。区分公共默认值、环境差异、凭据及应用结构变化。
2. 公共默认值维护在 `addons/<app>/`；真实差异维护在私有仓库 overlay；
   `examples/overlays/<app>/` 只保存完整的虚构环境示例。具体接口与发布要求以公共规范为准。
3. 修改时同步应用输入说明与受影响的示例；若规范改变，仅更新 references 中的权威文本。
   功能资源的必要变更依照 AGENTS.md 处理，不以本技能为由扩大改动范围。
4. 执行根 `scripts/validate.sh`，并对目标应用执行 `scripts/validate.sh --app <app>`；
   首期合同检查仅实现 open-webui，新增应用需补对应检查。修改校验器时运行
   `python3 -m unittest discover -s scripts/tests -v`。
5. 准备私有部署配置时使用 `scripts/render-private.py` 的临时副本流程；工具只生成文件，
   实际 apply/rollout 根据当前部署授权和应用文档执行。
6. 报告实际完成的检查与尚未完成的运行/发布条件；计划记进度，`CHANGELOG/<app>/CHANGELOG-v<major>.md` 记录发布影响，
   不把渲染通过记成集群验收或正式上架。

通用检查程序在根 `scripts/`，完整示例在根 `examples/`，均不再复制进技能目录。
