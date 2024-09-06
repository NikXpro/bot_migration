import discord
from discord.ext import commands
import asyncio
import time

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

role_mapping = {
    "client": "customers",
}

AUTHORIZED_USER_ID = 372925126808961025
ATTRIBUER_NOUVEAU_MEMBRE_A_TOUS = True


@bot.event
async def on_ready():
    print(f'{bot.user} est connecté et prêt!')


def create_progress_bar(progress, total, length=20):
    filled_length = int(length * progress // total)
    bar = '█' * filled_length + '▒' * (length - filled_length)
    percent = f"{100 * progress / total:.1f}"
    return bar, percent


def format_time(seconds):
    if seconds < 60:
        return f"{seconds:.0f} secondes"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} minutes"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} heures"


async def update_embed(message, embed, processed, total, eta):
    bar, percent = create_progress_bar(processed, total)
    embed.set_field_at(0, name="Status", value=f"En cours... \n{bar}", inline=False)
    embed.set_field_at(1, name="Progression", value=f"{percent}%", inline=True)
    embed.set_field_at(2, name="Membres traités", value=f"{processed}/{total}", inline=True)
    embed.set_field_at(3, name="Temps estimé restant", value=format_time(eta), inline=True)
    embed.set_field_at(4, name="Temps total estimé", value=format_time(eta), inline=True)
    await message.edit(embed=embed)


async def verify_roles(guild):
    missing_roles = []
    for old_role, new_role in role_mapping.items():
        if not discord.utils.get(guild.roles, name=old_role):
            missing_roles.append(f"Ancien rôle '{old_role}'")
        if not discord.utils.get(guild.roles, name=new_role):
            missing_roles.append(f"Nouveau rôle '{new_role}'")
    return missing_roles


@bot.command()
async def transferer_roles(ctx):
    if ctx.author.id != AUTHORIZED_USER_ID:
        await ctx.send("Désolé, vous n'êtes pas autorisé à utiliser cette commande.")
        return

    guild = ctx.guild

    # Vérification de l'existence des rôles
    missing_roles = await verify_roles(guild)
    if missing_roles:
        error_message = "Migration annulée. Les rôles suivants n'existent pas :\n" + "\n".join(missing_roles)
        embed = discord.Embed(title="Erreur de Transfert des Rôles", color=discord.Color.red(),
                              description=error_message)
        await ctx.send(embed=embed)
        return

    members = guild.members
    total_members = len(members)
    processed_members = 0

    embed = discord.Embed(title="Transfert et Attribution des Rôles", color=discord.Color.blue())
    embed.add_field(name="Status", value="Initialisation...", inline=False)
    embed.add_field(name="Progression", value="0%", inline=True)
    embed.add_field(name="Membres traités", value="0/" + str(total_members), inline=True)
    embed.add_field(name="Temps estimé restant", value="Calcul en cours...", inline=True)
    embed.add_field(name="Temps total estimé", value="Calcul en cours...", inline=True)
    progress_message = await ctx.send(embed=embed)

    last_update = 0
    update_interval = max(1, min(total_members // 100, 50))
    start_time = time.time()

    nouveau_membre_role = discord.utils.get(guild.roles, name="nouveau_membre")

    for member in members:
        try:
            roles_changed = False

            if ATTRIBUER_NOUVEAU_MEMBRE_A_TOUS:
                if nouveau_membre_role not in member.roles:
                    await member.add_roles(nouveau_membre_role)
                    roles_changed = True
                    await asyncio.sleep(0.25)  # Attente pour respecter les limites de taux

            for old_role_name, new_role_name in role_mapping.items():
                old_role = discord.utils.get(guild.roles, name=old_role_name)
                new_role = discord.utils.get(guild.roles, name=new_role_name)

                if old_role and new_role and old_role in member.roles:
                    if not ATTRIBUER_NOUVEAU_MEMBRE_A_TOUS or new_role_name != "nouveau_membre":
                        await member.remove_roles(old_role)
                        await asyncio.sleep(0.45)
                        await member.add_roles(new_role)
                        await asyncio.sleep(0.45)
                        roles_changed = True

            if roles_changed:
                processed_members += 1

            if processed_members - last_update >= update_interval or processed_members == total_members:
                elapsed_time = time.time() - start_time
                members_per_second = processed_members / elapsed_time
                eta = (total_members - processed_members) / members_per_second
                await update_embed(progress_message, embed, processed_members, total_members, eta)
                last_update = processed_members

        except discord.errors.Forbidden:
            print(f"Erreur: Permissions insuffisantes pour modifier les rôles de {member.name}")
        except Exception as e:
            print(f"Erreur lors du traitement de {member.name}: {str(e)}")

        await asyncio.sleep(0.25)  # Attente générale entre chaque membre

    total_time = time.time() - start_time
    embed.set_field_at(0, name="Status", value="Terminé ✅", inline=False)
    embed.set_field_at(3, name="Temps total", value=format_time(total_time), inline=True)
    embed.set_field_at(4, name="Temps moyen par membre", value=format_time(total_time / total_members), inline=True)
    await progress_message.edit(embed=embed)

bot.run('')