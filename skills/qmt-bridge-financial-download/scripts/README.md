# qmt-bridge-financial-download 脚本

| 脚本 | 状态 | 说明 |
|------|------|------|
| `download_financial_data.py` | ✅ | 下载财报到服务端缓存；建议 `--verify` |

```bash
just agent-download-financial --host 127.0.0.1 --port 8080 \
  --codes 600584.SH,603986.SH --table Pershareindex --verify
```
