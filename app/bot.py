import discord
from discord.ext import commands
from datetime import datetime
import asyncio
import os
import requests
import tempfile
import gspread
from dotenv import load_dotenv
from supabase import create_client, Client
from oauth2client.service_account import ServiceAccountCredentials
from discord import ui
import re
from discord.utils import get

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_API_KEY")
INVITE_URL = os.getenv("INVITE_URL")
ADMIN_USER_ID = 1353745472153583616

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

intents = discord.Intents.default()
intents.members = True
intents.dm_messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

DEFAULT_TIMEOUT = 3600

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}


def is_initial_avatar(member: discord.Member) -> bool:
    return member.avatar is None

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_member_join(member: discord.Member):
    if is_initial_avatar(member):
        role = discord.utils.get(member.guild.roles, name="初期アイコン")
    else:
        role = discord.utils.get(member.guild.roles, name="説明中")
    if role:
        await member.add_roles(role)
    if role and role.name == "初期アイコン":
        # 初期アイコンロール付与時にアイコン変更を促すDMを送信
        try:
            dm = await member.create_dm()
            await dm.send("初期アイコンの状態です。プロフィール画像を変更してください。変更後、再度参加手続きを進められます。")
        except Exception as e:
            print(f"DM送信失敗: {e}")
    if role and role.name == "説明中":
        await start_questionnaire(member)

@bot.event
async def on_user_update(before: discord.User, after: discord.User):
    if before.avatar != after.avatar:
        for guild in bot.guilds:
            member = guild.get_member(after.id)
            if member:
                has_initial = discord.utils.get(guild.roles, name="初期アイコン")
                if has_initial and has_initial in member.roles:
                    await member.remove_roles(has_initial)
                    if is_initial_avatar(member):
                        await member.add_roles(has_initial)
                    else:
                        role2 = discord.utils.get(guild.roles, name="説明中")
                        if role2:
                            await member.add_roles(role2)
                            await start_questionnaire(member)


async def update_user_role(member: discord.Member):
    guild = member.guild  # メンバーが所属するギルド（サーバー）

    # ロール名で指定（大文字・小文字・全角・半角も正確に！）
    EXPLAINING_ROLE_NAME = "説明中"
    INVITED_ROLE_NAME = "招待済み"

    explaining_role = get(guild.roles, name=EXPLAINING_ROLE_NAME)
    invited_role = get(guild.roles, name=INVITED_ROLE_NAME)

    if explaining_role is None or invited_role is None:
        print("⚠️ ロールが見つかりません。名前が正しいか確認してください。")
        return

    try:
        if explaining_role in member.roles:
            await member.remove_roles(explaining_role)
            print(f"❌ {EXPLAINING_ROLE_NAME} ロールを削除: {member.display_name}")

        await member.add_roles(invited_role)
        print(f"✅ {INVITED_ROLE_NAME} ロールを付与: {member.display_name}")

    except discord.Forbidden:
        print("⚠️ ロール変更に必要な権限がありません。")
    except discord.HTTPException as e:
        print(f"⚠️ Discord APIエラー: {e}")

async def send_invite_message(dm_channel, invite_url):
    match = re.search(r'discord\.com/channels/(\d+)/(\d+)/(\d+)', invite_url)
    if not match:
        await dm_channel.send("招待リンクが無効です。")
        return

    guild_id, channel_id, message_id = map(int, match.groups())

    try:
        # メッセージ取得
        channel = await bot.fetch_channel(channel_id)
        message = await channel.fetch_message(message_id)

        # 招待リンクを抽出
        invite_match = re.search(r'(https?://)?(www\.)?(discord\.gg|discord\.com/invite)/[a-zA-Z0-9]+', message.content)
        if invite_match:
            invite_url = invite_match.group(0)

            try:
                # 招待の有効性を確認
                invite = await bot.fetch_invite(invite_url)
                # 有効：そのまま送信
                await dm_channel.send(message.content)

            except discord.NotFound:
                # 無効：案内を送って管理者に通知
                await dm_channel.send("""この招待リンクは現在無効です。
管理者から新しいリンクが送付されるまでしばらくお待ちください。""")

                # # 管理者にDMで通知
                admin_user = await bot.fetch_user(ADMIN_USER_ID)
                user = dm_channel.recipient  # DMの相手（案内を受けたユーザー）

                await admin_user.send(
                    f"⚠️ 無効な招待リンクが使用されました。\n"
                    f"・元メッセージリンク: https://discord.com/channels/{guild_id}/{channel_id}/{message_id}\n"
                    f"・対象ユーザー: {user} (`{user.id}`)"
                )

        else:
            await dm_channel.send("メッセージに招待リンクが含まれていません。")

    except discord.NotFound:
        await dm_channel.send("指定されたメッセージが見つかりませんでした。")
    except discord.Forbidden:
        await dm_channel.send("メッセージにアクセスする権限がありません。")
    except Exception as e:
        await dm_channel.send(f"メッセージ取得中にエラーが発生しました：{e}")

# --- 招待者選択用Select ---
class InviterSelect(ui.Select):
    def __init__(self, inviter_mapping: dict[str, str]):
        options = [
            discord.SelectOption(label=name, value=inviter_id)
            for inviter_id, name in inviter_mapping.items()
        ]
        super().__init__(placeholder="招待者を選択してください", options=options, max_values=1, min_values=1)
        self.selected_id = None

    async def callback(self, interaction: discord.Interaction):
        self.selected_id = self.values[0]
        await interaction.response.send_message(f"{self.view.inviter_mapping[self.selected_id]} を選択しました。", ephemeral=True)
        self.view.selected_id = self.selected_id
        self.view.stop()

class InviterSelectView(ui.View):
    def __init__(self, member: discord.Member, inviter_mapping: dict[str, str]):
        super().__init__(timeout=DEFAULT_TIMEOUT)
        self.member = member
        self.inviter_mapping = inviter_mapping
        self.selected_id = None
        self.add_item(InviterSelect(inviter_mapping))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.member.id

    @ui.button(label="キャンセル", style=discord.ButtonStyle.danger)
    async def cancel_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("キャンセルされました。", ephemeral=True)
        self.stop()

# --- Yes/No ボタンView ---
class YesNoView(ui.View):
    def __init__(self, member: discord.Member, question_key: str, timeout=DEFAULT_TIMEOUT):
        super().__init__(timeout=timeout)
        self.member = member
        self.question_key = question_key
        self.answer = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.member.id

    @ui.button(label="YES", style=discord.ButtonStyle.success)
    async def yes_button(self, interaction: discord.Interaction, button: ui.Button):
        self.answer = "yes"
        await interaction.response.send_message("はい を選択しました。", ephemeral=True)
        self.stop()

    @ui.button(label="NO", style=discord.ButtonStyle.danger)
    async def no_button(self, interaction: discord.Interaction, button: ui.Button):
        self.answer = "no"
        await interaction.response.send_message("いいえ を選択しました。", ephemeral=True)
        self.stop()

async def start_questionnaire(member: discord.Member):
    dm = await member.create_dm()
    answers = {}

    guild = bot.get_guild(1361763625953398945)  # ここに対象のサーバーIDを入れる
    role = guild.get_role(1373499098359136256)  # 対象のロールID

    inviter_mapping = {}

    for inviter_member in role.members:
        inviter_mapping[str(inviter_member.id)] = inviter_member.display_name

    # 招待者選択ビューに渡す
    view = InviterSelectView(member, inviter_mapping)
    await dm.send("招待者を選択してください。", view=view)
    await view.wait()
    if view.selected_id is None:
        await dm.send("招待者選択がキャンセルされたか、時間切れです。")
        return
    answers["招待者"] = view.selected_id

    # 生年月日質問（テキスト入力方式に変更）
    await dm.send("生年月日を「YYYY-MM-DD」の形式で入力してください。")

    def check(m):
        return m.author == member and isinstance(m.channel, discord.DMChannel)

    try:
        msg = await bot.wait_for("message", timeout=120, check=check)
        dob_str = msg.content.strip()
        dob = datetime.strptime(dob_str, "%Y-%m-%d")
    except asyncio.TimeoutError:
        await dm.send("時間切れです。生年月日が入力されませんでした。中断します。")
        return
    except ValueError:
        await dm.send("入力形式が正しくありません。`YYYY-MM-DD` の形式で入力してください。中断します。")
        return

    answers["生年月日"] = dob_str

    # 学年判定
    def is_high_school_student(dob: datetime) -> bool:
        today = datetime.today()
        school_year_start = datetime(today.year, 4, 1)
        base_year = today.year if today >= school_year_start else today.year - 1
        age_on_april_1 = base_year - dob.year - ((dob.month, dob.day) > (4, 1))
        return age_on_april_1 <= 17

    if is_high_school_student(dob):
        role = discord.utils.get(member.guild.roles, name="資格無し")
        if role:
            await member.add_roles(role)
        await dm.send("""現在高校生相当のため、参加資格がありません。
    誤答の場合はあるかなまでご連絡ください。""")
        await store_answers(member.id, answers)
        return


    # 「現在高校生ですか？」質問
    view = YesNoView(member, "高校卒業確認")
    await dm.send("あなたは現在高校生ですか？", view=view)
    await view.wait()
    if view.answer is None:
        await dm.send("時間切れです。")
        return
    answers["高校卒業確認"] = view.answer

    if view.answer == "yes":
        role = discord.utils.get(member.guild.roles, name="資格無し")
        if role:
            await member.add_roles(role)
        await dm.send("""現在高校生のため、参加資格がありません。
誤答の場合はあるかなまでご連絡ください。""")
        await store_answers(member.id, answers)
        return

    # 「過去Lawlessに参加していた？」質問
    view = YesNoView(member, "出戻り確認")
    await dm.send("過去Lawlessというサーバーに参加していたことがありましたか？", view=view)
    await view.wait()
    if view.answer is None:
        await dm.send("時間切れです。")
        return
    answers["出戻り確認"] = view.answer

    if view.answer == "yes":
        role = discord.utils.get(member.guild.roles, name="出戻り")
        if role:
            await member.add_roles(role)
        await dm.send("""出戻りの方は原則参加禁止となっています。
誤答、または出戻りでも参加したい場合はあるかなまでご連絡ください。""")
        await store_answers(member.id, answers)
        return  # ✅ 中断


    # 「以上、確認できましたか？（サーバー説明）」質問
    view = YesNoView(member, "サーバー説明")
    await dm.send("""これから招待させていただく**__Lawless__**というサーバーはエロイプを中心としたサーバーです。
                  
サーバーの方針として**__声の善し悪し__**が重視される傾向にあり、
声が良ければそれだけ優遇されます。
                  
もちろん声に自信がなくても蹴られる！ということはなく、
トーク力や浮上率などその他の要素も考慮されますが、声が第1の評価基準になります。
確認できましたか？""", view=view)
    await view.wait()
    if view.answer is None:
        await dm.send("時間切れです。")
        return
    answers["サーバー説明"] = view.answer

    if view.answer != "yes":
        role = discord.utils.get(member.guild.roles, name="資格無し")
        if role:
            await member.add_roles(role)
        await dm.send("""サーバーについてご理解いただけない方は、参加資格がありません。
誤答の場合はあるかなまでご連絡ください。""")
        await store_answers(member.id, answers)
        return

    # 「以上、確認できましたか？（ルール確認）」質問
    view = YesNoView(member, "ルール確認")
    await dm.send("""Lawlessでは鯖主である**__やまげさんが絶対のルール__**です。
                  
一つ一つ細かくルールを記載するととても長くなり穴も生まれるため
運営上効率がいい鯖主を絶対のルールとする形をとっています。
                  
もちろん理不尽に怒られる・蹴られるなどは無いため、そこは心配しなくても大丈夫です。
                  
とはいえ、全くルールがない状態だと基準が分からず困るため
大まかなルールについてはサーバーに記載があります。
しっかりと読み込んでください。
以上、確認できましたか？""", view=view)
    await view.wait()
    if view.answer is None:
        await dm.send("時間切れです。")
        return
    answers["ルール確認"] = view.answer

    if view.answer != "yes":
        role = discord.utils.get(member.guild.roles, name="資格無し")
        if role:
            await member.add_roles(role)
        await dm.send("""ルールを理解していない方は、参加資格がありません。
誤答の場合はあるかなまでご連絡ください。""")
        await store_answers(member.id, answers)
        return

    # 「以上を実行していただけますか？」質問
    view = YesNoView(member, "面接の予約")
    await dm.send("""## サーバーに参加した際にして欲しいこと
最後に、入ってからしてもらいたいことがいくつかあります。
                  
1つ目が最初の**__案内を読み飛ばさず、該当の項目にチェックを入れること__**です。
性別などのチェック欄が出てくるので、一つ一つしっかりとチェックしてください。
                  
2つ目が**__ルールの確認__**です。
サーバーに参加するとルール確認というチャンネルが見えるかと思います。
中身を確認・理解し、遵守してください。
                  
3つ目が**__面接の予約__**です。
当サーバーでは日本語が話せるかの確認程度の簡単な面接を行っています。
面接は水曜日を除いた22時、その他土日、水曜日を除き不定期で13,25時に行っています。
この中で都合のいい時間帯を選び、22時の場合は面接日程に、13,25時の場合はサブ面接日程に
『"""+str(inviter_mapping[answers["招待者"]])+"""からの招待で来ました。️
〇月️〇日の〇時から面接をお願いします』
と書き込みをお願いします。 また、日程は面接官の都合により変更される可能性があります。
面接日程チャンネルで面接前にお知らせが入るのでそこを参照して予約をお願いします。

以上を実行していただけますか？""", view=view)
    await view.wait()
    if view.answer is None:
        await dm.send("時間切れです。")
        return
    answers["面接の予約"] = view.answer

    if view.answer != "yes":
        role = discord.utils.get(member.guild.roles, name="資格無し")
        if role:
            await member.add_roles(role)
        await dm.send("""面接の予約を実行できない方には、参加資格がありません。
誤答の場合はあるかなまでご連絡ください。""")
        await store_answers(member.id, answers)
        return

    # 全質問回答後
    await send_invite_message(dm, INVITE_URL)
    await store_answers(member.id, answers)
    await update_user_role(member)

async def store_answers(user_id: int, answers: dict):
    data = {"id": str(user_id), **answers}
    try:
        resp = supabase.table("responses").upsert(data).execute()
        print("✅ 回答をSupabaseに保存しました:", resp.data)
    except Exception as e:
        print(f"❌ Supabase保存エラー: {e}")

# 参加ボタン付きメッセージを指定チャンネルに送信する関数
class ParticipateButton(ui.Button):
    def __init__(self):
        super().__init__(label="参加する", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        member = interaction.user
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("このコマンドはサーバー内で実行してください。", ephemeral=True)
            return

        role_initial = get(guild.roles, name="初期アイコン")
        role_explaining = get(guild.roles, name="説明中")
        role_returnee = get(guild.roles, name="出戻り")
        role_invited = get(guild.roles, name="招待済み")

        user_roles = member.roles

        if role_explaining and role_explaining in user_roles:
            await interaction.response.defer(ephemeral=True)
            await start_questionnaire(member)
            await interaction.followup.send("質問を開始しました。DMを確認してください。", ephemeral=True)
        elif role_initial and role_initial in user_roles:
            await interaction.response.send_message("プロフィール画像を変更してください。", ephemeral=True)
        elif role_returnee and role_returnee in user_roles:
            await interaction.response.send_message("参加資格が制限されています。詳細は管理者にお問い合わせください。", ephemeral=True)
        elif role_invited and role_invited in user_roles:
            await interaction.response.send_message("すでに招待済みです。新しくリンクが必要な場合はあるかなにお問い合わせください。", ephemeral=True)
        else:
            await interaction.response.send_message("エラーが発生しました。詳細は管理者にお問い合わせください。", ephemeral=True)

class ParticipateView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ParticipateButton())

@bot.command(name="send_participate_message")
@commands.has_permissions(administrator=True)
async def send_participate_message(ctx,channel_id: int, text: str):
    channel = bot.get_channel(channel_id)
    if channel is None:
        print(f"チャンネルID {channel_id} が見つかりません。")
        return
    await channel.send(text, view=ParticipateView())
    await ctx.send("参加ボタン付きメッセージを送信しました。")

@bot.command(name="start_questionnaire_manual")
@commands.has_permissions(administrator=True)  # 管理者のみ実行可
async def start_questionnaire_manual(ctx, member: discord.Member):
    try:
        await ctx.send(f"{member.display_name} に質問を開始します。")
        await start_questionnaire(member)
    except Exception as e:
        await ctx.send(f"❌ エラー: {e}")


json_string = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
if not json_string:
    raise RuntimeError("環境変数 GOOGLE_SERVICE_ACCOUNT_JSON が設定されていません")

# 一時ファイルに保存して認証
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as tmp_file:
    tmp_file.write(json_string)
    tmp_file.flush()
    credentials = ServiceAccountCredentials.from_json_keyfile_name(tmp_file.name, scope)
    gc = gspread.authorize(credentials)

# スプレッドシートに接続
spreadsheet = gc.open("invites")
worksheet = spreadsheet.sheet1

# ✅ 通常コマンド：招待情報を手動で登録
@bot.command(name="add_invite_bulk")
@commands.has_permissions(manage_guild=True)
async def add_invite_bulk(ctx):
    try:
        content = ctx.message.content
        lines = content.splitlines()[1:]  # 1行目はコマンド名なのでスキップ
        success_count = 0
        fail_count = 0
        failed_lines = []

        for line in lines:
            parts = line.strip().split()
            if len(parts) != 4:
                fail_count += 1
                failed_lines.append(f"❌ フォーマットエラー: `{line}`")
                continue

            inviter_id, invited_id, gender, method = parts
            data = {
                "inviter_id": inviter_id,
                "invited_id": invited_id,
                "invite_method": method,
                "gender": gender
            }

            try:
                supabase.table("invites").insert(data).execute()
                success_count += 1
            except Exception as e:
                fail_count += 1
                failed_lines.append(f"❌ エラー（{invited_id}）: {str(e)}")

        result_message = (
            f"✅ 登録完了\n"
            f"- 成功: {success_count} 件\n"
            f"- 失敗: {fail_count} 件"
        )
        if failed_lines:
            result_message += "\n" + "\n".join(failed_lines[:10])  # エラーは最大10件表示

        await ctx.send(result_message)

    except Exception as e:
        await ctx.send(f"❌ コマンドエラー: {str(e)}")

@bot.command(name="mark_settled")
@commands.has_permissions(manage_guild=True)
async def mark_settled(ctx, *invited_ids: str):
    try:
        updated = 0
        for invited_id in invited_ids:
            response = supabase.table("invites").update({"settled": True}).eq("invited_id", invited_id).execute()
            if response.data:
                updated += 1
        await ctx.send(f"✅ {updated} 件のユーザーを定着済みに更新しました。")
    except Exception as e:
        await ctx.send(f"❌ 更新に失敗しました: {e}")

# ✅ 通常コマンド：Googleスプレッドシートに集計出力
from datetime import datetime, timedelta

@bot.command(name="export_invite_summary")
@commands.has_permissions(manage_guild=True)
async def export_invite_summary(ctx, days: int = 30):
    try:
        await ctx.send(f"📊 過去{days}日間の集計を開始します。しばらくお待ちください...")

        since_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

        result = supabase.table("invites") \
            .select("invite_method", "gender", "settled", "invited_at") \
            .gte("invited_at", since_date) \
            .execute()
        data = result.data


        # 通常集計と定着数集計を分ける
        summary = {}
        settled_summary = {}
        for row in data:
            method = row["invite_method"]
            gender = row["gender"]
            settled = row.get("settled", False)

            if method not in summary:
                summary[method] = {"男性": 0, "女性": 0, "未入力": 0}
                settled_summary[method] = {"男性": 0, "女性": 0, "未入力": 0}

            summary[method][gender] += 1
            if settled:
                settled_summary[method][gender] += 1

        # スプレッドシート出力
        worksheet.clear()

        # 1段目: 全体の集計
        worksheet.append_row(["招待方法", "男性", "女性", "未入力", "合計"])
        for method, counts in summary.items():
            male = counts["男性"]
            female = counts["女性"]
            unknown = counts["未入力"]
            total = male + female + unknown
            worksheet.append_row([method, male, female, unknown, total])

        # 空行
        worksheet.append_row([])

        # 2段目: 定着数と割合
        worksheet.append_row(["定着数", "男性", "女性", "未入力", "男性割合", "女性割合"])
        for method in summary:
            settled = settled_summary.get(method, {"男性": 0, "女性": 0, "未入力": 0})
            total = sum(summary[method].values())
            male_rate = f"{round(settled['男性'] / summary[method]['男性'] * 100)}％" if summary[method]['男性'] > 0 else "0％"
            female_rate = f"{round(settled['女性'] / summary[method]['女性'] * 100)}％" if summary[method]['女性'] > 0 else "0％"

            worksheet.append_row([
                method,
                settled["男性"],
                settled["女性"],
                settled["未入力"],
                male_rate,
                female_rate
            ])

        await ctx.send("✅ 集計結果をGoogleスプレッドシートに出力しました。")
    except Exception as e:
        await ctx.send(f"❌ 出力に失敗しました: {e}")

@bot.command(name="export_invite_summary_range")
@commands.has_permissions(manage_guild=True)
async def export_invite_summary_range(ctx, start_date: str, end_date: str):
    try:
        await ctx.send(f"📊 {start_date}〜{end_date}の集計を開始します...")

        result = supabase.table("invites") \
            .select("invite_method", "gender", "settled", "invited_at") \
            .gte("invited_at", start_date) \
            .lte("invited_at", end_date) \
            .execute()
        data = result.data



        # 通常集計と定着数集計を分ける
        summary = {}
        settled_summary = {}
        for row in data:
            method = row["invite_method"]
            gender = row["gender"]
            settled = row.get("settled", False)

            if method not in summary:
                summary[method] = {"男性": 0, "女性": 0, "未入力": 0}
                settled_summary[method] = {"男性": 0, "女性": 0, "未入力": 0}

            summary[method][gender] += 1
            if settled:
                settled_summary[method][gender] += 1

        # スプレッドシート出力
        worksheet.clear()

        # 1段目: 全体の集計
        worksheet.append_row(["招待方法", "男性", "女性", "未入力", "合計"])
        for method, counts in summary.items():
            male = counts["男性"]
            female = counts["女性"]
            unknown = counts["未入力"]
            total = male + female + unknown
            worksheet.append_row([method, male, female, unknown, total])

        # 空行
        worksheet.append_row([])

        # 2段目: 定着数と割合
        worksheet.append_row(["定着数", "男性", "女性", "未入力", "男性割合", "女性割合"])
        for method in summary:
            settled = settled_summary.get(method, {"男性": 0, "女性": 0, "未入力": 0})
            total = sum(summary[method].values())
            male_rate = f"{round(settled['男性'] / summary[method]['男性'] * 100)}％" if summary[method]['男性'] > 0 else "0％"
            female_rate = f"{round(settled['女性'] / summary[method]['女性'] * 100)}％" if summary[method]['女性'] > 0 else "0％"

            worksheet.append_row([
                method,
                settled["男性"],
                settled["女性"],
                settled["未入力"],
                male_rate,
                female_rate
            ])

        await ctx.send("✅ 集計結果をGoogleスプレッドシートに出力しました。")
    except Exception as e:
        await ctx.send(f"❌ 出力に失敗しました: {e}")

bot.run(TOKEN)