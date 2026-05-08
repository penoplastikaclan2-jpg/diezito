import discord
from discord.ext import commands
import json
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
FAMILY_ROLE_ID = int(os.getenv("FAMILY_ROLE_ID"))

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "contracts.json"

contracts = {}
contract_counter = 0


def load_data():
    global contracts, contract_counter

    if not os.path.exists(DATA_FILE):
        contracts = {}
        contract_counter = 0
        return

    with open(DATA_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    contracts = data.get("contracts", {})
    contract_counter = data.get("contract_counter", 0)


def save_data():
    data = {
        "contracts": contracts,
        "contract_counter": contract_counter
    }

    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def mention_user(guild, user_id):
    member = guild.get_member(int(user_id))
    return member.mention if member else f"<@{user_id}>"


def format_list(guild, user_ids):
    if not user_ids:
        return "—"

    return "\n".join(
        f"**{index}.** {mention_user(guild, user_id)}"
        for index, user_id in enumerate(user_ids, start=1)
    )


def make_lobby_embed():
    embed = discord.Embed(
        title="📋 Система контрактов семьи",
        description="Нажмите кнопку ниже, чтобы создать контракт.",
        color=discord.Color.gold()
    )

    embed.set_footer(text="DIEZITO Contract System")

    return embed


def make_contract_embed(contract, guild, closed=False):
    creator = mention_user(guild, contract["creator"])

    if closed:
        title = f"✅ Контракт #{contract['id']} собран"
        color = discord.Color.green()
    else:
        title = f"📋 Контракт #{contract['id']}"
        color = discord.Color.gold()

    embed = discord.Embed(
        title=title,
        color=color
    )

    embed.add_field(
        name="👑 Создатель:",
        value=creator,
        inline=False
    )

    embed.add_field(
        name=f"👥 Участники ({len(contract['members'])}/4):",
        value=format_list(guild, contract["members"]),
        inline=False
    )

    if closed:
        embed.add_field(
            name="✅ Статус:",
            value="Состав собран.",
            inline=False
        )

    embed.set_footer(text="DIEZITO Contract System")

    return embed


class LobbyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Создать контракт",
        style=discord.ButtonStyle.primary,
        custom_id="create_contract_button"
    )
    async def create_contract(self, interaction: discord.Interaction, button: discord.ui.Button):
        global contract_counter

        contract_counter += 1

        contract = {
            "id": contract_counter,
            "creator": str(interaction.user.id),
            "members": [str(interaction.user.id)],
            "closed": False
        }

        embed = make_contract_embed(contract, interaction.guild)

        view = ContractView()

        await interaction.response.send_message(
            content=f"<@&{FAMILY_ROLE_ID}>",
            embed=embed,
            view=view,
            allowed_mentions=discord.AllowedMentions(roles=True)
        )

        message = await interaction.original_response()

        contracts[str(message.id)] = contract

        save_data()


class ContractView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Присоединиться",
        style=discord.ButtonStyle.success,
        custom_id="join_contract_button"
    )
    async def join_contract(self, interaction: discord.Interaction, button: discord.ui.Button):
        message_id = str(interaction.message.id)
        user_id = str(interaction.user.id)

        if message_id not in contracts:
            await interaction.response.send_message(
                "Контракт не найден.",
                ephemeral=True
            )
            return

        contract = contracts[message_id]

        if contract.get("closed"):
            await interaction.response.send_message(
                "Контракт уже закрыт.",
                ephemeral=True
            )
            return

        if user_id in contract["members"]:
            await interaction.response.send_message(
                "Ты уже участвуешь.",
                ephemeral=True
            )
            return

        if len(contract["members"]) >= 4:
            await interaction.response.send_message(
                "Контракт уже заполнен.",
                ephemeral=True
            )
            return

        contract["members"].append(user_id)

        save_data()

        closed = len(contract["members"]) >= 4

        if closed:
            contract["closed"] = True
            save_data()

        embed = make_contract_embed(
            contract,
            interaction.guild,
            closed=closed
        )

        creator = interaction.guild.get_member(
            int(contract["creator"])
        )

        if creator:
            try:
                await creator.send(
                    f"🔔 {interaction.user.mention} присоединился к контракту #{contract['id']}."
                )
            except:
                pass

        if closed:
            await interaction.response.edit_message(
                embed=embed,
                view=NewContractView()
            )
        else:
            await interaction.response.edit_message(
                embed=embed,
                view=self
            )


class NewContractView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Создать новый контракт",
        style=discord.ButtonStyle.primary,
        custom_id="new_contract_button"
    )
    async def new_contract(self, interaction: discord.Interaction, button: discord.ui.Button):
        global contract_counter

        contract_counter += 1

        contract = {
            "id": contract_counter,
            "creator": str(interaction.user.id),
            "members": [str(interaction.user.id)],
            "closed": False
        }

        embed = make_contract_embed(
            contract,
            interaction.guild
        )

        view = ContractView()

        await interaction.response.send_message(
            content=f"<@&{FAMILY_ROLE_ID}>",
            embed=embed,
            view=view,
            allowed_mentions=discord.AllowedMentions(roles=True)
        )

        message = await interaction.original_response()

        contracts[str(message.id)] = contract

        save_data()


@bot.event
async def on_ready():
    load_data()

    bot.add_view(LobbyView())
    bot.add_view(ContractView())
    bot.add_view(NewContractView())

    print("-----------------------------")
    print(f"Бот запущен как {bot.user}")
    print("-----------------------------")


@bot.command()
async def setup_contracts(ctx):
    embed = make_lobby_embed()

    view = LobbyView()

    await ctx.send(
        embed=embed,
        view=view
    )


bot.run(TOKEN)