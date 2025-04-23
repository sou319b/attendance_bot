import discord
import os
from discord.ext import commands
from dotenv import load_dotenv
import discord.ui
import json
import sqlite3
from datetime import datetime
import traceback

# .envファイルから環境変数を読み込む
load_dotenv()
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

if DISCORD_BOT_TOKEN is None:
    print("エラー: DISCORD_BOT_TOKENが設定されていません。")
    print(".envファイルを作成し、DISCORD_BOT_TOKEN='YOUR_BOT_TOKEN'のように記述してください。")
    exit()

# --- 定数 --- 
MESSAGE_FILE = "attendance_message.json"
DB_FILE = "attendance.db"

# --- データベース関連 --- 
def init_db():
    """データベースを初期化し、テーブルを作成する"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        user_name TEXT NOT NULL,
        action TEXT NOT NULL, -- 'attend' or 'leave'
        timestamp TEXT NOT NULL
    )
    """)
    conn.commit()
    conn.close()
    print(f"データベース {DB_FILE} を初期化しました。")

def log_attendance(user_id, user_name, action):
    """入退室ログをデータベースに記録する"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO attendance_log (user_id, user_name, action, timestamp) VALUES (?, ?, ?, ?)",
                   (user_id, user_name, action, timestamp))
    conn.commit()
    conn.close()
    print(f"ログ記録: {user_name} ({user_id}) が {action} しました ({timestamp})")

def get_current_attendees():
    """現在入室中のユーザーリストを取得する"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # 各ユーザーの最新ログを取得
    cursor.execute("""
    SELECT user_id, user_name, action
    FROM attendance_log
    WHERE id IN (
        SELECT MAX(id)
        FROM attendance_log
        GROUP BY user_id
    )
    ORDER BY timestamp DESC
    """)
    latest_logs = cursor.fetchall()
    conn.close()

    attendees = [log[1] for log in latest_logs if log[2] == 'attend'] # 最新が 'attend' のユーザー名
    return attendees

# --- メッセージID管理 --- 
def load_message_data():
    """メッセージデータをファイルから読み込む (辞書形式)"""
    try:
        with open(MESSAGE_FILE, 'r') as f:
            data = json.load(f)
            # キーを整数から文字列に変換している場合があるため、文字列キーで統一
            return {str(k): v for k, v in data.items()}
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        print(f"警告: {MESSAGE_FILE} の内容が不正です。空のデータとして扱います。")
        return {}

def save_message_data(data):
    """メッセージデータ全体をファイルに保存する (辞書形式)"""
    with open(MESSAGE_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def add_or_update_message_data(channel_id, message_id):
    """指定されたチャンネルのメッセージIDを追加または更新する"""
    data = load_message_data()
    data[str(channel_id)] = message_id
    save_message_data(data)

def remove_message_data(channel_id):
    """指定されたチャンネルのメッセージデータを削除する"""
    data = load_message_data()
    removed = data.pop(str(channel_id), None)
    if removed:
        save_message_data(data)
        print(f"チャンネル {channel_id} のメッセージデータを削除しました。")
    return removed is not None

# --- Embed更新 --- 
async def update_attendance_message(bot, channel_id, message_id):
    """指定されたメッセージのEmbedを現在の入室状況で更新する"""
    channel_id_str = str(channel_id)
    message_id_int = int(message_id)
    channel_id_int = int(channel_id) # channel_id も整数に変換
    print(f"DEBUG: update_attendance_message 開始 (Channel: {channel_id_str}, Message: {message_id_int})")

    try:
        channel = bot.get_channel(channel_id_int)
        if not channel:
            print(f"エラー: チャンネル {channel_id_str} が見つかりません。データを削除します。")
            remove_message_data(channel_id_str)
            return False # 更新失敗
        print(f"DEBUG: チャンネル取得成功 (Channel: {channel.name})")
        message = await channel.fetch_message(message_id_int)
        print(f"DEBUG: メッセージ取得成功 (Message ID: {message.id})")
    except discord.NotFound:
        print(f"エラー: メッセージ {message_id_int} が見つかりません。データを削除します。")
        remove_message_data(channel_id_str)
        return False # 更新失敗
    except discord.Forbidden:
        print(f"エラー: チャンネル {channel.name} またはメッセージ {message_id_int} へのアクセス権がありません。データは維持されます。")
        return False # 更新失敗
    except Exception as e:
        print(f"メッセージ取得中に予期せぬエラー: {e}")
        traceback.print_exc()
        return False # 更新失敗

    try:
        print("DEBUG: get_current_attendees 呼び出し開始")
        attendees = get_current_attendees()
        print(f"DEBUG: get_current_attendees 完了 (取得件数: {len(attendees)})")
        embed = discord.Embed(title="入退室管理", color=discord.Color.blue())
        if attendees:
            embed.description = "\n".join([f"- {name}" for name in attendees])
            embed.add_field(name="現在の入室者", value=f"{len(attendees)} 名", inline=False)
        else:
            embed.description = "現在、入室者はいません。"

        try:
            await message.edit(content=None, embed=embed, view=AttendanceView()) # Viewも再適用
            print(f"メッセージ ({message.id}) のEmbedを更新しました。現在の入室者: {len(attendees)}名")
            return True # 更新成功
        except discord.Forbidden:
            print(f"エラー: メッセージ {message.id} の編集権限がありません。")
            return False # 更新失敗
        except Exception as e:
            print(f"メッセージ編集中に予期せぬエラー: {e}")
            return False # 更新失敗
    except Exception as e:
        print(f"get_current_attendees 実行中に予期せぬエラー: {e}")
        return False # 更新失敗

# --- インテントとボット設定 --- 
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

# --- 入退室ボタン View --- 
class AttendanceView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def update_embed(self, interaction: discord.Interaction):
        """現在のインタラクションのメッセージのEmbedを更新するヘルパー関数"""
        # 管理対象のメッセージかどうかは update_attendance_message 内で判断される
        await update_attendance_message(interaction.client, interaction.channel.id, interaction.message.id)

    @discord.ui.button(label="入室", style=discord.ButtonStyle.success, custom_id="attend_button")
    async def attend(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        await interaction.response.defer(ephemeral=True, thinking=False)
        log_attendance(user.id, user.display_name, 'attend')
        await interaction.followup.send(f'{user.display_name}さんが入室しました。', ephemeral=True)
        await self.update_embed(interaction) # Embedを更新

    @discord.ui.button(label="退出", style=discord.ButtonStyle.danger, custom_id="leave_button")
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        await interaction.response.defer(ephemeral=True, thinking=False)
        log_attendance(user.id, user.display_name, 'leave')
        await interaction.followup.send(f'{user.display_name}さんが退出しました。', ephemeral=True)
        await self.update_embed(interaction) # Embedを更新

# --- ボットイベントハンドラ --- 
@bot.event
async def on_ready():
    init_db() # DB初期化
    print(f'{bot.user.name} としてログインしました')
    print('------')
    bot.add_view(AttendanceView()) # Viewを登録 (ボタン押下に対応するため)

    # 保存された全メッセージIDのEmbedを更新
    message_data = load_message_data()
    if message_data:
        print(f"{len(message_data)} 件の管理メッセージを更新します...")
        # イテレーション中に辞書を変更する可能性があるのでキーをコピー
        for channel_id_str, message_id in list(message_data.items()):
            print(f"  チャンネル {channel_id_str} のメッセージ {message_id} を更新中...", end="")
            success = await update_attendance_message(bot, channel_id_str, message_id)
            print(" 完了" if success else " スキップ/失敗")
        print("管理メッセージの更新が完了しました。")

# --- ボットコマンド --- 
@bot.command()
async def ping(ctx):
    await ctx.send(f'Pong! {round(bot.latency * 1000)}ms')

@bot.command()
async def hello(ctx):
    await ctx.send('こんにちは！')

@bot.command()
async def attendance(ctx):
    """現在のチャンネルに入退室管理メッセージを表示/更新するコマンド"""
    channel_id_str = str(ctx.channel.id)
    message_data = load_message_data()
    existing_message_id = message_data.get(channel_id_str)

    # 既存メッセージがある場合 -> 更新を試みる
    if existing_message_id:
        print(f"チャンネル {channel_id_str} の既存メッセージ ({existing_message_id}) を更新します。")
        success = await update_attendance_message(bot, channel_id_str, existing_message_id)
        if success:
            await ctx.send("入退室管理メッセージを更新しました。", delete_after=5)
        else:
            # 更新に失敗した場合（メッセージが見つからない等でデータ削除された可能性）
            # 新規作成を試みる
            print(f"既存メッセージの更新に失敗したため、新規作成を試みます。")
            existing_message_id = None # 新規作成フラグ
            # 再度loadしないと削除が反映されない
            message_data = load_message_data()
            existing_message_id = message_data.get(channel_id_str)

    # 新規作成が必要な場合 (existing_message_id が None)
    if existing_message_id is None:
        print(f"チャンネル {channel_id_str} に新しい入退室管理メッセージを作成します。")
        initial_embed = discord.Embed(title="入退室管理", description="読み込み中...", color=discord.Color.light_grey())
        view = AttendanceView()
        try:
            new_message = await ctx.send(embed=initial_embed, view=view)
            add_or_update_message_data(ctx.channel.id, new_message.id)
            print(f"新しいメッセージ (ID: {new_message.id}) を作成し、情報を保存しました。")
            # 保存後にEmbed内容を更新
            await update_attendance_message(bot, ctx.channel.id, new_message.id)
        except discord.Forbidden:
             await ctx.send("エラー: このチャンネルにメッセージを送信またはEmbedを送信する権限がありません。", delete_after=10)
        except Exception as e:
             await ctx.send(f"メッセージ作成中に予期せぬエラーが発生しました: {e}", delete_after=10)

# --- ログ表示コマンド (オプション) --- 
@bot.command(name='showlog')
async def show_log(ctx, limit: int = 10):
    """直近の入退室ログを表示する (デフォルト10件)"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, user_name, action FROM attendance_log ORDER BY id DESC LIMIT ?", (limit,))
    logs = cursor.fetchall()
    conn.close()

    if not logs:
        await ctx.send("ログはまだありません。")
        return

    log_text = "\n".join([f"`{row[0]}`: {row[1]} - {row[2]}" for row in logs])
    embed = discord.Embed(title=f"入退室ログ (直近{len(logs)}件)", description=log_text, color=discord.Color.orange())
    await ctx.send(embed=embed)

# --- 管理メッセージ削除コマンド --- 
@bot.command(name='removeattendance')
@commands.has_permissions(manage_messages=True) # メッセージ管理権限がある人のみ実行可能
async def remove_attendance(ctx):
    """現在のチャンネルの入退室管理メッセージを削除するコマンド"""
    channel_id_str = str(ctx.channel.id)
    message_data = load_message_data()
    message_id = message_data.get(channel_id_str)

    if not message_id:
        await ctx.send("このチャンネルには入退室管理メッセージは設定されていません。", delete_after=10)
        return

    # メッセージを削除
    try:
        message = await ctx.channel.fetch_message(message_id)
        await message.delete()
        print(f"メッセージ (ID: {message_id}) を削除しました。")
    except discord.NotFound:
        print(f"削除対象のメッセージ (ID: {message_id}) が見つかりませんでした。データのみ削除します。")
    except discord.Forbidden:
        await ctx.send("エラー: このチャンネルのメッセージを削除する権限がありません。", delete_after=10)
        return # データ削除は行わない
    except Exception as e:
        await ctx.send(f"メッセージ削除中にエラーが発生しました: {e}", delete_after=10)
        return # データ削除は行わない

    # データを削除
    if remove_message_data(channel_id_str):
        await ctx.send("入退室管理メッセージを削除しました。", delete_after=10)
    else:
        # remove_message_data 内でエラーが出ることは稀だが念のため
        await ctx.send("メッセージは削除されましたが、データファイルの更新に問題が発生した可能性があります。", delete_after=10)

@remove_attendance.error
async def remove_attendance_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("このコマンドを実行するにはメッセージ管理権限が必要です。", delete_after=10)
    else:
        await ctx.send(f"コマンド実行中にエラーが発生しました: {error}", delete_after=10)

# ボットを実行
bot.run(DISCORD_BOT_TOKEN)
