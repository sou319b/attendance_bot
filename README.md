# Discord 入退室管理ボット

多機能なDiscordボットです。入退室管理、ログ記録、複数チャンネル対応などの機能を備えています。

## 機能

*   **入退室管理:**
    *   「入室」「退出」ボタンによる簡単な操作。
    *   Embedメッセージ内に現在の入室者リストをリアルタイム表示。
*   **ログ記録:**
    *   SQLiteデータベース (`attendance.db`) にユーザーID、ユーザー名、アクション（入室/退出）、タイムスタンプを記録。
    *   `!showlog` コマンドで記録されたログの表示が可能。
*   **複数チャンネル対応:**
    *   `!attendance` コマンドを実行した各チャンネルで、独立して入退室管理メッセージを管理。
    *   管理情報は `attendance_message.json` に保存。
*   **その他コマンド:**
    *   `!ping`: ボットの応答速度を確認。
    *   `!hello`: 簡単な挨拶を返す。

## 必要なもの

*   Python 3.8 以降
*   Discordアカウントとボットアプリケーション

## セットアップと実行方法

1.  **リポジトリのクローン (またはファイルのダウンロード):**
    ```bash
    # 必要に応じてリポジトリをクローン
    # git clone <repository_url>
    # cd <repository_directory>
    ```

2.  **依存関係のインストール:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **ボットトークンの設定:**
    *   プロジェクトルートに `.env` という名前のファイルを作成します。
    *   `.env` ファイル内に以下のように記述し、`YOUR_BOT_TOKEN_HERE` を実際のボットトークンに置き換えます。
        ```dotenv
        DISCORD_BOT_TOKEN='YOUR_BOT_TOKEN_HERE'
        ```
    *   ボットトークンは [Discord Developer Portal](https://discord.com/developers/applications) で取得できます。

4.  **Discord Developer Portalでの設定:**
    *   [Discord Developer Portal](https://discord.com/developers/applications) でボットのアプリケーションを選択します。
    *   左メニューの「Bot」セクションに移動します。
    *   **「Privileged Gateway Intents」** の項目で、以下の **両方** を有効 (トグルをオン) にします。
        *   **MESSAGE CONTENT INTENT**
        *   **SERVER MEMBERS INTENT**
    *   変更を保存します。

5.  **ボットの実行:**
    ```bash
    python discord_bot.py
    ```
    *   ボットが起動すると、コンソールにログが表示され、`attendance.db` (データベースファイル) と `attendance_message.json` (管理メッセージ情報ファイル) が必要に応じて作成されます。

## 使い方

1.  **入退室管理の開始:**
    *   入退室管理を行いたいDiscordチャンネルで、 `!attendance` と入力します。
    *   ボットがEmbedメッセージ（現在の入室者リストを表示）と「入室」「退出」ボタンを投稿します。
    *   この操作は、管理を行いたい各チャンネルで個別に行う必要があります。

2.  **入退室の記録:**
    *   チャンネルに表示された「入室」または「退出」ボタンをクリックします。
    *   クリックした本人にのみ一時的な確認メッセージが表示されます。
    *   Embedメッセージの入室者リストが更新されます。
    *   `attendance.db` にアクションが記録されます。

3.  **ログの確認:**
    *   `!showlog` と入力すると、直近10件の入退室ログが表示されます。
    *   `!showlog 20` のように、表示する件数を指定することもできます。

4.  **入退室管理の終了:**
    *   管理メッセージを削除したいチャンネルで `!removeattendance` と入力します。
    *   ボットが投稿したEmbedメッセージとボタンが削除され、関連データもクリアされます。
    *   **注意:** このコマンドを実行するには、Discordの「メッセージの管理」権限が必要です。

5.  **その他のコマンド:**
    *   `!ping`: ボットがオンラインか、応答速度はどのくらいかを確認できます。
    *   `!hello`: ボットが挨拶を返します。 