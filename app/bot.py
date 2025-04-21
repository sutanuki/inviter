import discord
from discord.ext import commands
from datetime import datetime
import asyncio
import json
import os
import requests
from dotenv import load_dotenv
import os

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")

HEADERS = {
    "apikey": SUPABASE_API_KEY,
    "Authorization": f"Bearer {SUPABASE_API_KEY}",
    "Content-Type": "application/json"
}

# データをSupabaseから取得
def load_data():
    global user_data
    response = requests.get(f"{SUPABASE_URL}/rest/v1/user_data?select=*", headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        user_data = {item["id"]: {"answers": item["answers"]} for item in data}
    else:
        print("Supabaseからのデータ取得に失敗しました:", response.text)
        user_data = {}

# データをSupabaseに保存
def save_data():
    data_list = []
    for uid, entry in user_data.items():
        data_list.append({
            "id": uid,
            "answers": entry.get("answers", {})
        })
    for data in data_list:
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/user_data",
            headers={**HEADERS, "Prefer": "resolution=merge-duplicates"},
            json=[data]
        )
        if response.status_code not in [200, 201]:
            print("保存失敗:", response.text)

# 起動時にSupabaseからデータ取得
load_data()

intents = discord.Intents.default()
intents.members = True
intents.message_content = True  # メッセージの内容を取得するため

bot = commands.Bot(command_prefix='!', intents=intents)

REMIND_CHANNEL_ID = 1362318510251970560

DATA_FILE = "data.json"
ADMIN_USER_IDS = [1353745472153583616,1361769649485906200]

# データをロードまたは初期化
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        user_data = json.load(f)
else:
    user_data = {}


def check_channel(ctx, allowed_channel_id):
    """指定したチャンネルでのみコマンドを実行させる"""
    if ctx.channel.id != allowed_channel_id:
        raise commands.CheckFailure("このコマンドはこのチャンネルでは使用できません。")

def calculate_age(birthday_str):
    """生年月日（YYYY-MM-DD形式）から年齢を計算する"""
    birthday = datetime.strptime(birthday_str, '%Y-%m-%d')
    today = datetime.today()
    age = today.year - birthday.year - ((today.month, today.day) < (birthday.month, birthday.day))
    return age

@bot.event
async def on_member_join(member):
    role_name = "付与待ち"  # 付与するロール名（適切に変更してください）
    
    # サーバー内のロールを取得
    role = discord.utils.get(member.guild.roles, name=role_name)
    await member.add_roles(role)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.content == "サポートサーバー(https://discord.gg/7Td6kK9hF8)":
        await message.channel.send("リマインド送るね。")
        await asyncio.sleep(3600)  # 600秒 = 10分
        channel = bot.get_channel(REMIND_CHANNEL_ID)
        if channel:
            await channel.send("<@1353745472153583616> dissoku")

    elif message.content == "https://www.paypal.com/ncp/payment/V2257AKBQS2S6":
        await message.channel.send("リマインド送るね。")
        await asyncio.sleep(7200)  # 600秒 = 10分
        channel = bot.get_channel(REMIND_CHANNEL_ID)
        if channel:
            await channel.send("<@1353745472153583616> bump")

    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f"Bot起動完了: {bot.user}")

@bot.command()
async def Q1(ctx, date):

    allowed_channel_id = 1361763632312094803  # ここに特定のチャンネルIDを指定
    check_channel(ctx, allowed_channel_id)  # チャンネル制限をチェック
    # 日付形式のチェック
    try:
        valid_date = datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        await ctx.send("日付の形式が正しくありません。正しい形式は `YYYY-MM-DD` です。例：`1995-07-16`")
        return

    # ユーザーのデータを保存
    uid = str(ctx.author.id)
    user_data.setdefault(uid, {})
    user_data[uid]["answers"] = {}
    user_data[uid]["answers"]['Q1'] = date
    
    age = calculate_age(date)
    
    if age < 18:
        try:
            channel = bot.get_channel(1362298047949832317)
            await check(ctx, ctx.author, channel)
            await ctx.guild.ban(ctx.author, reason="BANされました。")
        except discord.Forbidden:
            await ctx.send(f"{ctx.author.mention} をbanできませんでした。権限が不足している可能性があります。")
        except discord.HTTPException as e:
            await ctx.send(f"{ctx.author.mention} をbanできませんでした。エラー: {str(e)}")
        return

    save_data()

    role_name = "Q1"
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    await ctx.author.remove_roles(role)

    role_name = "Q2"
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    await ctx.author.add_roles(role)

    msg = await ctx.send(f"{ctx.author.mention} の生年月日を `{date}` として記録しました。\n<#1361763812071571656>に進んでください。")

    await asyncio.sleep(5)
    await ctx.message.delete()
    await msg.delete()

@bot.command()
async def Q2(ctx, answer: str):

    allowed_channel_id = 1361763812071571656  # ここに特定のチャンネルIDを指定
    check_channel(ctx, allowed_channel_id)  # チャンネル制限をチェック
    # 日付形式のチェック
    
    # ユーザーのデータを保存
    uid = str(ctx.author.id)
    user_data.setdefault(uid, {})
    user_data[uid]["answers"]['Q2'] = answer
    
    correct_answer = 'No'

    # 回答が正しいかチェック
    if answer != correct_answer:
        try:
            channel = bot.get_channel(1362298047949832317)
            await check(ctx, ctx.author, channel)
            await ctx.guild.ban(ctx.author, reason="BANされました。")
        except discord.Forbidden:
            await ctx.send(f"{ctx.author.mention} をキックできませんでした。権限が不足している可能性があります。")
        except discord.HTTPException as e:
            await ctx.send(f"{ctx.author.mention} をキックできませんでした。エラー: {str(e)}")
        return

    save_data()

    role_name = "Q2"
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    await ctx.author.remove_roles(role)
    role_name = "Q3"
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    await ctx.author.add_roles(role)

    msg = await ctx.send(f"{ctx.author.mention} の回答を記録しました。\n<#1361777019632746656>に進んでください。")


# 元のメッセージを安全に削除
    try:
        await ctx.message.delete()
    except discord.NotFound:
        pass  # メッセージがもう無ければ無視
    except discord.Forbidden:
        await ctx.send("メッセージを削除する権限がありません。")
    except Exception as e:
        await ctx.send(f"メッセージ削除中にエラーが発生しました: {e}")

    # botのメッセージも安全に削除
    try:
        await msg.delete()
    except discord.NotFound:
        pass
    except Exception as e:
        print(f"msg削除エラー: {e}")

@bot.command()
async def Q3(ctx, answer: str):

    allowed_channel_id = 1361777019632746656  # ここに特定のチャンネルIDを指定
    check_channel(ctx, allowed_channel_id)  # チャンネル制限をチェック
    # 日付形式のチェック
    
    # ユーザーのデータを保存
    uid = str(ctx.author.id)
    user_data.setdefault(uid, {})
    user_data[uid]["answers"]['Q3'] = answer
    
    correct_answer = 'No'

    if answer != correct_answer:
        try:
            channel = bot.get_channel(1362298047949832317)
            await check(ctx, ctx.author, channel)
            await ctx.guild.ban(ctx.author, reason="BANされました。")
        except discord.Forbidden:
            await ctx.send(f"{ctx.author.mention} をキックできませんでした。権限が不足している可能性があります。")
        except discord.HTTPException as e:
            await ctx.send(f"{ctx.author.mention} をキックできませんでした。エラー: {str(e)}")
        return

    save_data()

    role_name = "Q3"
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    await ctx.author.remove_roles(role)
    role_name = "about"
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    await ctx.author.add_roles(role)

    msg = await ctx.send(f"{ctx.author.mention} の回答を記録しました。\n<#1361776848094367794>に進んでください。")

    await asyncio.sleep(5)
    await ctx.message.delete()
    await msg.delete()

@bot.command()
async def about(ctx):

    allowed_channel_id = 1361776848094367794  # ここに特定のチャンネルIDを指定
    check_channel(ctx, allowed_channel_id)  # チャンネル制限をチェック
    # 日付形式のチェック
    
    # ユーザーのデータを保存
    uid = str(ctx.author.id)
    user_data.setdefault(uid, {})
    user_data[uid]["answers"]['about'] = "Yes"
    
    save_data()

    role_name = "about"
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    await ctx.author.remove_roles(role)
    role_name = "rule"
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    await ctx.author.add_roles(role)

    msg = await ctx.send(f"{ctx.author.mention} の回答を記録しました。\n<#1361763876995207290>に進んでください。")

    await asyncio.sleep(5)
    await ctx.message.delete()
    await msg.delete()

@bot.command()
async def rule(ctx):

    allowed_channel_id = 1361763876995207290  # ここに特定のチャンネルIDを指定
    check_channel(ctx, allowed_channel_id)  # チャンネル制限をチェック
    # 日付形式のチェック
    
    # ユーザーのデータを保存
    uid = str(ctx.author.id)
    user_data.setdefault(uid, {})
    user_data[uid]["answers"]['rule'] = "Yes"
    
    save_data()

    role_name = "rule"
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    await ctx.author.remove_roles(role)
    role_name = "request"
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    await ctx.author.add_roles(role)

    msg = await ctx.send(f"{ctx.author.mention} の回答を記録しました。\n<#1361776896483786814>に進んでください。")

    await asyncio.sleep(5)
    await ctx.message.delete()
    await msg.delete()

@bot.command()
async def request(ctx):

    allowed_channel_id = 1361776896483786814  # ここに特定のチャンネルIDを指定
    check_channel(ctx, allowed_channel_id)  # チャンネル制限をチェック
    # 日付形式のチェック
    
    # ユーザーのデータを保存
    uid = str(ctx.author.id)
    user_data.setdefault(uid, {})
    user_data[uid]["answers"]['request'] = "Yes"
    
    save_data()

    role_name = "request"
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    await ctx.author.remove_roles(role)
    role_name = "invite"
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    await ctx.author.add_roles(role)

    msg = await ctx.send(f"{ctx.author.mention} の回答を記録しました。\n<#1361776932684824708>に進んでください。")

    channel = bot.get_channel(1362298047949832317)
    await check(ctx, ctx.author, channel)

    await asyncio.sleep(5)
    await ctx.message.delete()
    await msg.delete()

@bot.command()
async def check(ctx, user: discord.Member = None, channel: discord.TextChannel = None):

    target = user or ctx.author
    uid = str(target.id)
    if uid not in user_data:
        await ctx.send("データが見つかりません。")
        return

    answers = user_data[uid].get("answers", {})
    msg = f"【{target.display_name}({uid}) の情報】\n回答\n"
    for q, a in answers.items():
        msg += f" - {q}: {a}\n"
    if channel != None:
        await channel.send(msg)
    else:
        await ctx.send(msg)

@bot.command()
async def check_id(ctx, id=None, channel: discord.TextChannel = None):
    if id is None:
        await ctx.send("ユーザーIDを指定してください。")
        return

    uid = str(id)

    if uid not in user_data:
        await ctx.send("指定されたIDのデータが見つかりません。")
        return

    answers = user_data[uid].get("answers", {})

    msg = f"【({uid}) の情報】\n回答\n"
    for q, a in answers.items():
        msg += f" - {q}: {a}\n"

    if channel is not None:
        await channel.send(msg)
    else:
        await ctx.send(msg)

async def send_flexible_embed(
    bot: commands.Bot,
    channel_id: int,
    title: str = None,
    description: str = None,
    fields: list = None,  # [{name, value, inline}]
    color: discord.Color = discord.Color.blue(),
    footer: str = None,
    timestamp: bool = False,
    use_fetch: bool = False  # Trueならfetch_channelを使う
):
    # チャンネル取得
    channel = await bot.fetch_channel(channel_id) if use_fetch else bot.get_channel(channel_id)
    if channel is None:
        print(f"チャンネル（ID: {channel_id}）が見つかりませんでした。")
        return

    # Embed生成
    embed = discord.Embed(title=title, description=description, color=color)
    
    if timestamp:
        embed.timestamp = discord.utils.utcnow()

    # フィールド追加
    if fields:
        for field in fields[:25]:  # 最大25件まで
            embed.add_field(
                name=field.get("name", "No Name"),
                value=field.get("value", "No Value"),
                inline=field.get("inline", False)
            )

    if footer:
        embed.set_footer(text=footer)

    await channel.send(embed=embed)

@bot.command()
async def embed(ctx, channel_id: int, title: str, description: str, *fields: str):
    """
    チャンネルに埋め込みメッセージを送信するコマンド
    フィールド名と内容をユーザーが指定
    例: !embed <channel_id> <title> <description> フィールド数 <フィールド名1> <フィールド内容1> <フィールド名2> <フィールド内容2> ...
    """

    # 入力が奇数個の場合、フィールド名と内容が対応しないのでエラーメッセージ
    if len(fields) % 2 != 0:
        await ctx.send("フィールドのペア数が合っていません。フィールド名と内容をペアで入力してください。")
        return

    # フィールドのリストを作成
    field_list = []
    for i in range(0, len(fields), 2):
        field_name = fields[i]
        field_value = fields[i+1]
        field_list.append({"name": field_name, "value": field_value, "inline": False})

    # send_flexible_embed関数を呼び出し
    await send_flexible_embed(
        bot=bot,
        channel_id=channel_id,
        title=title,
        description=description,
        fields=field_list,
        color=discord.Color.green(),
        footer="認証",
        timestamp=True
    )



bot.run("MTM2MTc2OTY0OTQ4NTkwNjIwMA.GE786O.DMzOZantaOG-hKBmBuqIp5Y60PFoaOLzNnLQTM")  # ← ここに実際のトークンを入れてください
