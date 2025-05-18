
import discord
from discord.ext import commands
from discord.ui import Button, View
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

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

def load_data():
    global user_data
    response = requests.get(f"{SUPABASE_URL}/rest/v1/user_data_copy?select=*", headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        user_data = {item["id"]: {"answers": item["answers"]} for item in data}
    else:
        print("Supabaseからのデータ取得に失敗しました:", response.text)
        user_data = {}

def save_data():
    data_list = []
    for uid, entry in user_data.items():
        data_list.append({
            "id": uid,
            "answers": entry.get("answers", {})
        })
    for data in data_list:
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/user_data_copy",
            headers={**HEADERS, "Prefer": "resolution=merge-duplicates"},
            json=[data]
        )
        if response.status_code not in [200, 201]:
            print("保存失敗:", response.text)

load_data()

bot = commands.Bot(command_prefix='!', intents=intents)

REMIND_CHANNEL_ID = 1358914591870156872

DATA_FILE = "data.json"
ADMIN_USER_IDS = [1353745472153583616,1361769649485906200]

inviters = os.getenv("INVITERS")

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        user_data = json.load(f)
else:
    user_data = {}

def calculate_age(birthday_str):
    """生年月日（YYYY-MM-DD形式）から年齢を計算する"""
    birthday = datetime.strptime(birthday_str, '%Y-%m-%d')
    today = datetime.today()
    age = today.year - birthday.year - ((today.month, today.day) < (birthday.month, birthday.day))
    return age


async def check_inviters(ctx, answer: str) -> bool:
    return answer.lower() in inviters

async def check_birthday(interaction, answer: str) -> bool:
    try:
        datetime.strptime(answer, "%Y-%m-%d")
    except ValueError:
        return False

    age = calculate_age(answer)
    if age < 18:
        channel = await bot.fetch_channel(1358914591870156872)
        if channel:
            msg = await generate_check_message(interaction.user)
            await channel.send(msg)
        await interaction.guild.ban(interaction.user, reason="未成年のためBAN")
        return False  # 送信は on_submit 側に任せる
    return True


async def change_role(user: discord.Member, guild: discord.Guild, remove: str, add: str):
    if remove:
        remove_role = discord.utils.get(guild.roles, name=remove)
        if remove_role:
            await user.remove_roles(remove_role)
    if add:
        add_role = discord.utils.get(guild.roles, name=add)
        if add_role:
            await user.add_roles(add_role)

@bot.event
async def on_member_join(member):
    role_name = "付与待ち"
    
    role = discord.utils.get(member.guild.roles, name=role_name)
    await member.add_roles(role)

async def generate_check_message(user: discord.User) -> str:
    uid = str(user.id)
    if uid not in user_data:
        return "データが見つかりません。"

    answers = user_data[uid].get("answers", {})
    msg = f"【{user.display_name}({uid}) の情報】\n回答\n"
    for q, a in answers.items():
        msg += f" - {q}: {a}\n"
    return msg

async def send_flexible_embed(
    bot: commands.Bot,
    channel_id: int,
    title: str = None,
    description: str = None,
    fields: list = None,  # [{name, value, inline}]
    color: discord.Color = discord.Color.blue(),
    footer: str = None,
    view=None,
    timestamp: bool = False,
    use_fetch: bool = False 
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
    await channel.send(embed=embed, view=view)

class YesNoView(View):
    def __init__(self, question_name: str, next_channel: str, correct_answer: str, remove_role: str = None, add_role: str = None):
        super().__init__(timeout=None)
        self.question_name = question_name
        self.next_channel = next_channel
        self.correct_answer = correct_answer.lower()
        self.remove_role = remove_role
        self.add_role = add_role

        yes_button = Button(label="Yes", style=discord.ButtonStyle.success)
        no_button = Button(label="No", style=discord.ButtonStyle.danger)

        yes_button.callback = self.make_callback("yes")
        no_button.callback = self.make_callback("no")

        self.add_item(yes_button)
        self.add_item(no_button)

    def make_callback(self, answer: str):
        async def callback(interaction: discord.Interaction):
            uid = str(interaction.user.id)
            user_data.setdefault(uid, {})
            user_data[uid]["answers"] = user_data[uid].get("answers", {})
            user_data[uid]["answers"][self.question_name] = answer
            save_data()

            if answer != self.correct_answer:
                # 間違えた場合 → BAN & 通知
                await interaction.guild.ban(interaction.user, reason="不正解によるBAN")
                await interaction.response.send_message("あなたには参加権がないようです。誤答の場合は招待者にDMを送ってください。", ephemeral=True)
                return

            # 正解の場合は従来処理
            await change_role(interaction.user, interaction.guild, self.remove_role, self.add_role)
            await interaction.response.send_message(
                f"{interaction.user.mention} 回答を「{answer}」として記録しました。\n"
                f"<#{self.next_channel}>へ進んでください。",
                ephemeral=True
            )
        return callback

    
class FormModal(discord.ui.Modal):
    def __init__(self, example: str, question: str, next_channel: str, check_func, remove_role: str = None, add_role: str = None):
        super().__init__(title="回答する")
        self.question = question
        self.next_channel = next_channel
        self.check_func = check_func
        self.remove_role = remove_role
        self.add_role = add_role
        self.answer = discord.ui.TextInput(
            label="回答を入力してください",
            placeholder=example,
            required=True
        )
        self.add_item(self.answer)

    async def on_submit(self, interaction: discord.Interaction):
        user_answer = self.answer.value
        valid = await self.check_func(interaction, user_answer)
        if valid:
            await self.save_answer(interaction, user_answer)
        else:
            await interaction.response.send_message("❌ 回答の形式が正しくありません。", ephemeral=True)

    async def save_answer(self, interaction: discord.Interaction, answer: str):
        uid = str(interaction.user.id)
        user_data.setdefault(uid, {})
        user_data[uid]["answers"] = user_data[uid].get("answers", {})
        user_data[uid]["answers"][self.question] = answer
        save_data()

        await change_role(interaction.user, interaction.guild, self.remove_role, self.add_role)

        await interaction.response.send_message(
            f"{interaction.user.mention} 回答を「{answer}」として記録しました。\n"
            f"<#{self.next_channel}>へ進んでください。",
            ephemeral=True
        )

class FormView(discord.ui.View):
    def __init__(self, question: str, example: str, check_func, next_channel: str, remove_role: str = None, add_role: str = None):
        super().__init__(timeout=None)
        self.question = question
        self.example = example
        self.check_func = check_func
        self.next_channel = next_channel
        self.remove_role = remove_role
        self.add_role = add_role

    @discord.ui.button(label="回答する", style=discord.ButtonStyle.primary)
    async def answer_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(FormModal(
            example=self.example,
            question=self.question,
            next_channel=self.next_channel,
            check_func=self.check_func,
            remove_role=self.remove_role,
            add_role=self.add_role
        ))


@bot.command()
async def ask_YesNo(ctx, question: str, correct_answer: str, channel_id: int, next_channel: int, remove_role: str, add_role: str, title: str, description: str, *fields: str):
    if len(fields) % 2 != 0:
        await ctx.send("フィールド名と内容はペアで指定してください。")
        return

    field_list = []
    for i in range(0, len(fields), 2):
        field_list.append({"name": fields[i], "value": fields[i+1], "inline": False})

    await send_flexible_embed(
        bot=bot,
        channel_id=channel_id,
        title=title,
        description=description,
        fields=field_list,
        color=discord.Color.green(),
        footer="認証",
        timestamp=True,
        view=YesNoView(
            question_name=question,
            next_channel=next_channel,
            correct_answer=correct_answer,
            remove_role=remove_role,
            add_role=add_role
        )
    )

@bot.command()
async def ask_Modal(ctx, question: str, check_type: str, example: str, channel_id: int, next_channel: int, remove_role: str, add_role: str, title: str, description: str, *fields: str):
    if check_type == "inviters":
        check_func = check_inviters
    elif check_type == "birthday":
        check_func = check_birthday
    else:
        await ctx.send("無効なチェックタイプです。'choice' か 'date' を選んでください。")
        return

    if len(fields) % 2 != 0:
        await ctx.send("フィールド名と内容はペアで指定してください。")
        return

    field_list = []
    for i in range(0, len(fields), 2):
        field_list.append({"name": fields[i], "value": fields[i+1], "inline": False})

    await send_flexible_embed(
        bot=bot,
        channel_id=channel_id,
        title=title,
        description=description,
        fields=field_list,
        color=discord.Color.green(),
        footer="認証",
        timestamp=True,
        view=FormView(question, example, check_func, next_channel=next_channel, remove_role=remove_role, add_role=add_role)
    )

@bot.command()
async def check(ctx, user: discord.Member = None, channel: discord.TextChannel = None):
    target = user or ctx.author
    msg = await generate_check_message(target)
    await (channel or ctx).send(msg)

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

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)