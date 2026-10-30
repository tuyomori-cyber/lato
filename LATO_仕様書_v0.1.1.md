# LATO 仕様書 v0.1.1

- 文書バージョン：0.1.1
- 作成日：2026-10-30
- 状態：MVP実装向け仕様確定
- 仮称：LATO（Local Access Touch）
- 対象：Firefox拡張／Linux（Foxbookでのタッチ操作を主用途とする）

## 1. 目的と範囲

LATOは、端末に設定された単一のローカルルート配下をタッチで辿り、Markdown（`.md`）文書を閲覧する読み取り専用Firefox拡張である。ファイル管理一般ではなく「探す・読む・パスをコピーする」に特化する。

MVPでは、フォルダ移動、Markdown表示、拡張内タブ、ローカルMarkdownリンク、文書の絶対パス・親ディレクトリの絶対パス・ファイル名のコピーを提供する。編集・保存、ファイル操作、PDFなどMarkdown以外の閲覧、外部Webの閲覧は対象外とする。

## 2. ルート設定と端末別管理

- ルートディレクトリは端末ごとにNative Messaging Hostの設定で固定する。Firefoxアカウントを共有しても他端末の設定を引き継がない。
- MVPでは単一ルートとし、拡張の設定画面および拡張からの要求でルートを変更できない。初期設定・変更はHost設定を保守作業で更新する。
- Host設定は`~/.config/lato/config.json`に置き、所有者だけが変更できるようにする。

```json
{
  "version": 1,
  "root_path": "/home/user/project"
}
```

- `browser.storage.local`はルートの正本として使わない。画面状態、直近の相対パス、内部タブ状態など、認可範囲を変えない状態だけを端末ローカルに保存する。
- 拡張はルートの絶対パスを指定せず、ルートからの相対パスだけをHostへ送る。

## 3. Native Messaging Host

- Host名は`org.foxbook.lato`、FirefoxアドオンIDは`lato@foxbook.local`で固定する。
- Host manifestはLinuxのFirefox用Native Messaging Host配置場所に導入し、`allowed_extensions`には`lato@foxbook.local`だけを登録する。
- 拡張は`browser.runtime.sendNativeMessage()`を使う。Hostは要求ごとに起動するステートレスな読み取り専用プロセスとする。
- 拡張の最小権限は`nativeMessaging`、`storage`、`tabs`とする。`clipboardWrite`は初期実機検証で不要と確認できるまで追加しない。
- Hostは標準出力へNative Messagingの応答以外を書き込まない。診断ログは標準エラーへ出力する。

### 3.1 固定操作と応答

| 操作 | 入力 | 成功時の結果 |
| --- | --- | --- |
| `list_directory` | 相対ディレクトリパス | フォルダとMarkdownファイルの一覧 |
| `read_markdown` | 相対`.md`ファイルパス | UTF-8本文とコピー用パス情報 |

要求は次の共通形式とする。

```json
{
  "version": 1,
  "request_id": "UUID",
  "operation": "list_directory",
  "relative_path": "docs"
}
```

`read_markdown`の成功応答には、本文とコピー用情報を含める。

```json
{
  "ok": true,
  "request_id": "UUID",
  "result": {
    "relative_path": "docs/spec.md",
    "content": "# Spec\n",
    "path_info": {
      "absolute_path": "/home/user/project/docs/spec.md",
      "parent_absolute_path": "/home/user/project/docs",
      "file_name": "spec.md"
    }
  }
}
```

失敗時は`INVALID_REQUEST`、`INVALID_PATH`、`OUTSIDE_ROOT`、`NOT_FOUND`、`NOT_A_DIRECTORY`、`NOT_A_MARKDOWN_FILE`、`SYMLINK_NOT_ALLOWED`、`READ_FAILED`、`FILE_TOO_LARGE`、`DIRECTORY_TOO_LARGE`、`INVALID_ENCODING`の固定エラーコードを返す。

### 3.2 サイズとパスの制約

- Markdown本文の上限は512 KiBとする。上限を超える場合は`FILE_TOO_LARGE`を返し、本文の一部を返さない。
- 一覧は最大1,000件とする。上限を超えるディレクトリは明示的なエラーとして扱う。
- 相対パスはルートを表す空文字列、または通常の相対パスだけを許可する。絶対パス、`..`、NUL文字、空要素を拒否する。
- Hostはルートと対象を実パスに正規化して比較し、ルート外を拒否する。シンボリックリンクは一覧・読取ともに拒否する。
- 隠しファイル・隠しディレクトリはMVPでは表示しない。

## 4. Markdown表示とリンク

- MarkdownのHTML変換には既存ライブラリを同梱して使い、外部CDNに依存しない。生HTMLはMVPでは無効化し、変換後HTMLもサニタイズする。
- 相対パスによる`.md`文書間リンク、同一文書の見出しアンカー、別文書のアンカー移動を対象とする。リンク先は現在の文書から解決し、Hostのパス検証が成功した場合だけ遷移する。
- 同一文書の`#anchor`は現在の内部タブを維持し、該当見出しまでスクロールする。
- 別文書へのリンクは、同じ解決済み相対パスの内部タブが開いていればそのタブを選択し、開いていなければ新しい内部タブで開く。リンクにアンカーがあれば、選択または新規作成したタブで該当見出しまでスクロールする。
- リンク遷移によって現在の内部タブを別文書へ置き換えない。
- 外部URLは開かず、対象外であることを利用者に通知する。画像などMarkdown以外の埋め込みリソースはMVP対象外とする。

## 5. 拡張内タブとUI

- ツールバーボタンからLATO用のFirefoxタブを開く。既存のLATOタブがあれば再利用する。
- 文書を一覧から開く際も、同じ解決済み相対パスの内部タブがあれば選択し、なければ新しい内部タブで開く。
- 内部タブは最大8件とする。閉じた場合は左隣を選択し、文書タブが残らなければ探索画面を表示する。
- 新規内部タブは探索状態から始める。文書ごとのスクロール位置は、LATOのFirefoxタブを開いている間だけ保持する。Firefox再起動後の復元はMVP対象外とする。
- タッチ操作を前提に十分なタップ領域を確保する。フォルダ一覧、ビューアー、内部タブ、コピー用メニューを備える。具体的な画面レイアウトは実機MVPで決める。

## 6. パスコピー

- 文書閲覧中にメニューから、文書の絶対パス、親ディレクトリの絶対パス、ファイル名をコピーできる。
- コピー値は`file://` URLではなく通常のLinux絶対パスとする。
- コピー操作は利用者の明示的なタップイベント内で実行し、成功・失敗を簡潔に通知する。
- 一覧上の項目でコピー操作を提供するかはMVP対象外とする。

## 7. MVP確認項目

- 端末ごとにHost設定の異なるルートで独立動作する。
- ルート外パス、`..`、絶対パス、シンボリックリンクを安全に拒否する。
- フォルダをタッチで辿り、通常のMarkdownを表示できる。
- 512 KiB超の文書を部分表示せず安全に扱う。
- 複数文書を内部タブで切り替え、Markdownリンクで既存タブの選択、新規タブ作成、アンカー移動ができる。
- 3種類のパスを正しくコピーできる。
- Host未導入、設定不備、権限拒否、存在しないファイル、読取エラー、UTF-8以外を安全に通知する。

以上をv0.1.1の基準とし、実機MVPの検証結果に応じて更新する。
