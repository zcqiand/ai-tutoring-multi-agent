# Tag 规约

> 从 CLAUDE.md 移出（L0 60 行门），口径未改。

| 字段 | 值 |
|---|---|
| 格式 | `v<MAJOR>.<MINOR>.<PATCH>-<YYYYMMDD>` |
| 用途 | 公开里程碑（sprint 收尾 / 部署上线 / 版本基线） |
| 能否删 / 覆盖 | **禁止** |

样例：

- `v0.7.0-20260821` —— saas-nextjs backend 塌缩后的 0.7.0 release
- `v0.1.2-20260821` —— suite 根仓的 release（这次 form A → B + tag / submodule 规约更新）

> `<YYYYMMDD>` 是 tag 创建日（commit author date 也可，但要同一仓一致）。
> 不放 commit 数 —— `git describe` 会自动加 `-<N>-g<sha>` 后缀。
>
> **历史遗留**：tag（legacy，已按 Release 格式重命名）——
>
> - `v1.0-003` → `v0.0.1-20260627`（`12af366`）
> - `v1.0-Harness-工程：围绕-Claude-Code-构建可靠系统` → `v0.0.2-20260629`（`12af366`）
>
> 旧名已删，仅 Release 格式名生效；**新 tag 一律用 Release 格式**。

## 推送

```bash
# 正确
git push origin v0.7.0-20260821

# 错误：可能误推未准备好的 tag
git push --tags
```

`--tags` 把本地**全部** tag 推上去。Release tag 应该显式 `push origin <tag>`，让
reviewer 在推送前显式选择。
