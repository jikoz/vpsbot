import discord
from discord import app_commands
from discord.ext import commands
from datetime import timedelta

TOKEN = "YOUR_BOT_TOKEN"

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Sync slash commands
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

# ✅ Check if user is Admin
def is_admin():
    async def predicate(interaction: discord.Interaction):
        return interaction.user.guild_permissions.administrator
    return app_commands.check(predicate)

# =========================
# 🔥 PURGE COMMAND
# =========================
@bot.tree.command(name="purge", description="Delete multiple messages")
@is_admin()
async def purge(interaction: discord.Interaction, amount: int):
    await interaction.response.defer(ephemeral=True)
    await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"Deleted {amount} messages.", ephemeral=True)

# =========================
# 🔨 BAN COMMAND
# =========================
@bot.tree.command(name="ban", description="Ban a member")
@is_admin()
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    await member.ban(reason=reason)
    await interaction.response.send_message(f"{member.mention} has been banned.", ephemeral=True)

# =========================
# 👢 KICK COMMAND
# =========================
@bot.tree.command(name="kick", description="Kick a member")
@is_admin()
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    await member.kick(reason=reason)
    await interaction.response.send_message(f"{member.mention} has been kicked.", ephemeral=True)

# =========================
# ⏳ TIMEOUT COMMAND
# =========================
@bot.tree.command(name="timeout", description="Timeout a member (minutes)")
@is_admin()
async def timeout(interaction: discord.Interaction, member: discord.Member, minutes: int):
    duration = timedelta(minutes=minutes)
    await member.timeout(duration)
    await interaction.response.send_message(f"{member.mention} has been timed out for {minutes} minutes.", ephemeral=True)

# =========================
# 📩 DM COMMAND
# =========================
@bot.tree.command(name="dm", description="Send DM to a member")
@is_admin()
async def dm(interaction: discord.Interaction, member: discord.Member, message: str):
    try:
        await member.send(message)
        await interaction.response.send_message("DM sent successfully.", ephemeral=True)
    except:
        await interaction.response.send_message("Failed to send DM.", ephemeral=True)

# =========================
# 🎟️ TICKET SETUP
# =========================
class TicketButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.green)
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True)
        }

        channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            overwrites=overwrites
        )

        await channel.send(f"{interaction.user.mention} Ticket created!")
        await interaction.response.send_message("Ticket created!", ephemeral=True)

@bot.tree.command(name="ticket_setup", description="Setup ticket system")
@is_admin()
async def ticket_setup(interaction: discord.Interaction):
    view = TicketButton()
    await interaction.channel.send("Click below to create a ticket:", view=view)
    await interaction.response.send_message("Ticket system setup complete.", ephemeral=True)

bot.run(TOKEN)
# -------------------- LIST VPS --------------------

@bot.tree.command(name="vps_list", description="List VPS (Admin only)")
async def vps_list(interaction: discord.Interaction):
    if not is_admin(interaction.user.id):
        return await interaction.response.send_message("Admin only!", ephemeral=True)

    msg = "\n".join([f"{k} -> {v['owner']} ({v['status']})" for k, v in data["vps"].items()])
    await interaction.response.send_message(msg or "No VPS")

# -------------------- DELETE VPS --------------------

@bot.tree.command(name="delete_vps", description="Delete VPS (Admin only)")
async def delete_vps(interaction: discord.Interaction, name: str):
    if not is_admin(interaction.user.id):
        return await interaction.response.send_message("Admin only!", ephemeral=True)

    subprocess.run(["docker", "rm", "-f", name])
    data["vps"].pop(name, None)
    save_data(data)

    await interaction.response.send_message("VPS deleted!")

# -------------------- SUSPEND VPS --------------------

@bot.tree.command(name="suspend_vps", description="Suspend VPS (Admin only)")
async def suspend_vps(interaction: discord.Interaction, name: str):
    if not is_admin(interaction.user.id):
        return await interaction.response.send_message("Admin only!", ephemeral=True)

    subprocess.run(["docker", "stop", name])
    data["vps"][name]["status"] = "stopped"
    save_data(data)

    await interaction.response.send_message("VPS suspended!")

# -------------------- MANAGE PUBLIC --------------------

@bot.tree.command(name="manage", description="Manage your VPS")
async def manage(interaction: discord.Interaction):
    owned = [k for k, v in data["vps"].items() if v["owner"] == str(interaction.user.id)]
    await interaction.response.send_message(f"Your VPS: {owned}")

# -------------------- CHANGE PASSWORD --------------------

@bot.tree.command(name="change_passwd", description="Change VPS password")
async def change_passwd(interaction: discord.Interaction, name: str):
    if name not in data["vps"]:
        return await interaction.response.send_message("VPS not found")

    if data["vps"][name]["owner"] != str(interaction.user.id):
        return await interaction.response.send_message("Not your VPS", ephemeral=True)

    new_pass = generate_password()
    subprocess.run(["docker", "exec", name, "bash", "-c",
                    f"echo 'user:{new_pass}' | chpasswd"])

    data["vps"][name]["password"] = new_pass
    save_data(data)

    await interaction.response.send_message(f"New Password: `{new_pass}`")

bot.run(TOKEN)
