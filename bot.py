import discord
from discord.ext import commands
from discord import app_commands
import os
import subprocess
import json
import random
import string
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DEFAULT_OS = os.getenv("DEFAULT_OS_IMAGE", "ubuntu:22.04")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "vps_data.json"

# -------------------- DATABASE --------------------

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"admins": [], "vps": {}}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

# -------------------- UTILS --------------------

def generate_password(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def is_admin(user_id):
    return str(user_id) in data["admins"]

# -------------------- EVENTS --------------------

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot ready as {bot.user}")

# -------------------- ADMIN COMMANDS --------------------

@bot.tree.command(name="admin_add", description="Add new admin")
async def admin_add(interaction: discord.Interaction, user: discord.User):
    if not is_admin(interaction.user.id):
        return await interaction.response.send_message("Admin only!", ephemeral=True)

    data["admins"].append(str(user.id))
    save_data(data)
    await interaction.response.send_message("Admin added!")

@bot.tree.command(name="list_admin", description="List admins")
async def list_admin(interaction: discord.Interaction):
    if not is_admin(interaction.user.id):
        return await interaction.response.send_message("Admin only!", ephemeral=True)

    await interaction.response.send_message(f"Admins: {data['admins']}")

@bot.tree.command(name="remove_admin", description="Remove admin")
async def remove_admin(interaction: discord.Interaction, user: discord.User):
    if not is_admin(interaction.user.id):
        return await interaction.response.send_message("Admin only!", ephemeral=True)

    data["admins"].remove(str(user.id))
    save_data(data)
    await interaction.response.send_message("Admin removed!")

# -------------------- CREATE VPS --------------------

@bot.tree.command(name="create_vps", description="Create VPS (Admin only)")
async def create_vps(interaction: discord.Interaction, user: discord.User):
    if not is_admin(interaction.user.id):
        return await interaction.response.send_message("Admin only!", ephemeral=True)

    container_name = f"vps_{user.id}"
    password = generate_password()

    try:
        subprocess.run(["docker", "run", "-dit", "--name", container_name, DEFAULT_OS], check=True)
        subprocess.run(["docker", "exec", container_name, "bash", "-c",
                        f"useradd -m user && echo 'user:{password}' | chpasswd"], check=True)

        data["vps"][container_name] = {
            "owner": str(user.id),
            "password": password,
            "status": "running"
        }

        save_data(data)

        await interaction.response.send_message(
            f"VPS Created!\nName: `{container_name}`\nUser: `user`\nPassword: `{password}`"
        )

    except:
        await interaction.response.send_message("Failed to create VPS", ephemeral=True)

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
