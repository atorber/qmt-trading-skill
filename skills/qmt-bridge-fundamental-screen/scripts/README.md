# qmt-bridge-fundamental-screen 脚本

| 脚本 | 状态 | 说明 |
|------|------|------|
| `screen_financial.py` | ✅ | 财报筛选；默认缺数自动下载 |

仅下载财报 → [financial-download](../../qmt-bridge-financial-download/SKILL.md)

```bash
python skills/qmt-bridge-fundamental-screen/scripts/screen_financial.py --host 127.0.0.1 --port 8080 \
  --codes 688008.SH,603986.SH --table Pershareindex --field roe --min 5
```

| 常用参数 | |
|----------|--|
| `--from-positions` | 用当前持仓代码筛选 |
| `--download` | 强制刷新后筛选 |
| `--no-if-missing` | 不自动补下载 |
| `--min 5` | ROE 等为百分点（5 = 5%） |
