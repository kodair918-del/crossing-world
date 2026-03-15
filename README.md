# イキノコオリ（Thin Ice）デジタル試作

「1つのコードで完結させたい」という要望向けに、**`thin_ice.py` 1ファイル**で
ルールエンジン・AI・CLIをまとめた実装です。

## 実行

```bash
python thin_ice.py --players 4 --ai 3 --seed 42
```

## オプション

- `--players` : プレイヤー人数（2-4）
- `--ai` : 先頭からAI化する人数
- `--seed` : 乱数シード
- `--sun` : 太陽タイル枚数
- `--snow` : 雪タイル枚数

## 1ファイル構成の中身

- データモデル: `Tile`, `PlayerState`, `GameState`
- ゲームエンジン: `ThinIceGame`
  - 初期化
  - 合法手生成
  - 移動＋除去
  - 太陽/雪効果
  - 手番遷移
- AI:
  - `choose_ai_move`
  - `choose_ai_snow_placements`
- CLI:
  - `parse_args`
  - `main`

## テスト

```bash
pytest
```
