import discord
from discord.ext import commands
from datetime import datetime
import asyncio
import json
import os

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

# データ保存関数
def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(user_data, f, ensure_ascii=False, indent=2)

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

    if message.content() == "サポートサーバー(https://discord.gg/7Td6kK9hF8)":
        await message.channel.send("リマインド送るね。")
        await asyncio.sleep(3600)  # 600秒 = 10分
        channel = bot.get_channel(REMIND_CHANNEL_ID)
        if channel:
            await channel.send("<@1353745472153583616> dissoku")

    elif message.content() == "https://www.paypal.com/ncp/payment/V2257AKBQS2S6":
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
            await ctx.guild.ban(ctx.author, reason="18歳未満のためbanされました。")
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
    
    correct_answer = 'Yes'

    # 回答が正しいかチェック
    if answer != correct_answer:
        try:
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

    await asyncio.sleep(5)
    await ctx.message.delete()
    await msg.delete()

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
async def check(ctx, user: discord.Member = None, channel = None):
    """ユーザーの回答を確認（管理者のみ）"""
    if ctx.author.id not in ADMIN_USER_IDS:
        await ctx.send("このコマンドを使用する権限がありません。")
        return

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


bot.run("MTM2MTc2OTY0OTQ4NTkwNjIwMA.GE786O.DMzOZantaOG-hKBmBuqIp5Y60PFoaOLzNnLQTM")  # ← ここに実際のトークンを入れてください
