# lark-cli 环境（官方）

来源：[larksuite/cli](https://github.com/larksuite/cli)（飞书官方 CLI，MIT）。

## 环境要求

- **Node.js**（`npm` / `npx`）
- 源码构建才需要 Go 1.23+、Python 3

## AI Agent 首次配置（四步）

```bash
# 1. 安装 CLI + 全局 Skills（官方推荐）
npx @larksuite/cli@latest install
npx skills add larksuite/cli -y -g

# 2. 应用凭证（后台运行，把授权链接发给用户在浏览器完成）
lark-cli config init --new

# 3. 用户 OAuth 登录（--recommend 为常用自动审批 scope）
lark-cli auth login --recommend

# 4. 验证
lark-cli auth status
```

`auth login` 可后台运行并提取链接；也可用 `--no-wait` + `--device-code` 恢复轮询（见官方文档）。

## 与本项目相关的官方 Skills

| Skill | 本仓库用途 |
|-------|------------|
| **lark-shared** | 认证、权限、身份 `--as user`（**必须先读**） |
| **lark-doc** | `docs +create` / `docs +update`（`--api-version v2`，Markdown） |
| **lark-drive** | `drive files patch` 改标题；`--folder-token`；`drive +search` |
| **lark-markdown** | 仅当同步 **Drive 原生 .md 文件** 时用；复盘默认走 **docx**（lark-doc） |
| **lark-im** | 可选：把报告链接发到群（非本 Skill 默认路径） |

完整 26 个 Skill 列表见官方 README。

## 命令层级（按需）

1. **快捷命令**（`+` 前缀，Agent 优先）：`lark-cli docs +update`、`calendar +agenda` …
2. **API 命令**：`lark-cli calendar calendars list`
3. **通用调用**：`lark-cli api GET /open-apis/...`

写 docx 正文用 **Shortcuts** `docs +update`，不要混用未评测的底层 API 除非 **lark-openapi-explorer** 已确认。

## 常用参数

| 参数 | 说明 |
|------|------|
| `--as user` / `--as bot` | 身份（复盘上传一般用 **user**） |
| `--dry-run` | 写操作前预览请求 |
| `--format json` / `table` | 输出格式 |
| `--page-all` | 自动翻页 |

## 安全（官方摘要）

- Agent 以授权用户身份操作，勿将机器人拉入不可信群聊
- 勿把 QMT `API_KEY`、账户明细写入公开文档
- 默认安全配置不建议随意关闭

## 排障

| 现象 | 处理 |
|------|------|
| 命令找不到 | 重装 `npx @larksuite/cli@latest install`，确认 `lark-cli` 在 PATH |
| scope 不足 | `lark-cli auth login --recommend` 或按 **lark-shared** 补 scope |
| Node 18 `ERR_REQUIRE_ESM` | 升级到 **Node 20+** 再执行 install |
| `--content @file` 失败 | 在**仓库根**执行，路径相对当前目录，如 `@reports/feishu_daily_eval.md` |
