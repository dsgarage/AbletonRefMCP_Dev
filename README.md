# AbletonRefMCP — Ableton リファレンス・ワークフロー MCP サーバー

Ableton Live / Move / Push 3 / Note / Max for Live (LOM) の日英バイリンガル対応リファレンス・ワークフロー相談 MCP サーバー。
Claude Code / Claude Desktop から自然言語でデバイス仕様・ハードウェア機能・リリースノート・LOM・用語集を検索できます。

```
Claude → AbletonRefMCP（調べる：Live/Move/Push/Note/M4L）
       → MaxRefMCP（調べる：Max/MSP）  ← 姉妹サーバー
       → MaxMCP（作る：Max パッチ操作）
```

---

## ツール一覧

### デバイス検索（3）
| ツール | 説明 |
|--------|------|
| `ableton.search_device` | Live/Move/Push のデバイス検索（楽器・エフェクト・ラック） |
| `ableton.get_device` | デバイス詳細（available_on / parameters / 注意事項） |
| `ableton.compare_devices` | 2〜5 デバイスの比較 |

### ハードウェア（2）
| ツール | 説明 |
|--------|------|
| `ableton.search_hardware` | Move / Push 3 / Note の機能・バージョン履歴を検索 |
| `ableton.get_hardware` | 製品仕様の取得（version 指定可、Move 1.x vs 2.0 の差分など） |

### リリースノート / ニュース（3）
| ツール | 説明 |
|--------|------|
| `ableton.release_notes` | Live/Move/Note のリリースノートを横断検索（ローカル DB） |
| `ableton.release_notes_page` | ableton.com のリリースノートページから最新版を取得（Web） |
| `ableton.official_news` | ableton.com/blog の最新記事一覧（Web） |
| `ableton.read_article` | 個別記事の本文を取得（ableton.com / help.ableton.com URL） |

### LOM (Live Object Model)（2）
| ツール | 説明 |
|--------|------|
| `ableton.lom_search` | LOM クラス検索（Track, Clip, Device, Scene, …） |
| `ableton.lom_get` | LOM クラス詳細（プロパティ・メソッド・親クラス） |

### ワークフロー / 用語（3）
| ツール | 説明 |
|--------|------|
| `ableton.search_pattern` | ワークフローパターン検索（"Move でループを Audio Track に置く" 等） |
| `ableton.suggest_approach` | やりたいことに対する手順提案（制約条件考慮） |
| `ableton.glossary` | 用語の日英辞書（warp, clip, scene, …） |

### フィードバック / 計測（3）
| ツール | 説明 |
|--------|------|
| `ableton.report_bug` | バグ報告 → AbletonRefMCP_Dev に Issue 自動作成 |
| `ableton.request_feature` | 機能リクエスト → 同上 |
| `ableton.analytics` | API 利用状況サマリー |

> `report_bug` / `request_feature` の利用には `GITHUB_TOKEN` 環境変数が必要。未設定時は手動作成用の URL を返します。

---

## セットアップ

### ローカル起動

```bash
pip install -r requirements.txt
python core.py
# → http://localhost:8001/mcp
```

ポートは `PORT` 環境変数で変更可能（デフォルト 8001、MaxRefMCP の 8000 と衝突回避）。

### Claude Code / Claude Desktop で使う

`~/.claude.json` または `claude_desktop_config.json` に追加:

```json
{
  "mcpServers": {
    "ableton-ref": {
      "url": "http://localhost:8001/mcp"
    }
  }
}
```

---

## データソース

Phase 1 では最小シードデータを同梱しています。
- `device-db.json` — Live / Move 主要デバイス 10 種
- `hardware-db.json` — Move 1.x / 2.0、Push 3、Note の最小スペック
- `release-notes-db.json` — Move 2.0 / Live 12.4 / Note の最新リリースノート
- `lom-db.json` — LOM 主要クラス 8 種（Application, Song, Track, Clip, …）
- `glossary-db.json` — Ableton 用語 12 種
- `pattern-db.json` — ワークフロー 5 種

Phase 2 で公式マニュアル / Help Center / リリースノート全件の ingest を予定。

## 開発状況

- **Phase 1 (進行中)**: スケルトン + 最小シードデータで動作確認
- Phase 2: 公式マニュアル / Help Center / リリースノート全件 ingest
- Phase 3: Railway デプロイ + 公開 MCP 設定

## ライセンス

MIT
