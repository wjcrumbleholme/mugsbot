# Send message in a channel and let users react for each week to sign up for 6hrs on sunday night, draw names on monday morning
# Randomise the users and send everyone a message in a dm (not their own)
# Let everyone who has signed up submit 1 photo into #mug of the week submissions / delete anyone who is not signed up or put more than one message in the channel, allow this through the weekend
# Monday mornings, close submissions and open voting (everyone has 3 votes) untill the end of the day
# On tuseday morning, announce winners and update the leaderboard



#TODO
#Need to make it post the winners in ⁠mug-of-the-week along with who posted it and what place they came
#Make bounty system, admins will have to manually reveiw photos and if there is metadata, post it with it.


import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View
import asyncio
import random
import json
import os
import datetime
from PIL import Image, ExifTags
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apikeys import *


SERVER_ID = 1157045575250878567
CHANNEL_ID = 1157045577545167002
SIGNUP_CHANNEL_ID = 1157261080503001118
MUG_SUBMISSIONS_ID = 1157292030137999460
MOTW_ROLE = 1160688315893301389


users_signed_up = [] #Stores the signed up users
final_rand_users_signed_up = [] #Stores the users that get sent out to signed up people
prev_img_sub_usr_list = [] #Used to check if a user had already submitted a mug
prev_img_dict = {} #Used to keep track of wh posted what
usr_votes = {} #Used to keep track of how many votes a user has
old_top_scores = [] #Used to store all the scores in
vote_tracker = {} #Tracks what image a user has voted on
curr_leaderboard = "" #Stores the last leaderboard.
overall_leaderboard = {} #Stores overall score for all users

toggles = {"sign_up": False,
           "sub_mug": False,
           "voting": False
           }


bot = commands.Bot(command_prefix= '-', intents=discord.Intents.all())


#-----Start-up---------#

@bot.event
async def on_ready():
    print("Bot is ready.")
    print("---------------")

    try:
        await load_all_files('./backups')
        print("Successfully loaded configs.")
    except:
        print("Error with loading configs.")

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)

    bot.add_view(MugView())
    bot.add_view(SignUpView())

    # scheduler = AsyncIOScheduler()
    # scheduler.configure(timezone='gmt')
    # scheduler.add_job(test,CronTrigger(minute='0'))
    # scheduler.start()
    

#-------------------------------------#


#----File Storing-----#

async def store_file(data, name):
    with open('./backups/backup_'+f'{name}'+'.json', "w") as f:
        json.dump(data, f, indent=2)
        print(f"Stored: {data} to file")

async def store_all_files(directory):
    for filename in os.listdir(directory):
        store_file(globals()[filename[7:-5]], filename)

#----File Loading----#
async def load_file(filename):
    with open(f"./backups/{filename}", "r") as f:
        globals()[filename[7:-5]] = json.load(f)
        print(f"Loaded: {filename}")

async def load_all_files(directory):
    for filename in os.listdir(directory):
            if filename.endswith('.json'):
                await load_file(filename)

#-----Useful relevant commands-----#

@bot.tree.command(name="toggle_sign_up", description="(Admin) Toggles sign up")
async def sign_up_command(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You do not have permission to do that", ephemeral=True)
    else:
        if toggles.get("sign_up") == False:
            toggles["sign_up"] = True
            c = bot.get_channel(SIGNUP_CHANNEL_ID)
            msg = await c.send("Click the button to sign up for this week's mug of the week.",view=SignUpView())
            toggles["sign_up_msg_id"] = msg.id
            await store_file(toggles,f'{toggles=}'.split('=')[0])
            await interaction.response.send_message("Sent sign up message.",ephemeral=True)
        else:
            toggles["sign_up"] = False
            await bot.get_channel(SIGNUP_CHANNEL_ID).get_partial_message(toggles.get("sign_up_msg_id")).delete()
            await store_file(toggles,f'{toggles=}'.split('=')[0])
            await interaction.response.send_message("Unsent sign up message.", ephemeral=True)

@bot.tree.command(name="toggle_mug_submission",description="(Admin) Toggles if mugs can be submitted")
async def mug_sub_command(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You do not have permission to do that", ephemeral=True)
    else:
        if toggles.get("sub_mug") == False:
            toggles["sub_mug"] = True
            await store_file(toggles,f'{toggles=}'.split('=')[0])
            await interaction.response.send_message("Enabled mugs to be able to be sent", ephemeral=True)
        else:
            toggles["sub_mug"] = False
            await store_file(toggles,f'{toggles=}'.split('=')[0])
            await interaction.response.send_message("Disabled mugs to be able to be sent", ephemeral=True)
        

@bot.tree.command(name="toggle_voting",description="(Admin) Toggles votes on mugs")
async def mug_vote_command(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You do not have permission to do that", ephemeral=True)
    else:
        if toggles.get("voting") == False:
            toggles["voting"] = True
            await interaction.response.send_message("Enabled mugs to be able to be voted on", ephemeral=True)
            for key in prev_img_dict:
                await bot.get_channel(MUG_SUBMISSIONS_ID).get_partial_message(int(key)).edit(view=MugView())
            await store_file(toggles,f'{toggles=}'.split('=')[0])
        else:
            toggles["voting"] = False
            await interaction.response.send_message("Disabled mugs to be able to be voted on", ephemeral=True)
            for key in prev_img_dict:
                await bot.get_channel(MUG_SUBMISSIONS_ID).get_partial_message(int(key)).edit(view=None)
            await store_file(toggles,f'{toggles=}'.split('=')[0])

@bot.tree.command(name="clear_all",description="(Admin) Clears all backups DONT RUN UNLESS NESSISARY")
async def mug_sub_command(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You do not have permission to do that", ephemeral=True)
    else:
        files_to_delete = ["users_signed_up", "final_rand_users_signed_up", "prev_img_sub_usr_list", "prev_img_dict", "usr_votes","old_top_scores","vote_tracker"]
        for filename in os.listdir("./backups"):
            if filename[7:-5] in files_to_delete:
                os.remove(f"./backups/{filename}")
        await interaction.response.send_message("Successfullu cleared backups", ephemeral=True)

# @bot.tree.command(name="save_file", description="Test to see if metadata is retained")
# async def save_usr_files(interaction: discord.Interaction, file: discord.Attachment):
#     await file.save(file.filename)
#     await interaction.response.send_message("Successfully saved file", ephemeral=True)
#     print(file.filename)
#     await image_date(f"{file.filename}")
    
    
    
# async def image_date(filename):
#     image_exif = Image.open(filename)._getexif()
#     if image_exif:
#         # Make a map with tag names
#         exif = { ExifTags.TAGS[k]: v for k, v in image_exif.items() if k in ExifTags.TAGS and type(v) is not bytes }
#         print(json.dumps(exif, indent=4))
#         # Grab the date
#         date_obj = datetime.strptime(exif['DateTimeOriginal'], '%Y:%m:%d %H:%M:%S')
#         print(date_obj)
#     else:
#         print('Unable to get date from exif for %s' % filename)
        


#-----Sign up stuff------#

class SignUpView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Click to sign up!", custom_id="sign_up", style=discord.ButtonStyle.green)
    async def button_callback(self, interaction, button):
        await on_sign_up(interaction)

    @discord.ui.button(label="", custom_id="sign_up_cancel", style=discord.ButtonStyle.gray, emoji="❌")
    async def vote_button_callback(self, interaction, button):
        await on_sign_up_cancel(interaction)

async def on_sign_up(interaction):
    user = interaction.user.id
    if (user in users_signed_up):
        await interaction.response.send_message("You have already signed up.",ephemeral=True)
    else:
        users_signed_up.append(user)
        await interaction.response.send_message("You have successfully signed up for mug of the week for this week.",ephemeral=True)
        await store_file(users_signed_up,f'{users_signed_up=}'.split('=')[0])
        role = bot.get_guild(SERVER_ID).get_role(MOTW_ROLE)
        roleuser = await bot.get_guild(SERVER_ID).fetch_member(user)
        await roleuser.add_roles(role)
        

async def on_sign_up_cancel(interaction):
    user = interaction.user.id
    if (user in users_signed_up):
        users_signed_up.remove(user)
        await interaction.response.send_message("You have been successfully removed from mug of the week for this week.",ephemeral=True)
        await store_file(users_signed_up,f'{users_signed_up=}'.split('=')[0])
        role = bot.get_guild(SERVER_ID).get_role(MOTW_ROLE)
        roleuser = await bot.get_guild(SERVER_ID).fetch_member(user)
        await roleuser.remove_roles(role)
    else:
        await interaction.response.send_message("You haven't signed up so can't be removed.",ephemeral=True)


#--------------------------------------#



#-----Rand dm stuff-------#

# send a message to a user in a dm

@bot.tree.command(name="send_rand_dms", description="(Admin) sends the dms to all the people signed up with their mugtims")
async def send_rand_dm(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You do not have permission to do that", ephemeral=True)
    else:
        await interaction.response.defer(ephemeral=True)
        final_rand_users_signed_up = []
        rand_users_signed_up = users_signed_up.copy()
        random.shuffle(rand_users_signed_up)
        for i in range(0, len(users_signed_up)):
            while users_signed_up[i] == rand_users_signed_up[0]:
                if(i == len(users_signed_up)-1):
                    temp = final_rand_users_signed_up[i-1]
                    final_rand_users_signed_up[i-1] = rand_users_signed_up[0]
                    rand_users_signed_up[0] = temp
                    await store_file(final_rand_users_signed_up,f'{final_rand_users_signed_up=}'.split('=')[0])
                else:
                    random.shuffle(rand_users_signed_up)
            else:
                final_rand_users_signed_up.append(rand_users_signed_up[0])
                await store_file(final_rand_users_signed_up,f'{final_rand_users_signed_up=}'.split('=')[0])
                rand_users_signed_up.remove(rand_users_signed_up[0])
        
        for i in range(0, len(users_signed_up)):
            guild = await bot.fetch_guild(SERVER_ID)
            dmsend = await guild.fetch_member(users_signed_up[i])
            dmuser = dmsend
            dmvict = await guild.fetch_member(final_rand_users_signed_up[i])


            if dmuser.nick == None:
                dmuser = dmuser
            else:
                dmuser = dmuser.nick


            if dmvict.nick == None:
                dmvict = dmvict
            else:
                dmvict = dmvict.nick


            await dmsend.send(f"Hello {dmuser}, you have got to mug {dmvict} this week. Once you have got the best mug you can, run /submit_mug in any channel. You have untill friday evening to do this.")

        await interaction.followup.send("Successfully sent dms.", ephemeral=True)

             
        


#-------------------------------------#


#------Mug submission-----#

#allows the user to do /sub_photos to submit one photo per week
@bot.tree.command(name="submit_mug", description="Use this command to submit mugs")
async def sub_photos(interaction: discord.Interaction, file: discord.Attachment):
    
    if toggles.get("sub_mug") == True:
        if (interaction.user.id in users_signed_up):
            if interaction.user.id not in prev_img_sub_usr_list:
                await interaction.response.send_message("Mug successfully submitted",ephemeral=True)
                c = bot.get_channel(MUG_SUBMISSIONS_ID)
                if toggles["sign_up"] == False:
                    currview = None
                else:
                    currview = MugView()
                msg = await c.send(file, view=currview)
                prev_img_sub_usr_list.append(interaction.user.id)
                await store_file(prev_img_sub_usr_list,f'{prev_img_sub_usr_list=}'.split('=')[0])
                prev_img_dict.update({str(msg.id): interaction.user.id})
                await store_file(prev_img_dict,f'{prev_img_dict=}'.split('=')[0])
            else:
                await interaction.response.send_message("You have already submitted your mug for this week.",ephemeral=True)
        else:
            await interaction.response.send_message("You did not sign up this week, so you cant submit a mug.",ephemeral=True)
    else:
        await interaction.response.send_message("Mugs are not able to be sent at this time.", ephemeral=True)
    

class MugView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="", custom_id="mug_up", style=discord.ButtonStyle.gray, emoji="⬆️")
    async def button_callback(self, interaction, button):
        await on_vote(interaction)

    @discord.ui.button(label="", custom_id="mug_cancel", style=discord.ButtonStyle.gray, emoji="❌")
    async def vote_button_callback(self, interaction, button):
        await on_vote_removal(interaction)

async def on_vote(interaction):
    user = interaction.user.id
    msg = interaction.message.id

    if (str(msg) in vote_tracker): #Check if user has voted on the mug before
        pass
    else:
        vote_tracker.update({str(msg):[]})
        await store_file(vote_tracker,f'{vote_tracker=}'.split('=')[0])

    img_voters = vote_tracker.get(str(msg))
    if(prev_img_dict.get(str(msg)) == user): #Check if the mug belogns to the person who submitted it
        await interaction.response.send_message("You cannot vote on your own mug!", ephemeral=True)
    elif (user in img_voters): #Check if user has already voted on the mug
        await interaction.response.send_message("You have already voted on this mug!", ephemeral = True)
    elif (str(user) not in usr_votes): #If user hasnt voted before, add them to the image votes and to the main votes
        vote_temp = vote_tracker.get(str(msg))
        vote_temp = vote_temp + [user]
        vote_tracker[str(msg)] = vote_temp
        await store_file(vote_tracker,f'{vote_tracker=}'.split('=')[0])
        usr_votes[str(user)] = 2
        await store_file(usr_votes,f'{usr_votes=}'.split('=')[0])
        await interaction.response.send_message(f"You have {usr_votes[str(user)]} votes remaining.", ephemeral=True)
    elif (usr_votes.get(str(user)) == 0): #If user has run out of votes, give an error message
        await interaction.response.send_message("You cannot vote as you have 0 votes remaining.", ephemeral=True)
    else: #If user has voted before, but not for this image, add them to the image votes and subtract 1 from main votes
        vote_temp = vote_tracker.get(str(msg))
        vote_temp = vote_temp + [user]
        vote_tracker[str(msg)] = vote_temp
        await store_file(vote_tracker,f'{vote_tracker=}'.split('=')[0])
        num = usr_votes.get(str(user))
        num = num - 1
        usr_votes[str(user)] = num
        await store_file(usr_votes,f'{usr_votes=}'.split('=')[0])
        await interaction.response.send_message(f"You have {usr_votes[str(user)]} vote(s) remaining.", ephemeral=True)
    

async def on_vote_removal(interaction):
    user = interaction.user.id
    msg = interaction.message.id
    img_voters = vote_tracker.get(str(msg))
    if(prev_img_dict.get(str(msg)) == user): #Check if the mug belogns to the person who submitted it
        await interaction.response.send_message("You cannot remove a vote on your own mug!", ephemeral=True)  
    elif (user in img_voters):
        img_voters.remove(user)
        vote_tracker[str(msg)] = img_voters
        await store_file(vote_tracker,f'{vote_tracker=}'.split('=')[0])
        num = usr_votes.get(str(user))
        num = num + 1
        usr_votes[str(user)] = num
        await store_file(usr_votes,f'{usr_votes=}'.split('=')[0])
        await interaction.response.send_message(f"Successfully removed a vote, you have {usr_votes[str(user)]} votes remaining.", ephemeral=True)
    else:
        await interaction.response.send_message("You haven't voted on this mug, so you cant remove a vote!", ephemeral=True)


#------Leaderboard stuff------------#

#command for totaling the leaderboard
@bot.tree.command(name="draw_winners", description="This command totals up the scores for the submitted mugs of the week (Admin only)")
async def ann_winn(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You do not have permission to do that", ephemeral=True)
    else:
        await interaction.response.defer(ephemeral=True)
        old_top_scores = []
        for key in prev_img_dict:
            votes = vote_tracker.get(key)
            if (votes == None):
                vote_tracker[key] = []
                votes = vote_tracker.get(key)

            votes = len(votes)
            #add all scores to a list
            old_top_scores.append([prev_img_dict[key], votes])
            await store_file(old_top_scores,f'{old_top_scores=}'.split('=')[0])
            
        


        #Group people with the same score together, so that ties work
        top_scores = await Sort(old_top_scores)
        top_scores.reverse()
        i = len(top_scores) - 1  # Start from the last index
        while i >= 1:
            if int(top_scores[i][1]) == int(top_scores[i-1][1]):
                top_scores[i-1] += top_scores[i]  # Merge the two elements
                top_scores.pop(i)  # Remove the second element
            i -= 1  # Move to the previous index

        # #group all the same values together, so that ties work
        # top_scores = await Sort(old_top_scores)
        # top_scores.reverse()
        # for i in range(0, len(top_scores) -2):
        #     if top_scores[i+1][1] == top_scores[i][1]:
        #         top_scores[i] = top_scores[i] + top_scores[i+1]
        #         top_scores.pop(i+1)
        # print(f"List - {top_scores}")

        # Try and get first, second and third place
        try:
            first = await calcplace(top_scores[0], 3)
            await calc_medal(top_scores[0], 0)
        except:
            first = "No one"

        try:
            second = await calcplace(top_scores[1], 2)
            await calc_medal(top_scores[1], 1)
        except:
            second = "No one"

        try:
            third = await calcplace(top_scores[2], 1)
            await calc_medal(top_scores[2], 2)
        except:
            third = "No one"

        # first = await calcplace(top_scores[0], 3)
        # await calc_medal(top_scores[0], 0)


        # second = await calcplace(top_scores[1], 2)
        # await calc_medal(top_scores[1], 1)


        # third = await calcplace(top_scores[2], 1)
        # await calc_medal(top_scores[2], 2)

        await interaction.followup.send(f"Drawn winners",ephemeral=True)
        c = bot.get_channel(MUG_SUBMISSIONS_ID)
        curr_leaderboard = f"First: {first}\nSecond: {second}\nThird: {third}"
        await c.send(curr_leaderboard)
        await store_file(curr_leaderboard,f'{curr_leaderboard=}'.split('=')[0])

        with open(f"./leaderboards/{datetime.date.today()}curr.json", "w") as f:
            json.dump(curr_leaderboard, f, indent= 2)

        with open(f"./leaderboards/{datetime.date.today()}overall.json", "w") as f:
            json.dump(overall_leaderboard, f, indent= 2)


        for key in prev_img_dict:
            try:
                await bot.get_channel(MUG_SUBMISSIONS_ID).get_partial_message(key).edit(view=None)
            except:
                print("Cant find image")

#Split ties back up so they can be output
async def calcplace(list1, points):
    second = ""
    if len(list1) == 2: #If only one user in position
        dmuser = ""
        try:
            guild = await bot.fetch_guild(SERVER_ID)
            dmuser = await guild.fetch_member(final_rand_users_signed_up[users_signed_up.index(list1[0])])
        except:
            print ("Cant find user")
            nametouse = ""
        
        if dmuser != "":
                if dmuser.nick != None:
                    nametouse = dmuser.nick
                else:
                    nametouse = dmuser
        else:
            nametouse = ""

        print(f"{nametouse}")
        second = f"<@{list1[0]}> - {list1[1]} vote(s)   [+{points} Point(s)] | [{nametouse} +1 Pp]" 
        await add_overall_leader(list1[0], points)
        if dmuser != "":
            await add_overall_leader(dmuser.id, 1)
        
    else:
        for i in range(1, int(len(list1)/2)+1): #If multiple users are in position
            # curruser = await bot.fetch_user(list1[(i*2)-2])
            dmuser = ""
            try:
                guild = await bot.fetch_guild(SERVER_ID)
                dmuser = await guild.fetch_member(final_rand_users_signed_up[users_signed_up.index(list1[(i*2)-2])])
            except:
                print ("Cant find user")
                nametouse = ""

            if dmuser != "":
                if dmuser.nick != "":
                    nametouse = dmuser.nick
                else:
                    nametouse = dmuser
            else:
                nametouse = ""

            print(f"{dmuser}")
            chunk = f"<@{list1[(i*2)-2]}> - {list1[(i*2)-1]} vote(s)   [+{points} Point(s)] | [{nametouse} +1 Pp]"
            await add_overall_leader(list1[(i*2)-2], points)
            if dmuser != "":
                await add_overall_leader(dmuser.id, 1)
            if i == int(len(list1))/2:
                second = second + chunk
            else:
                second = second + chunk + "   and   "
            
    return second

#Awards medals to mugs
async def calc_medal(list2, place):
    try:
        match place:
            case 0:
                medal = "🥇"
            case 1:
                medal = "🥈"
            case 2:
                medal = "🥉"
        if len(list2) == 2:
            #Find user who sent the message by looping through pre_img_dict
            #Check that the list2[0] message is the same as the pre_img_dict[key]
            for key in prev_img_dict:
                if prev_img_dict.get(key) == list2[0]:
                    await bot.get_channel(MUG_SUBMISSIONS_ID).get_partial_message(key).add_reaction(medal)
        elif len(list2) > 2:
            for i in range (1, int(len(list2)/2)+1):
                for key in prev_img_dict:
                    if prev_img_dict.get(key) == list2[(i*2)-2]:
                        await bot.get_channel(MUG_SUBMISSIONS_ID).get_partial_message(key).add_reaction(medal)
    except:
        print("Cant find image to put medal on.")

#Add points to the overall leaderboard
async def add_overall_leader(user_id, points):
    if str(user_id) in overall_leaderboard:
        num = overall_leaderboard.get(str(user_id))
        num = num + points
        overall_leaderboard[str(user_id)] = num
        await store_file(overall_leaderboard,f'{overall_leaderboard=}'.split('=')[0])
    else:
        overall_leaderboard[str(user_id)] = points
        await store_file(overall_leaderboard,f'{overall_leaderboard=}'.split('=')[0])



async def Sort(sub_li):
   
    l = len(sub_li)
     
    for i in range(0, l):
        for j in range(0, l-i-1):
             
            if (sub_li[j][1] > sub_li[j + 1][1]):
                tempo = sub_li[j]
                sub_li[j] = sub_li[j + 1]
                sub_li[j + 1] = tempo
     
    return sub_li


@bot.tree.command(name="current_leaderboard", description="Use this command to look at the last leaderboard")
async def send_curr_leader(interaction: discord.Interaction):
    if curr_leaderboard == "":
        await interaction.response.send_message("No previous leaderboard to show.", ephemeral=True)
    else:
        await interaction.response.send_message(curr_leaderboard, ephemeral=True)

@bot.tree.command(name="top_leaderboard", description="Use this command to look at the top  leaderboard")
async def send_top_leader(interaction: discord.Interaction):
    if overall_leaderboard == {}:
        await interaction.response.send_message("There is no overall leaderboard to show.", ephemeral=True)
    else:
        await interaction.response.defer(ephemeral=True)
        tuple_sorted_leaderboard = sorted(overall_leaderboard.items(), key= lambda x:x[1], reverse=True)
        sorted_leaderboard = [list(ele) for ele in tuple_sorted_leaderboard] #Convert the tuples in the list to lists



        #Group people with the same score together
        sorted_leaderboard = await Sort(sorted_leaderboard)
        sorted_leaderboard.reverse()
        print(len(sorted_leaderboard))
        i = len(sorted_leaderboard) - 1  # Start from the last index
        while i >= 1:
            if int(sorted_leaderboard[i][1]) == int(sorted_leaderboard[i-1][1]):
                sorted_leaderboard[i-1] += sorted_leaderboard[i]  # Merge the two elements
                sorted_leaderboard.pop(i)  # Remove the second element
            i -= 1  # Move to the previous index

        print(sorted_leaderboard)


        position = 0
        if str(interaction.user.id) in overall_leaderboard:
            for place in sorted_leaderboard:
                if str(interaction.user.id) in place:
                    position = sorted_leaderboard.index(place) + 1
        else: 
            pass
        
        if len(sorted_leaderboard) >= 3:
            await interaction.followup.send(f"First: {await calcoverplace(sorted_leaderboard[0])} \nSecond: {await calcoverplace(sorted_leaderboard[1])} \nThird: {await calcoverplace(sorted_leaderboard[2])}\n Your place is {position} with {overall_leaderboard.get(str(interaction.user.id))} point(s)", ephemeral=True)
        elif len(sorted_leaderboard) == 2:
            await interaction.followup.send(f"First: {await calcoverplace(sorted_leaderboard[0])} \nSecond: {await calcoverplace(sorted_leaderboard[1])} \nThird: No one\n Your place is {position} with {overall_leaderboard.get(str(interaction.user.id))} point(s)", ephemeral=True)
        elif len(sorted_leaderboard) == 1:
            await interaction.followup.send(f"First: {await calcoverplace(sorted_leaderboard[0])} \nSecond: No one \nThird: No one\n Your place is {position} with {overall_leaderboard.get(str(interaction.user.id))} point(s)", ephemeral=True)
        else:
            await interaction.followup.send(f"First: No one \nSecond: No one \nThird: No one\n Your place is {position} with {overall_leaderboard.get(str(interaction.user.id))} point(s)", ephemeral=True)
            
async def calcoverplace(list1):
    second = ""
    try:
        if len(list1) == 2: #If only one user in position
            second = f"<@{list1[0]}> - {list1[1]} point(s)"        
        else:
            for i in range(1, int(len(list1)/2)+1): #If multiple users are in position
                chunk = "<@"+str(list1[(i*2)-2]) +"> - "+ str(list1[(i*2)-1]) +" points(s)"

                if i == int(len(list1))/2:
                    second = second + chunk
                else:
                    second = second + chunk + " and "
        return second
    except:
        return second
        



#--------------------------------------#







#------Test stuff------#
async def test():
    await bot.wait_until_ready()
    c = bot.get_channel(CHANNEL_ID)
    await c.send('test')

#-------------------------------------#


#------Kinda useless reaction stuff--------#


# listen for any reactions added to messages
@bot.event
async def on_raw_reaction_add(payload):
    message = await bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
    reaction = discord.utils.get(message.reactions)
    user=payload.member

    print(f"Message {message.content} was reacted with {reaction} by {user}")




# listen for any reactions removed from messages
@bot.event
async def on_raw_reaction_remove(payload):
    message = await bot.get_channel(payload.channel_id).fetch_message(payload.message_id) 
    reaction = discord.utils.get(message.reactions)
    user = discord.utils.get(message.guild.members, id=payload.user_id)

    print(f"Reaction {reaction} was removed from {message.content} by {user}")


#--------------------------------------------#





#------IRRELEVANT COMMANDS-------#

@bot.tree.command(name="hello")
async def first_command(interaction: discord.Interaction):
    button1 = Button(label="Click me!", style=discord.ButtonStyle.blurple, emoji="⬆️")

    async def button_callback(interaction):
        await interaction.response.send_message("Hi!", ephemeral=True)
        await interaction.followup.send("Hello!", ephemeral=True)

    button1.callback = button_callback

    view = View()
    view.add_item(button1)

    await interaction.response.send_message("Hello!",view=view)

@bot.command()
async def purge(ctx, amt):
    await ctx.channel.purge(limit = int(amt) + 1)
    msg = await ctx.send(f"Purged {amt} messages.")
    await asyncio.sleep(3)
    await msg.delete()

bot.run(BOTTOKEN)
