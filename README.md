# LATO

タッチ操作で固定されたローカルルート配下のMarkdownを閲覧する、読み取り専用Firefox拡張です。仕様の正本は[LATO仕様書 v0.1.1](LATO_仕様書_v0.1.1.md)、未完了事項は[TODO](TODO.md)です。

## 必要環境

- Linux版Firefox（Native Messagingを利用できる通常の導入形態）
- Python 3.12以降
- Node.js 18以降（拡張をビルドする場合）

## ビルド

```sh
npm install
npm run build
```

ビルド済み拡張は`dist/extension/`に出力されます。開発時はFirefoxの`about:debugging`から、このディレクトリの`manifest.json`を「一時的なアドオン」として読み込みます。

## Native Hostの導入

導入時に閲覧を許可する固定ルートを指定します。拡張からこのルートを変更することはできません。

```sh
python3 scripts/install_host.py \
  --root /absolute/path/to/markdown-root \
  --firefox /absolute/path/to/firefox
```

このコマンドは次をユーザー単位で配置します。

- `~/.local/share/lato/lato_host.py`
- `~/.config/lato/config.json`（モード`0600`、固定ルート）
- `~/.mozilla/native-messaging-hosts/org.foxbook.lato.json`

ルートを変更する場合は、同じコマンドを新しい`--root`で再実行します。指定先をよく確認してください。Hostは通常の`.md`だけを読み、シンボリックリンク、隠し項目、ルート外パスを拒否します。

## 利用

1. Native Hostを導入する。
2. `about:debugging`でLATO拡張を一時読み込みする。
3. ツールバーボタンからLATOを開く。
4. フォルダを辿り、Markdownをタップして閲覧する。

Markdown内の別文書リンクは既存の内部タブを再利用し、未表示の文書は新しい内部タブで開きます。同一文書の見出しリンクは現在のタブを維持します。

## テスト

```sh
npm test
npm run build
```

テストはHostのMarkdown読取、パストラバーサル拒否、シンボリックリンク拒否、512 KiB上限を検証します。実機でのFirefox・Native Messaging接続は別途確認します。
