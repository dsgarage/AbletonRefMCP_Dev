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
    "ableton-ref-mcp": {
      "type": "http",
      "url": "http://localhost:8001/mcp"
    }
  }
}
```

公開 URL に切替えるユーティリティ:

```bash
# localhost dev
python3 scripts/switch_mcp_url.py http://localhost:8001/mcp

# Railway 直接
python3 scripts/switch_mcp_url.py https://abletonrefmcp-production.up.railway.app/mcp

# 現状確認のみ
python3 scripts/switch_mcp_url.py --show
```

### Railway デプロイ

1. [railway.app](https://railway.app) にログイン → New Project → Deploy from GitHub
2. リポジトリ `dsgarage/AbletonRefMCP_Dev` を選択（develop ブランチを選ぶ）
3. Dockerfile が自動検出される（`railway.toml` で builder=DOCKERFILE 指定済み）
4. Settings → Variables で必要に応じて `GITHUB_TOKEN` を追加（report_bug / request_feature ツール用、未設定でも MCP 自体は動作）
5. Settings → Networking → Generate Domain で公開 URL を発行
6. ローカルで切替:
   ```bash
   python3 scripts/switch_mcp_url.py https://<your-railway-domain>/mcp
   ```
7. Claude Code を再起動

Railway は実行時に `PORT` 環境変数を動的に割り当てるので、Dockerfile の `ENV PORT=8001` はローカル開発のデフォルト用、本番では Railway 側が上書きします。

---

## データソース

- `device-db.json` — Live / Move 主要デバイス
- `hardware-db.json` — Move 1.x / 2.0、Push 3、Note のスペック
- `release-notes-db.json` — Live 12 / Move 1.x〜2.0 / Note 1.x〜2.0 のリリースノート（70 件超、ingest 済み）
- `lom-db.json` — LOM 主要クラス 8 種（Application, Song, Track, Clip, …）
- `glossary-db.json` — Ableton 用語
- `pattern-db.json` — ワークフローパターン

## ingest スクリプト

`scripts/` 配下に取得スクリプトを置いてあります。

```bash
# ableton.com の release notes を全件取得して JSON にマージ
python3 scripts/ingest_release_notes.py            # ドライラン
python3 scripts/ingest_release_notes.py --write    # 実書き込み

# Live マニュアルのデバイス TOC（Phase 2.5 で再実装予定 / 現状 0 件）
python3 scripts/ingest_devices.py

# help.ableton.com (Zendesk Help Center) からの記事一覧
python3 scripts/ingest_help_center.py --search Move
python3 scripts/ingest_help_center.py --write
```

`ingest_release_notes.py` は手書き翻訳済みの `title_ja` / `highlights_ja` を保持したまま、英語の追加 highlights を `highlights_en_ingested` に追加するマージ動作です。

## 開発状況

- **Phase 1 (進行中)**: スケルトン + 最小シードデータで動作確認
- Phase 2: 公式マニュアル / Help Center / リリースノート全件 ingest
- Phase 3: Railway デプロイ + 公開 MCP 設定

## ライセンス

MIT
