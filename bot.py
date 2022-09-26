# bot.py
import os
import discord
from discord import message
from dotenv import dotenv_values
from discord.ext import commands
import sqlite3
import re
import random
import ssl
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


###############################################################################
# SQL queries 
###############################################################################
""" check to see if user exists in the database """
def check_user(userID):
    c.execute("SELECT * FROM users WHERE userid=?", (userID,))
    return c.fetchone()

""" add a user, code, and email address to the database """
def add_user(userID):
    c.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (userID, None, None, 0))
    conn.commit()

""" remove the user from the database if they leave the server """
def remove_user(userID):
    c.execute("DELETE FROM users WHERE userID=?", (userID,))

""" update email address """
def update_email(userID, email):
    c.execute("UPDATE users SET email=? WHERE userid=?", (email, userID))
    conn.commit()

""" update code """
def update_code(userID, code):
    c.execute("UPDATE users SET code=? WHERE userid=?", (code, userID))
    conn.commit()

""" verify user """
def verify_user(userID):
    c.execute("UPDATE users SET verified=1 WHERE userid=?", (userID,))
    conn.commit()


###############################################################################
# Various functions
###############################################################################
""" check if an email address...is an email address """
def email_check(email):
        regex = "(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|\"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*\")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])"
        if re.search(regex,email):
            return True
        else:
            return False

""" check if the user has been verified yet """
def check_if_verified(userID):
    record = check_user(userID)
    verified = record[3]
    if verified == 0:
        return False
    elif verified == 1:
        return True

""" check if user has been sent a verification code """
def check_if_email(userID):
    record = check_user(userID)
    email = record[1]
    if email == None:
        return False
    else:
        return True

""" get the absolute path for a file """
def abs_path(path):
    return os.path.abspath(path)


###############################################################################
# Get the Discord token and Gmail password from the .env file so pica can login
###############################################################################
token_values = dotenv_values(abs_path(".env"))
TOKEN = token_values['PICA_TOKEN']
GMAIL_PASSWORD = token_values['GMAIL_PASSWORD']
GUILD_ID = token_values['GUILD_ID']


###############################################################################
# Setup the users database
###############################################################################
conn = sqlite3.connect(abs_path("magpies.db"))
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS users(
   userid INT,
   email TEXT,
   code INT,
   verified INT);
""")

###############################################################################
# Log in the bot and start it up!
###############################################################################
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="P;!", intents=intents, help_command=None)


###############################################################################
# Event handler for connecting to discord
###############################################################################
@bot.event
async def on_ready():
    print('pica has connected to Discord')
    await bot.change_presence(activity=discord.Game("https://github.com/infosec-ucalgary/pica-bot"))


###############################################################################
# Print message when they join the server
###############################################################################
@bot.event
async def on_member_join(member):
    add_user(member.id)
    await member.send("Welcome to the Manzara's Magpies CTF team Discord server!\n\n" \
                      "To confirm you are a member of the team, please reply to this " \
                      "message with your @magpie.com email address and we will send " \
                      "you a email with your verification code.")


###############################################################################
# When someone leaves the server
###############################################################################
@bot.event
async def on_member_remove(member):
    # remove the user from the database
    remove_user(member.id)


###############################################################################
# Main message loop
###############################################################################
@bot.event
async def on_message(message):
    # check to see if the bot is talking to itself!
    if message.author == bot.user:
        return
    # strip the message of whitespace    
    message_content = message.content.strip()

    # Only reply to direct messages
    if isinstance(message.channel, discord.DMChannel):
        # the message is an email address
        if email_check(message_content):
            # if they have not been verified
            if not check_if_verified(message.author.id):
                # If it is a valid @magpie.com email address:
                if "@magpie.com" in message_content:
                    # generate verification code
                    verification_code = random.randint(100000, 999999)
                    # add their email address and verification code to the database
                    update_email(message.author.id, message_content)
                    update_code(message.author.id, verification_code)
                    # setup the email message to send them
                    port = 465
                    email_message = MIMEMultipart("alternative")
                    email_message["Subject"] = "Manzara's Magpies Verification Code"
                    email_message["From"] = "manzarasmagpies@gmail.com"
                    email_message["To"] = message_content
                    text = str(verification_code)
                    compiled = MIMEText(text, "plain")
                    email_message.attach(compiled)
                    # Create a secure SSL context for the gmail account to send the email
                    context = ssl.create_default_context()
                    # send the verification email from the gmail account
                    with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
                        server.login("manzarasmagpies@gmail.com", GMAIL_PASSWORD)
                        server.sendmail("manzarasmagpies@gmail.com", message_content, email_message.as_string())
                    await message.channel.send("A verification code has been emailed to you.  **Please reply to me with the " \
                                    "verficiation code to be added to the Manzara's Magpies server.** If you haven't received it, check your spam folder.")
                else:
                    await message.channel.send("That is not a valid email address.  If you do not yet have a valid @magpie.com " \
                                               "email address, please contact The University of Calgary Bureaucracy Club.")
            else:
                # If they're already verified, tell them to smarten up!
                await message.channel.send("You have already been verified.  Cut it out!")
        # check if this is a verification code
        elif (len(message_content) == 6) and message_content.isdigit():
            # check if they've submitted a valid @magpie.com email address yet
            if not check_if_email(message.author.id):
                await message.channel.send("You have not submitted a valid @magpie.com email address yet. " \
                                           "You must submit a valid email address before you can submit a " \
                                           "verification code.")
            # check if they're verified, and if not check their verification code
            elif not check_if_verified(message.author.id):
                # get their verification code from the database
                user_records = check_user(message.author.id)
                verification_code = user_records[2]
                # check the verification code in the database against the message they sent
                if verification_code == int(message_content):
                    # assign them the magpie role
                    server = bot.get_guild(int(GUILD_ID))
                    role = discord.utils.get(server.roles, name="magpie")
                    member = server.get_member(message.author.id)
                    await member.add_roles(role)
                    # announce that they're in to the server!
                    channel = discord.utils.get(server.text_channels, name='general')
                    if channel is not None:
                        new_user = message.author
                        await channel.send(f"A new magpie has landed!  Everyone welcome {new_user}!!!\n" \
                                            "https://c.tenor.com/EdyX5M8Vi7wAAAAC/magpie.gif")
                    # add them as verified in the database
                    verify_user(message.author.id)
                    await message.channel.send("Verification code match!  Welcome to Manzara's Magpies!")
                else:
                    await message.channel.send("Verification code does not match.")
            else:
                await message.channel.send("You have already been verified.  Cut it out!")
    await bot.process_commands(message)


###############################################################################
# Help message for interacting with pica
###############################################################################
@bot.command(name="help")
async def help_command(ctx):
    # Display help message
    response = "Hello, I am pica.\n\nThese are my user commands, remember to prefix them with \"P;!\" :\n" \
               "    help:        Display this message\n" \
               "    addrole:     Give yourself a specialization role\n" \

    embed = discord.Embed(description=response, color=0x4c4fb1)
    await ctx.send(embed=embed)

###############################################################################
# Command to give a user a requested specialization role.  The desired role
# should be listed in the command
###############################################################################
@bot.command(name="addrole")
async def addrole(ctx, *, role=''):
    channel = ctx.message.channel

    if not isinstance(channel, discord.DMChannel):
        try:
            if "cryptography" in role.lower():
                await ctx.author.add_roles(discord.utils.get(ctx.author.guild.roles, name="Cryptography"))
                await ctx.send("You have been given the Cryptography role.")
            elif "forensics" in role.lower():
                await ctx.author.add_roles(discord.utils.get(ctx.author.guild.roles, name="Forensics"))
                await ctx.send("You have been given the Forensics role.")
            elif "binary exploitation" in role.lower():
                await ctx.author.add_roles(discord.utils.get(ctx.author.guild.roles, name="Binary Exploitation"))
                await ctx.send("You have been given the Binary Exploitation role.")
            elif "web exploitation" in role.lower():
                await ctx.author.add_roles(discord.utils.get(ctx.author.guild.roles, name="Web Exploitation"))
                await ctx.send("You have been given the Web Exploitation role.")
            elif "reverse engineering" in role.lower():
                await ctx.author.add_roles(discord.utils.get(ctx.author.guild.roles, name="Reverse Engineering"))
                await ctx.send("You have been given the Reverse Engineering role.")
            elif "networks" in role.lower():
                await ctx.author.add_roles(discord.utils.get(ctx.author.guild.roles, name="Networks"))
                await ctx.send("You have been given the Networks role.")
            elif "osint" in role.lower():
                await ctx.author.add_roles(discord.utils.get(ctx.author.guild.roles, name="OSINT"))
                await ctx.send("You have been given the OSINT role.")
            else:
                response = "Please use this command followed immediately by a desired role selected from cryptography, forensics, binary exploitation, web exploitation," \
                           "osint, or reverse engineering.\nExample usage:    P;!addrole binary exploitation"
                await ctx.send(response)
        except:
            await ctx.send("There was an error using this command. Make sure you are using it in an appropriate server.")
    else:
        await ctx.send("I cannot add roles from direct messages.  Please run this command in the server!")


bot.run(TOKEN)
