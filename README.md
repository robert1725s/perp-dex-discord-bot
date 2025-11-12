# Perp DEX Discord通知BOT

複数のPerpetual DEX（分散型永久先物取引所）の市場データを定期的に監視し、取引機会をDiscordに自動通知するBOTです。

## 📊 プロジェクト概要

このBOTは、複数の取引所から市場データを並列取得し、Funding Rate（資金調達率）の差やOpen Interest（建玉）比率を分析して、収益機会を自動検出します。

### 主な特徴

- **マルチ取引所対応**: Extended（Starknet）、Lighter（zkSync）など複数の取引所に対応
- **リアルタイム分析**: 非同期処理による高速なデータ取得と分析
- **柔軟なスケジューリング**: Cron形式で自由に実行タイミングを設定可能
- **拡張性**: ファクトリーパターンにより新しい取引所を簡単に追加可能
- **堅牢性**: エラーハンドリングとリトライロジックによる安定動作

## 🎯 機能

### 市場分析機能

1. **Funding Rate差分析**
   - 2つの取引所間のFR差を検出
   - 取引高でフィルタリング
   - 差の大きい順にランキング表示

2. **OI比率分析**
   - Open Interest / Volume 比率を計算
   - 取引高範囲でフィルタリング
   - 低OI比率（流動性機会）を検出

3. **共通ペア管理**
   - 複数取引所の共通取引ペアを自動抽出
   - 日次更新またはスタートアップ時更新
   - キャッシュによる高速化

### 通知機能

- **Discord Webhook通知**
  - リッチなEmbed形式のメッセージ
  - テーブル形式の見やすい表示
  - エラー通知機能

## サポートされている取引所

- Extended (Starknet)
- Lighter (zkSync)

## プロジェクト構成

```
perp-dex-discord-bot/
├── config.yaml              # 設定ファイル
├── main.py                  # メインエントリポイント
├── scheduler.py             # スケジューラー管理
├── requirements.txt         # Python依存関係
│
├── core/                    # コアロジック
│   ├── analyzer.py          # データ分析ロジック
│   ├── common_pairs.py      # 共通ペア管理
│   └── types.py            # 型定義
│
├── exchanges/               # 取引所実装
│   ├── base.py             # 抽象基底クラス
│   ├── extended.py         # Extended取引所実装
│   ├── lighter.py          # Lighter取引所実装
│   └── factory.py          # 取引所ファクトリー
│
├── notifiers/              # 通知実装
│   ├── discord.py          # Discord通知
│   └── formatter.py        # メッセージフォーマット
│
└── storage/                # データ永続化
    └── cache.py            # 共通ペアキャッシュ
```

## セットアップ

### 1. 環境準備

Python 3.9以上が必要です。

```bash
# 仮想環境の作成
python -m venv venv

# 仮想環境の有効化
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 依存関係のインストール
pip install -r requirements.txt
```

### 2. 環境変数の設定

`.env`ファイルをプロジェクトルートに作成：

```bash
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_URL
```

### 3. 設定ファイルの編集

`config.yaml`を編集して、分析パラメータや通知スケジュールをカスタマイズします。

## 使用方法

### コマンドラインオプション

```bash
# ヘルプを表示
python main.py --help

# 通常起動（スケジュール実行）
python main.py

# テストモード（1回だけ実行）
python main.py --once

# カスタム設定ファイルを使用
python main.py --config my_config.yaml

# バージョン表示
python main.py --version
```

### Discord Webhookの取得方法

1. Discordサーバー設定を開く
2. 「連携サービス」→「ウェブフック」に移動
3. 「新しいウェブフック」をクリック
4. Webhook URLをコピーして`.env`ファイルに設定

### 実行例

```bash
# 1. 環境変数を設定
export DISCORD_WEBHOOK_URL='https://discord.com/api/webhooks/...'

# 2. テスト実行（1回だけ）
python main.py --once

# 3. 正常動作を確認後、本番起動
python main.py
```

### スケジュール設定

`config.yaml`で以下の設定が可能です：

- **通知スケジュール**: Cron形式で指定（例: `45 * * * *` = 毎時45分）
- **取引所の有効/無効**: `enabled: true/false`
- **分析パラメータ**: 最小取引高、上位件数など
- **ログレベル**: DEBUG, INFO, WARNING, ERROR

#### スケジュール例

```yaml
schedule:
  common_pairs_update: "daily"  # 共通ペア更新: daily or startup
  notification_time: "45 * * * *"  # 毎時45分に通知

# その他の例:
# "0 * * * *"   - 毎時0分
# "0 9 * * *"   - 毎日9:00
# "0 9,21 * * *" - 毎日9:00と21:00
# "0 0 * * 1"   - 毎週月曜日0:00
```

### ログの確認

```bash
# ログファイルを確認
tail -f logs/bot.log

# リアルタイムでログを確認
python main.py  # 標準出力にもログが表示されます
```

## ⚙️ 設定の詳細

### config.yaml の主要パラメータ

#### スケジュール設定

```yaml
schedule:
  # 共通ペアの更新頻度
  common_pairs_update: "daily"  # daily（毎日0:00）または startup（起動時のみ）

  # 市場分析と通知の実行時刻（Cron形式）
  notification_time: "45 * * * *"  # 毎時45分
```

#### 分析パラメータ

```yaml
analysis:
  # Funding Rate差分析
  fr_divergence:
    min_volume_usd: 1000000  # 最小取引高（1M USD）
    top_n: 5                  # 上位何件を通知するか

  # OI比率分析
  oi_ratio:
    min_volume_usd: 10000000  # 最小取引高（10M USD）
    max_volume_usd: 30000000  # 最大取引高（30M USD）
    top_n: 3                   # 上位何件を通知するか
    base_exchange: "Extended"  # 分析対象の取引所
```

#### ログ設定

```yaml
logging:
  level: "INFO"         # DEBUG, INFO, WARNING, ERROR
  file: "logs/bot.log"  # ログファイルパス
```

## 🔧 トラブルシューティング

### よくある問題と解決方法

#### 1. 環境変数エラー

**エラー**: `Environment variable 'DISCORD_WEBHOOK_URL' is not set`

**解決方法**:
```bash
# .envファイルを作成
cp .env.example .env

# .envファイルを編集してWebhook URLを設定
echo "DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN" > .env
```

#### 2. モジュールが見つからない

**エラー**: `ModuleNotFoundError: No module named 'apscheduler'`

**解決方法**:
```bash
# 依存関係を再インストール
pip install -r requirements.txt

# または個別にインストール
pip install APScheduler aiohttp PyYAML python-dotenv
```

#### 3. Discord通知が送信されない

**症状**: ログに「Failed to send Discord notification」と表示される

**解決方法**:
1. Webhook URLが正しいか確認
   ```bash
   # Webhook URLの形式を確認
   echo $DISCORD_WEBHOOK_URL
   # 正しい形式: https://discord.com/api/webhooks/ID/TOKEN
   ```

2. ネットワーク接続を確認
   ```bash
   # テスト通知を送信
   python test_discord_webhook.py
   ```

3. Discordサーバーの権限を確認
   - Webhookが削除されていないか
   - サーバーの権限設定が正しいか

#### 4. API呼び出しエラー

**エラー**: `Failed to fetch markets from Extended`

**解決方法**:
1. ネットワーク接続を確認
2. 取引所APIのステータスを確認
3. レート制限に達していないか確認（config.yamlのrate_limitを調整）

```yaml
exchanges:
  - name: "Extended"
    config:
      rate_limit: 500  # 低い値に変更してテスト
```

#### 5. 共通ペアが見つからない

**症状**: `No common pairs found`

**解決方法**:
1. 各取引所が正常にデータを取得できているか確認
   ```bash
   # テストモードで実行
   python main.py --once
   ```

2. ログで各取引所の取得マーケット数を確認
   ```
   INFO - Fetched 91 markets from Extended
   INFO - Fetched 102 markets from Lighter
   ```

3. シンボル正規化が正しく動作しているか確認

#### 6. スケジューラーが動作しない

**症状**: ジョブが実行されない

**解決方法**:
1. Cron表記が正しいか確認
   ```yaml
   # 正しい形式: "分 時 日 月 曜日"
   notification_time: "45 * * * *"  # ✓ 正しい
   notification_time: "every hour"   # ✗ 間違い
   ```

2. スケジューラーのログを確認
   ```bash
   tail -f logs/bot.log | grep "SCHEDULED JOBS"
   ```

3. タイムゾーンを確認（スケジューラーはUTCを使用）

### ログレベルの変更

問題を詳しく調査する場合は、ログレベルをDEBUGに変更：

```yaml
logging:
  level: "DEBUG"  # 詳細なログを出力
```

## 🔌 新しい取引所の追加方法

新しい取引所を追加する詳細な手順です。

### ステップ1: 取引所クラスの実装

`exchanges/newexchange.py` を作成:

```python
"""NewExchange implementation."""

import aiohttp
from typing import List, Dict
from .base import BaseExchange


class NewExchange(BaseExchange):
    """NewExchange実装"""

    def __init__(self, config: Dict):
        super().__init__(config)
        self.timeout = aiohttp.ClientTimeout(total=30)

    async def get_markets(self) -> List[Dict]:
        """
        マーケット情報を取得

        Returns:
            List[Dict]: マーケットデータのリスト
        """
        url = f"{self.api_base_url}/markets"

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(url) as response:
                data = await response.json()

                # データを標準形式に変換
                markets = []
                for item in data['markets']:
                    markets.append({
                        'symbol': self.normalize_symbol(item['symbol']),
                        'volume_24h': float(item['volume']),
                        'funding_rate': float(item['fundingRate']),
                        'open_interest': float(item['openInterest']),
                        'last_price': float(item['price'])
                    })

                return markets

    def normalize_symbol(self, raw_symbol: str) -> str:
        """
        シンボルを正規化

        Args:
            raw_symbol: 取引所固有のシンボル（例: "BTCUSD"）

        Returns:
            str: 正規化されたシンボル（例: "BTC-USD"）
        """
        # 例: "BTCUSD" -> "BTC-USD"
        if raw_symbol.endswith('USD'):
            base = raw_symbol[:-3]
            return f"{base}-USD"
        return raw_symbol
```

### ステップ2: ファクトリーに登録

`exchanges/factory.py` を編集:

```python
from .newexchange import NewExchange  # インポート追加

class ExchangeFactory:
    _registry: Dict[str, Type[BaseExchange]] = {
        'extended': ExtendedExchange,
        'lighter': LighterExchange,
        'newexchange': NewExchange,  # 追加
    }
```

### ステップ3: 設定ファイルに追加

`config.yaml` を編集:

```yaml
exchanges:
  - name: "NewExchange"
    type: "newexchange"      # factory.pyのキーに対応
    enabled: true
    api_base_url: "https://api.newexchange.com/v1"
    config:
      rate_limit: 1000        # 取引所のレート制限に合わせて調整
```

### ステップ4: テスト

```bash
# テストモードで実行
python main.py --once

# ログで確認
# "Initialized exchange: NewExchange" と表示されればOK
```

### 実装のポイント

1. **データ形式の統一**
   - `get_markets()`は必ず標準形式で返す
   - `symbol`, `volume_24h`, `funding_rate`, `open_interest`は必須

2. **エラーハンドリング**
   - API呼び出しは必ずtry-exceptで囲む
   - リトライロジックを実装する

3. **シンボル正規化**
   - 全ての取引所で統一された形式（例: "BTC-USD"）を使用
   - `normalize_symbol()`で各取引所の形式を変換

4. **レート制限の遵守**
   - 各取引所のAPI制限を確認
   - `config.rate_limit`で制御

### テスト用コード

```python
# exchanges/newexchange.py の最後に追加
if __name__ == '__main__':
    import asyncio
    import logging

    logging.basicConfig(level=logging.INFO)

    async def test():
        config = {
            'name': 'NewExchange',
            'api_base_url': 'https://api.newexchange.com/v1',
            'config': {'rate_limit': 1000}
        }

        exchange = NewExchange(config)
        markets = await exchange.get_markets()

        print(f"Fetched {len(markets)} markets")
        for market in markets[:3]:
            print(market)

    asyncio.run(test())
```

実行:
```bash
python -m exchanges.newexchange
```

## 📚 技術仕様

詳細な技術仕様は`doc/SPECIFICATION.md`を参照してください。

## 🤝 コントリビューション

プルリクエストを歓迎します！以下の流れで貢献してください：

1. このリポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## 📄 ライセンス

MIT License

## ⚠️ 免責事項・注意事項

- **投資助言ではありません**: このBOTは情報提供のみを目的としており、投資助言や推奨ではありません
- **APIレート制限**: 各取引所のAPIレート制限を必ず遵守してください
- **セキュリティ**: Discord Webhook URLは絶対に公開しないでください
- **自己責任**: 本BOTの使用による損失について、開発者は一切の責任を負いません
- **テスト**: 本番環境で使用する前に、必ずテストモードで動作確認してください

## 📞 サポート

問題が発生した場合：

1. まず[トラブルシューティング](#🔧-トラブルシューティング)を確認
2. それでも解決しない場合はIssueを作成
3. ログファイル（`logs/bot.log`）を添付すると解決が早くなります

---

**Happy Trading! 📈**
