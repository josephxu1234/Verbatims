#!/usr/bin/env python

#-----------------------------------------------------------------------
# db.py
# Author: Bryan Wang, Joanna Tang, Joseph Xu
#-----------------------------------------------------------------------

from contextlib import closing
import psycopg2
import random
import string
from datetime import datetime
from config import connection_settings
import cloudinary
import cloudinary.uploader
import cloudinary.api

# not the actual INT MAX, but capping it here
# in order to ensure that there exists a bijection between group codes/channels
# subtract 1 because ids range from 0 to INT_MAX
INT_MAX = 1572120576 - 1
cloudinary.config( 
  cloud_name = "verbatims", 
  api_key = "975697993375456", 
  api_secret = "beoLMSwc2TnnMXCINX5NWptLjFY" 
)

# initialize tables of the database
def init_tables():
    try:
        with psycopg2.connect(**connection_settings) as con:
            with closing(con.cursor()) as cursor:
                #create messages table
                # the unique combination of channelid and messageid
                # should be able to display any unique message

                # userid: id of the author
                # speakerid: the person who is being verbatim-ed
                create_messages_stmt = """CREATE TABLE IF NOT EXISTS messages(
                    channelid INT,
                    messageid INT,
                    userid INT,
                    content TEXT,
                    timestamp TIMESTAMPTZ,
                    speakerid INT,
                    PRIMARY KEY (channelid, messageid)
                );"""

                # show which channels each user is associated with
                # each membership comes with its own set of statistics

                #numrightid: the number of times that userid was correctly identified in a certain channel
                #numtotalid: the number of times that people tried to guess a quote by userid
                #ex: bryan has 2 messages. out of 20 ppl to guess on message 1, 15 got it right
                # out of 30 ppl to guess message 2, 25 got it right
                # his identifiability percentage = (15 + 25) / (20 + 25)

                # numrightguess = number of guesses that userid has gotten right
                # numtotalguess = number of guesses that userid has submitted in total
                create_membership_stmt = """CREATE TABLE IF NOT EXISTS membership(
                    channelid INT,
                    userid INT,
                    numrightid INT,
                    numtotalid INT,
                    numrightguess INT,
                    numtotalguess INT,
                    moderator BOOLEAN,
                    PRIMARY KEY (channelid, userid)
                );"""

                # max lengths based on recommendations found on google
                # numright, numtotal track statistics overa all time
                create_users_stmt = """CREATE TABLE IF NOT EXISTS users(
                    userid INT,
                    firstname VARCHAR(50),
                    lastname VARCHAR(50),
                    username VARCHAR(30),
                    bio VARCHAR(140),
                    numrightid INT,
                    numtotalid INT,
                    numrightguess INT,
                    numtotalguess INT,
                    pfpid TEXT,
                    pfpurl TEXT,
                    PRIMARY KEY (userid)
                );"""

                create_channelprops_stmt = """CREATE TABLE IF NOT EXISTS channelprops(
                    channelid INT,
                    channelname VARCHAR(50),
                    mostlikedverbatim TEXT,
                    pfpid TEXT,
                    pfpurl TEXT,
                    groupcode CHAR(6),
                    PRIMARY KEY (channelid)
                );"""

                create_guesses_stmt = """CREATE TABLE IF NOT EXISTS guesses(
                    channelid INT,
                    messageid INT,
                    guesserid INT,
                    speakerid INT,
                    correct BOOLEAN,
                    PRIMARY KEY (channelid, messageid, guesserid)
                );"""

                cursor.execute(create_messages_stmt)
                cursor.execute(create_membership_stmt)
                cursor.execute(create_users_stmt)
                cursor.execute(create_channelprops_stmt)
                cursor.execute(create_guesses_stmt)

                print("Initialized tables")
    except Exception as ex:
        print(ex)

#stmt: the SQL statement as a string
#value_arr: [value1, value2, value3, ...]
#intended to simplify execution of statements that don't require
#return values (e.g. SELECT statements)
def execute_stmt(stmt, value_arr):
    try:
        with psycopg2.connect(**connection_settings) as con:
            with closing(con.cursor()) as cursor:
                cursor.execute(stmt, value_arr)
    except Exception as ex:
        print(ex)
        return False
    return True

# default behavior: generate 6 char code, alphanumeric (uppercase + #'s 0-9)
# all groupcodes start with a letter
def generate_groupcode_helper(size=6, chars=string.ascii_uppercase + string.digits):
    return random.choice(string.ascii_uppercase) + ''.join(random.choice(chars) for _ in range(size - 1))

# create new, randomized, unique channel groupcode
def generate_groupcode():
    groupcode = generate_groupcode_helper()
    test_existence_stmt = """SELECT COUNT(1) FROM channelprops WHERE groupcode=%s""" 
    already_exists = True

    while(already_exists):
        try:
            with psycopg2.connect(**connection_settings) as con:
                with closing(con.cursor()) as cursor:
                    cursor.execute(test_existence_stmt, [groupcode])
                    row = cursor.fetchone()
                    if int(row[0]) == 0:
                        already_exists = False
                    else:
                        groupcode = generate_groupcode_helper()
        except Exception as ex:
            print(ex)
    return groupcode

# generates a unique message id in the channel
# helper function, called every time someone wants to send a message
def generate_messageid(channelid):
    messageid = random.randint(0, INT_MAX)
    test_existence_stmt = """SELECT COUNT(1) FROM messages WHERE messageid=%s AND channelid=%s""" 
    already_exists = True

    while(already_exists):
        try:
            with psycopg2.connect(**connection_settings) as con:
                with closing(con.cursor()) as cursor:
                    cursor.execute(test_existence_stmt, [messageid, channelid])
                    row = cursor.fetchone()
                    # test_existence_statement returns 0 if the messageid was not found
                    if int(row[0]) == 0:
                        already_exists = False
                    # if the messageid already exists, regenerate a messageid
                    else:
                        messageid = random.randint(0, INT_MAX)
        except Exception as ex:
            print(ex)
    return messageid

# generates a unique userid
# helper function, used every time you want to create a new user
def generate_userid():
    userid = random.randint(0, INT_MAX)
    test_existence_stmt = """SELECT COUNT(1) FROM users WHERE userid=%s"""
    already_exists = True

    while(already_exists):
        try:
            with psycopg2.connect(**connection_settings) as con:
                with closing(con.cursor()) as cursor:
                    cursor.execute(test_existence_stmt, [userid])
                    row = cursor.fetchone()
                    # test_existence_statement returns 0 if the userid was not found
                    if int(row[0]) == 0:
                        already_exists = False
                    # if the userid already exists, regenerate a userid
                    else:
                        userid = random.randint(0, INT_MAX)
        except Exception as ex:
            print(ex)
    return userid

# generates a unique channelid
# helper function, used every time you want to create a new user
def generate_channelid():
    channel_id = random.randint(0, INT_MAX)
    test_existence_stmt = """SELECT COUNT(1) FROM channelprops WHERE channelid=%s"""
    already_exists = True

    while(already_exists):
        try:
            with psycopg2.connect(**connection_settings) as con:
                with closing(con.cursor()) as cursor:
                    cursor.execute(test_existence_stmt, [channel_id])
                    row = cursor.fetchone()
                    # test_existence_statement returns 0 if the channelid was not found
                    if int(row[0]) == 0:
                        already_exists = False
                    # if the channelid already exists, regenerate a channelid
                    else:
                        channel_id = random.randint(0, INT_MAX)
        except Exception as ex:
            print(ex)
    return channel_id

# create a new channel
# default: empty string for mostlikedverbatim, pfpid, pfpurl
def create_channel(channelname):
    channelid = generate_channelid()
    create_user_stmt = """INSERT INTO channelprops
                        VALUES(%s, %s, %s, %s, %s, %s)"""

    execute_stmt(create_user_stmt, [channelid, channelname, "", "", "", generate_groupcode()])
    return channelid

# add a new user to user users table
# use unique userids in case people want to change usernames
# by default: aggregate user statistics = 0, pfpid = pfpurl = ""
def create_user(firstname, lastname, username, bio):
    userid = generate_userid()
    create_user_stmt = """INSERT INTO users 
                        VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
    execute_stmt(create_user_stmt, [userid, firstname, lastname, username, bio, 0, 0, 0, 0, "", ""])
    return userid

# return the channelid associated with a certain groupcode
def get_channelid_from_groupcode(groupcode):
    get_messages_stmt = """SELECT channelid FROM channelprops WHERE groupcode=%s"""
    try:
        with psycopg2.connect(**connection_settings) as con:
            with closing(con.cursor()) as cursor:
                cursor.execute(get_messages_stmt, [groupcode])
                row = cursor.fetchone()
                response = row[0]
    except Exception as ex:
        print(ex)
        return ex
    return response

# return whether there exists a channel with a certain groupcode
def isValid(groupcode):
    get_messages_stmt = """SELECT channelid FROM channelprops WHERE groupcode=%s"""
    try:
        with psycopg2.connect(**connection_settings) as con:
            with closing(con.cursor()) as cursor:
                cursor.execute(get_messages_stmt, [groupcode])
                row = cursor.fetchone()
                if (row is None):
                    return False
    except Exception as ex:
        print(ex)
        return ex
    return True

# add a user to a channel
# add user to channel supports both adding based on channelid or groupcode
# Return True upon success, an Exception with an error msg otherwise
def add_user_to_channel(id, userid):
    channelid = -1
    try:
        channelid = int(id)
    except ValueError:
        channelid = get_channelid_from_groupcode(id)
    if channelid == -1:
        return Exception("Unable to add user to channel")

    #check if already in channel
    check_stmt = """SELECT userid FROM membership WHERE channelid=%s AND userid=%s"""
    try:
        with psycopg2.connect(**connection_settings) as con:
            with closing(con.cursor()) as cursor:
                cursor.execute(check_stmt, [channelid, userid])
                row = cursor.fetchone()
                if row is not None:
                    return Exception("User already exists in channel")
    except Exception as ex:
        print(ex)
        return 

    #if empty channel, make moderator
    moderator = False
    checktwo_stmt = """SELECT userid FROM membership WHERE channelid=%s"""
    try:
        with psycopg2.connect(**connection_settings) as con:
            with closing(con.cursor()) as cursor:
                cursor.execute(checktwo_stmt, [channelid])
                row = cursor.fetchone()
                if row is None:
                    moderator = True
    except Exception as ex:
        print(ex)
        return 

    add_user_to_channel_stmt = """INSERT INTO membership
                                VALUES(%s, %s, %s, %s, %s, %s, %s)"""

    # ensure that the channel actually exists
    if isinstance(get_channelname(channelid), Exception):
        return Exception('Channel with id %d does not exist' % channelid)
    
    execute_stmt(add_user_to_channel_stmt, [channelid, userid, 0, 0, 0, 0, moderator])
    return True

def make_moderator(channelid, userid):
    make_moderator_stmt = """UPDATE membership SET moderator=%s WHERE channelid=%s AND userid=%s"""
    execute_stmt(make_moderator_stmt, [True, channelid, userid])

# send a new message to a channel
def send_message(channelid, userid, content, speakerid=-1):
    messageid = generate_messageid(channelid)
    create_message_stmt = """INSERT INTO messages
                            VALUES(%s, %s, %s, %s, %s, %s)"""

    update_mostlikedverbatim_stmt = "UPDATE channelprops SET mostlikedverbatim=%s WHERE channelid=%s"
    try:
        with psycopg2.connect(**connection_settings) as con:
            with closing(con.cursor()) as cursor:
                cursor.execute(create_message_stmt, [channelid, messageid, userid, content, datetime.now(), speakerid])
                cursor.execute(update_mostlikedverbatim_stmt, [content, channelid])
    except Exception as ex:
        print(ex)

# get all messages from a certain channel, sorted by timestamp
def get_messages(channelid):
    get_messages_stmt = """SELECT * FROM messages WHERE channelid=%s ORDER BY timestamp ASC"""
    try:
        with psycopg2.connect(**connection_settings) as con:
            with closing(con.cursor()) as cursor:
                cursor.execute(get_messages_stmt, [channelid])
                row = cursor.fetchone()
                response = []
                while row is not None:
                    response.append(row)
                    row = cursor.fetchone()
    except Exception as ex:
        print(ex)
    return response

# get list of channels that a user is part of
# PRIVATE. do not use this for flask/clientside
# flask/clientside should instead be using get_userchannels
def get_channels(userid):
    get_channels_stmt = """SELECT channelid FROM membership WHERE userid=%s"""
    try:
        with psycopg2.connect(**connection_settings) as con:
            with closing(con.cursor()) as cursor:
                cursor.execute(get_channels_stmt, [userid])
                row = cursor.fetchone()
                response = []
                while row is not None and not isinstance(row[0], Exception):
                    # row = (channelid, userid)
                    response.append(row[0])
                    row = cursor.fetchone()
    except Exception as ex:
        print(ex)
    return response

# get a dictionary of userids of users that are in a certain channel
def get_users(channelid):
    get_users_stmt = """SELECT userid, moderator FROM membership WHERE channelid=%s"""
    try:
        with psycopg2.connect(**connection_settings) as con:
            with closing(con.cursor()) as cursor:
                cursor.execute(get_users_stmt, [channelid])
                row = cursor.fetchone()
                response = {}
                while row is not None:
                    response[row[0]] = row[1]
                    row = cursor.fetchone()
    except Exception as ex:
        print(ex)
    return response


#get userid from username
def get_userid(username):
    get_userid_stmt = """SELECT userid FROM users WHERE username=%s"""
    try:
        with psycopg2.connect(**connection_settings) as con:
            with closing(con.cursor()) as cursor:
                cursor.execute(get_userid_stmt, [username])
                row = cursor.fetchone()
                #row[0] has userid
                response = row[0]
    except Exception as ex:
        print(ex)
    return response

# check if a userid exists in a database
def userid_exists(username):
    test_existence_stmt = """SELECT COUNT(1) FROM users WHERE username=%s"""
    try:
        with psycopg2.connect(**connection_settings) as con:
            with closing(con.cursor()) as cursor:
                cursor.execute(test_existence_stmt, [username])
                row = cursor.fetchone()
                # test_existence_statement returns 0 if the userid was not found
                return int(row[0]) != 0
    except Exception as ex:
        print(ex)
        return ex

#get channelname from channelid
def get_channelname(channelid):
    get_channelname_stmt = """SELECT channelname FROM channelprops WHERE channelid=%s"""
    try:
        with psycopg2.connect(**connection_settings) as con:
            with closing(con.cursor()) as cursor:
                cursor.execute(get_channelname_stmt, [channelid])
                row = cursor.fetchone()
                response = row[0]
    # row returned None, so there is no entry with the desired channelid
    except TypeError as ex:
        return Exception('Channelid %d does not exist' % channelid)
    except Exception as ex:
        print(ex)
        return ex
    return response

# return the properties associated with each channel as a dictionary
def get_channelprops(channelid):
    get_channelprops_stmt = """SELECT * FROM channelprops WHERE channelid=%s"""
    try:
        with psycopg2.connect(**connection_settings) as con:
            with closing(con.cursor()) as cursor:
                cursor.execute(get_channelprops_stmt, [channelid])
                row = cursor.fetchone()
                response = {}
                while row is not None:
                    response['channelid'] = row[0]
                    response['channelname'] = row[1]
                    response['mostlikedverbatim'] = row[2]
                    response['pfpid'] = row[3]
                    response['pfpurl'] = row[4]
                    response['groupcode'] = row[5]
                    row = cursor.fetchone()
    except Exception as ex:
        print(ex)
    return response

# return members sorted by criteria
def get_sorted_members(channelid, criteria):
    get_sorted_members_stmt = """SELECT userid, %s FROM membership WHERE channelid=%s ORDER BY %s DESC""" % (criteria, channelid, criteria)
    try:
        with psycopg2.connect(**connection_settings) as con:
            with closing(con.cursor()) as cursor:
                cursor.execute(get_sorted_members_stmt, [criteria, channelid])
                row = cursor.fetchone()
                response = []
                while row is not None:
                    # row = (userid, score)
                    response.append((row[0], row[1]))
                    row = cursor.fetchone()
    except Exception as ex:
        print(ex)
    return response

#get username associated with userid
def get_username(userid):
    get_username_stmt = """SELECT firstname, lastname FROM users WHERE userid=%s"""
    try:
        with psycopg2.connect(**connection_settings) as con:
            with closing(con.cursor()) as cursor:
                cursor.execute(get_username_stmt, [userid])
                row = cursor.fetchone()
                response = []
                while row is not None:
                    response.append(row[0] + " " + row[1])
                    row = cursor.fetchone()
    except Exception as ex:
        print(ex)
    return response

#get channelname from channelid
# dictionary where each key is a string literal exactly copied from the schema
def get_userinfo(userid):
    get_userinfo_stmt = """SELECT * FROM users WHERE userid=%s"""
    try:
        with psycopg2.connect(**connection_settings) as con:
            with closing(con.cursor()) as cursor:
                cursor.execute(get_userinfo_stmt, [userid])
                row = cursor.fetchone()
                response = {}
                while row is not None:
                    response['userid'] = row[0]
                    response['firstname'] = row[1]
                    response['lastname'] = row[2]
                    response['username'] = row[3]
                    response['bio'] = row[4]
                    response['numrightid'] = row[5]
                    response['numtotalid'] = row[6]
                    response['numrightguess'] = row[7]
                    response['numtotalguess'] = row[8]
                    response['pfpid'] = row[9]
                    response['pfpurl'] = row[10]
                    row = cursor.fetchone()
    except Exception as ex:
        print(ex)
    return response

# get the names of channels associated with a certain user
# return a list of (channelid, channelname)
def get_userchannels(userid):
    channelids = get_channels(userid)
    response = []
    for channelid in channelids:
        cname = get_channelname(channelid)
        if not isinstance(cname, Exception):
            response.append((channelid, cname))
    return response
    
# return the userid of who is being verbatimed for a certain message
def get_speakerid(channelid, messageid):
    stmt = "SELECT speakerid FROM messages WHERE channelid=%s AND messageid=%s"
    try:
        with psycopg2.connect(**connection_settings) as con:
            with closing(con.cursor()) as cursor:
                cursor.execute(stmt, [channelid, messageid])
                row = cursor.fetchone()
                response = row[0]
    except Exception as ex:
        print(ex)
    return response

#submits a guess by updating the guesses, users, and membership tables
# guesserid: the userid of the guesser
# speakerid: the userid of the person that the guesser thinks said the verbatim
def submitguess(channelid, messageid, guesserid, speakerid):
    submitguess_stmt = """INSERT into guesses VALUES(%s, %s, %s, %s, %s)"""
    actual_speakerid = int(get_speakerid(channelid, messageid))
    correct = (actual_speakerid == speakerid)

    guess_arr = [channelid, messageid, guesserid, speakerid, correct]
    execute_stmt(submitguess_stmt, guess_arr)

    # update the user statistics by channel
    update_numtotalid_stmt = "UPDATE membership SET numtotalid=numtotalid+1 WHERE userid=%s AND channelid=%s"
    execute_stmt(update_numtotalid_stmt, [actual_speakerid, channelid])
    update_numtotalguess_stmt = "UPDATE membership SET numtotalguess=numtotalguess+1 WHERE userid=%s AND channelid=%s"
    execute_stmt(update_numtotalguess_stmt, [guesserid, channelid])

    # update the user stats aggregate
    update_numtotalid_users_stmt = "UPDATE users SET numtotalid=numtotalid+1 WHERE userid=%s"
    execute_stmt(update_numtotalid_users_stmt, [actual_speakerid])

    update_numtotalguess_users_stmt = "UPDATE users SET numtotalguess=numtotalguess+1 WHERE userid=%s"
    execute_stmt(update_numtotalguess_users_stmt, [guesserid])
    

    if correct:
        update_numrightid_stmt = "UPDATE membership SET numrightid=numrightid+1 WHERE userid=%s AND channelid=%s"
        execute_stmt(update_numrightid_stmt, [speakerid, channelid])

        update_numrightguess_stmt = "UPDATE membership set numrightguess=numrightguess+1 WHERE userid=%s AND channelid=%s"
        execute_stmt(update_numrightguess_stmt, [guesserid, channelid])
        
        # update the user statistics
        update_numrightid_users_stmt = "UPDATE users set numrightid=numrightid+1 WHERE userid=%s"
        execute_stmt(update_numrightid_users_stmt, [speakerid])

        update_numrightguess_users_stmt = "UPDATE users set numrightguess=numrightguess+1 WHERE userid=%s"
        execute_stmt(update_numrightguess_users_stmt, [guesserid])        
    return correct

# returns True if the user associated with userid has submitted a guess on the verbatim identified by (channelid, messageid)
def has_guessed(userid, channelid, messageid):
    test_existence_stmt = """SELECT COUNT(1) FROM guesses WHERE guesserid=%s AND channelid=%s and messageid=%s"""

    try:
        with psycopg2.connect(**connection_settings) as con:
            with closing(con.cursor()) as cursor:
                cursor.execute(test_existence_stmt, [userid, channelid, messageid])
                row = cursor.fetchone()
                return int(row[0]) != 0
    except Exception as ex:
        print(ex)
        return ex

#get percent of correct guesses by channel
def get_gratio_by_channel(userid, channelid):
    stmt = "SELECT numrightguess, numtotalguess FROM membership WHERE userid=%s AND channelid=%s"
    try:
        with psycopg2.connect(**connection_settings) as con:
            with closing(con.cursor()) as cursor:
                cursor.execute(stmt, [userid, channelid])
                row = cursor.fetchone()
                if row[1] != 0:
                    response = row[0]/row[1]
                else: # numtotalguess=0
                    response = 0
    except Exception as ex:
        print(ex)
    return response

# get percent of correct guesses across all channels
def get_gratio_aggregate(userid):
    stmt = "SELECT numrightguess, numtotalguess FROM users WHERE userid=%s"
    try:
        with psycopg2.connect(**connection_settings) as con:
            with closing(con.cursor()) as cursor:
                cursor.execute(stmt, [userid])
                row = cursor.fetchone()
                if row[1] != 0:
                    response = row[0]/row[1]
                else: # numtotalguess=0
                    response = 0
    except Exception as ex:
        print(ex)
    return response

# get how identifiable a user is in a certain channel
def get_idratio_by_channel(userid, channelid):
    stmt = "SELECT numrightid, numtotalid FROM membership WHERE userid=%s AND channelid=%s"
    try:
        with psycopg2.connect(**connection_settings) as con:
            with closing(con.cursor()) as cursor:
                cursor.execute(stmt, [userid, channelid])
                row = cursor.fetchone()
                if row[1] != 0:
                    response = row[0]/row[1]
                else: # numtotalguess=0
                    response = 0
    except Exception as ex:
        print(ex)
    return response

# return how identifiable a user is across all of their channels
def get_idratio_aggregate(userid):
    stmt = "SELECT numrightid, numtotalid FROM users WHERE userid=%s"
    try:
        with psycopg2.connect(**connection_settings) as con:
            with closing(con.cursor()) as cursor:
                cursor.execute(stmt, [userid])
                row = cursor.fetchone()
                if row[1] != 0:
                    response = row[0]/row[1]
                else: # numtotalguess=0
                    response = 0
    except Exception as ex:
        print(ex)
    return response

# return a list of (firstname, lastname) of the users who guessed 
# correctly on channelid, messageid
def get_correct_guessers(channelid, messageid):
    stmt = "SELECT guesserid FROM guesses where channelid=%s AND messageid=%s AND correct=%s"
    try:
        with psycopg2.connect(**connection_settings) as con:
            with closing(con.cursor()) as cursor:
                cursor.execute(stmt, [channelid, messageid, True])
                row = cursor.fetchone() #row = guesserid
                response = []
                while row is not None:
                    userinfo = get_userinfo(row[0])
                    response.append((userinfo['firstname'], userinfo['lastname']))
                    row = cursor.fetchone()
    except Exception as ex:
        print(ex)
    return response

# return a list of (firstname, lastname) of the users who guessed 
# on channelid, messageid, REGARDLESS of correctness
def get_guessers(channelid, messageid):
    stmt = "SELECT guesserid FROM guesses where channelid=%s AND messageid=%s"
    try:
        with psycopg2.connect(**connection_settings) as con:
            with closing(con.cursor()) as cursor:
                cursor.execute(stmt, [channelid, messageid])
                row = cursor.fetchone() #row = guesserid
                response = []
                while row is not None:
                    userinfo = get_userinfo(row[0])
                    response.append((userinfo['firstname'], userinfo['lastname']))
                    row = cursor.fetchone()
    except Exception as ex:
        print(ex)
    return response

# upload pfp to cloudinary, save changes in db by modifying channelprops
# ex: pfp can be a url to an image, or a file object 
def upload_channel_pfp(channelid, pfp):
    response = cloudinary.uploader.upload(pfp)
    pfpid = response['public_id']
    pfpurl = response['secure_url']

    stmt = "UPDATE channelprops SET pfpid=%s, pfpurl=%s WHERE channelid=%s"
    execute_stmt(stmt, [pfpid, pfpurl, channelid])
    return pfpurl

# upload pfp to cloudinary, update db by changing users table
def upload_user_pfp(userid, pfp):
    response = cloudinary.uploader.upload(pfp)
    pfpid = response['public_id']
    pfpurl = response['secure_url']

    stmt = "UPDATE users SET pfpid=%s, pfpurl=%s WHERE userid=%s"
    execute_stmt(stmt, [pfpid, pfpurl, userid])
    return pfpurl

# return url of the user's pfp
def get_user_pfp(userid):
    stmt = "SELECT pfpurl FROM users WHERE userid=%s"
    try:
        with psycopg2.connect(**connection_settings) as con:
            with closing(con.cursor()) as cursor:
                cursor.execute(stmt, [userid])
                response = cursor.fetchone()[0]
    except Exception as ex:
        print(ex)
    return response

# return url of the channel's pfp
def get_channel_pfp(channelid):
    stmt = "SELECT pfpurl FROM channelprops WHERE channelid=%s"
    try:
        with psycopg2.connect(**connection_settings) as con:
            with closing(con.cursor()) as cursor:
                cursor.execute(stmt, [channelid])
                response = cursor.fetchone()[0]
    except Exception as ex:
        print(ex)
        # default pfp
        return 'https://media.mixbook.com/images/templates/97_1_0_m.jpg'
    return response

# update the channel profile picture
def update_channel_pfp(channelid, pfpid, pfpurl):
   stmt = "UPDATE channelprops SET pfpid=%s, pfpurl=%s WHERE channelid=%s"
   execute_stmt(stmt, [pfpid, pfpurl, channelid])
   return pfpurl
 
# update the user profile picture
def update_user_pfp(userid, pfpid, pfpurl):
   stmt = "UPDATE users SET pfpid=%s, pfpurl=%s WHERE userid=%s"
   execute_stmt(stmt, [pfpid, pfpurl, userid])
   return pfpurl

# update the properties associated with a certain user
def update_user(firstname, lastname, userid, bio):
    update_user_stmt = """UPDATE users SET firstname=%s, lastname=%s, bio = %s WHERE userid=%s"""
    execute_stmt(update_user_stmt, [firstname, lastname, bio, userid])

# delete a message, update statistics accordingly
def delete_message(channelid, messageid):
    stmt = "DELETE FROM messages WHERE channelid=%s AND messageid=%s"
    execute_stmt(stmt, [channelid, messageid])
    # get all guesserids from guesses

    stmt = "SELECT guesserid, speakerid, correct FROM guesses where channelid=%s AND messageid=%s"
    response = []
    try:
        with psycopg2.connect(**connection_settings) as con:
            with closing(con.cursor()) as cursor:
                cursor.execute(stmt, [channelid, messageid])
                row = cursor.fetchone() #row = guesserid
                
                while row is not None:
                    response.append((row[0], row[1], row[2]))
                    row = cursor.fetchone()
    except Exception as ex:
        print(ex)
    # for each, get the gid, sid, and correct
    for row in response:
        speakerid = row[1]
        guesserid = row[0]
        correct = row[2]
        # update the user statistics by channel
        update_numtotalid_stmt = "UPDATE membership SET numtotalid=numtotalid-1 WHERE userid=%s AND channelid=%s"
        execute_stmt(update_numtotalid_stmt, [speakerid, channelid])
        update_numtotalguess_stmt = "UPDATE membership SET numtotalguess=numtotalguess-1 WHERE userid=%s AND channelid=%s"
        execute_stmt(update_numtotalguess_stmt, [guesserid, channelid])

        # update the user stats aggregate
        update_numtotalid_users_stmt = "UPDATE users SET numtotalid=numtotalid-1 WHERE userid=%s"
        execute_stmt(update_numtotalid_users_stmt, [speakerid])

        update_numtotalguess_users_stmt = "UPDATE users SET numtotalguess=numtotalguess-1 WHERE userid=%s"
        execute_stmt(update_numtotalguess_users_stmt, [guesserid])
        

        if correct:
            update_numrightid_stmt = "UPDATE membership SET numrightid=numrightid-1 WHERE userid=%s AND channelid=%s"
            execute_stmt(update_numrightid_stmt, [speakerid, channelid])

            update_numrightguess_stmt = "UPDATE membership set numrightguess=numrightguess-1 WHERE userid=%s AND channelid=%s"
            execute_stmt(update_numrightguess_stmt, [guesserid, channelid])
            
            # update the user statistics
            update_numrightid_users_stmt = "UPDATE users set numrightid=numrightid-1 WHERE userid=%s"
            execute_stmt(update_numrightid_users_stmt, [speakerid])

            update_numrightguess_users_stmt = "UPDATE users set numrightguess=numrightguess-1 WHERE userid=%s"
            execute_stmt(update_numrightguess_users_stmt, [guesserid]) 

# clean out a channel by deleting all of the messages
# and removing the channel from channelprops
# and removing all users as members of the channel
def delete_channel(channelid):
    # get all messageids from channelid
    message_info = get_messages(channelid)
    message_ids = [a_tuple[1] for a_tuple in message_info]

    #clean messages (this implicity handles guesses) MAY NEED TO IMPROVE O(n^2) time

    for messageid in message_ids:
        delete_message(channelid, messageid)

    #clean membership
    stmt = "DELETE FROM membership WHERE channelid=%s"
    execute_stmt(stmt, [channelid])

    #clean channelprops
    stmt = "DELETE FROM channelprops WHERE channelid=%s"
    execute_stmt(stmt, [channelid])

# removes user from channel:
# POSTCONDITION: user's guesses and messages still exist 
def leave_channel(channelid, userid):
    # delete from membership

    #clean membership
    stmt = "DELETE FROM membership WHERE channelid=%s AND userid = %s"
    execute_stmt(stmt, [channelid, userid])

    

# return True/False depending on whether the user is a moderator in the given channel
def is_moderator(channelid, userid):
    is_moderator_stmt = """SELECT moderator FROM membership WHERE channelid=%s AND userid=%s"""
    try:
        with psycopg2.connect(**connection_settings) as con:
            with closing(con.cursor()) as cursor:
                cursor.execute(is_moderator_stmt, [channelid, userid])
                row = cursor.fetchone()
                response = row[0]
    except Exception as ex:
        print(ex)
    return response

# return all messages said by a certain user
def get_messages_by_speaker(channelid, speakerid):
    stmt = """SELECT * FROM messages WHERE channelid=%s AND speakerid=%s ORDER BY timestamp ASC"""
    try:
        with psycopg2.connect(**connection_settings) as con:
            with closing(con.cursor()) as cursor:
                cursor.execute(stmt, [channelid, speakerid])
                row = cursor.fetchone()
                response = []
                while row is not None:
                    response.append(row)
                    row = cursor.fetchone()
    except Exception as ex:
        print(ex)
    return response

# get all messages that contain certain text (content)
def get_messages_by_content(channelid, content):
    stmt = """SELECT * FROM messages WHERE channelid=%s ORDER BY timestamp ASC"""
    try:
        with psycopg2.connect(**connection_settings) as con:
            with closing(con.cursor()) as cursor:
                cursor.execute(stmt, [channelid])
                row = cursor.fetchone()
                response = []
                while row is not None:
                    if content.lower() in row[3].lower():
                        response.append(row)
                    row = cursor.fetchone()
    except Exception as ex:
        print(ex)
    return response

def main():
    joanna_id = create_user("joanna", "tang", "jztang", "im awesome")
    bryan_id = create_user("bryan", "wang", "bw22", "im cool")
    joseph_id = create_user("joseph", "xu", "jx6", "im amazing")
    ethan_id = create_user("ethan", "sample", "esample", "im great")
    riri_id = create_user("riri", "jiang", "ryj", "im riri")
    angel_id = create_user("angel", "kuo", "angelkuo", "im an angel")
    candace_id = create_user("candace", "do", "cdo", "im smort")
    zoe_id = create_user("zoe", "montague", "zoemontague", "im artistic")
    michelle_id = create_user("michelle", "huang", "mh52", "im talented")
    edward_id = create_user("edward", "zhang", "edwardzhang", "im musical")
    andrew_id = create_user("andrew", "mi", "andrewmi", "im lyrical")

    little_id = create_channel("little") #little hall
    cos333_id = create_channel("cos333") #COS 333
    orf309_id = create_channel("orf309") #ORF 309
    ppe_id = create_channel("ppe") #piano ensemble

    cos333_groupcode = get_channelprops(cos333_id)['groupcode']


    # little hall verbatims
    print(add_user_to_channel(little_id, bryan_id))
    add_user_to_channel(little_id, joseph_id)
    add_user_to_channel(little_id, ethan_id)
    add_user_to_channel(little_id, riri_id)
    add_user_to_channel(little_id, candace_id)
    add_user_to_channel(little_id, angel_id)
    add_user_to_channel(little_id, zoe_id)
    print(add_user_to_channel(111, bryan_id)) # Channel with id 111 does not exist

    # COS333 verbatims
    add_user_to_channel(cos333_groupcode, bryan_id)
    add_user_to_channel(cos333_groupcode, joseph_id)
    add_user_to_channel(cos333_groupcode, joanna_id)

    # ORF309 verbatims
    add_user_to_channel(orf309_id, joseph_id)
    add_user_to_channel(orf309_id, joanna_id)
    add_user_to_channel(orf309_id, ethan_id)
    add_user_to_channel(orf309_id, riri_id)

    # PPE verbatims
    add_user_to_channel(ppe_id, joseph_id)
    add_user_to_channel(ppe_id, michelle_id)
    add_user_to_channel(ppe_id, edward_id)
    add_user_to_channel(ppe_id, andrew_id)

    # messages in little hall verbatims
    send_message(little_id, joseph_id, "Can I be a Canadian wife's trophy man? @riri", speakerid=riri_id)
    send_message(little_id, riri_id, "When are you going to triple 8? @zoe triple 8? oh i thought you said chipotle @ethan", speakerid=ethan_id)
    send_message(little_id, angel_id, "this is my sensory deprivation chamber @candace", speakerid=candace_id)
    send_message(little_id, angel_id, "we can all read minds, just our own @joseph", speakerid=joseph_id)
    send_message(little_id, candace_id, "when i went to the dmv to take my driver's test for the first time, it caught on fire @joseph", speakerid=joseph_id)
    send_message(little_id, bryan_id, "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. @riri", speakerid=riri_id)
    send_message(little_id, ethan_id, "Ultrices in iaculis nunc sed augue lacus viverra vitae congue. @riri", speakerid=riri_id)
    send_message(little_id, zoe_id, "Volutpat commodo sed egestas egestas fringilla phasellus faucibus. @riri", speakerid=riri_id)


    # messages in cos 333 verbatims
    send_message(cos333_id, joseph_id, "we gotta make it CASCADING @bryan", speakerid=bryan_id)
    send_message(cos333_id, joanna_id, "we should make a water delivery app @bryan", speakerid=bryan_id)
    send_message(cos333_id, bryan_id, "Aliquet eget sit amet tellus cras. @joanna", speakerid=joanna_id)
    send_message(cos333_id, joseph_id, "Massa sapien faucibus et molestie ac feugiat sed lectus vestibulum. @joanna", speakerid=joanna_id)
    send_message(cos333_id, joanna_id, "Elit ullamcorper dignissim cras tincidunt. Netus et malesuada fames ac turpis. Amet purus gravida quis blandit turpis. @joanna", speakerid=joanna_id)
    send_message(cos333_id, bryan_id, "Nibh venenatis cras sed felis eget. @joanna", speakerid=joanna_id)

    # messages in orf 309 verbatims
    send_message(orf309_id, joseph_id, "claire is the goat @ethan", speakerid=ethan_id)
    send_message(orf309_id, ethan_id, "suppose that you are a student who is wandering drunk from an eating club and you a random walk and you can either get to the fruity yogurt store or your dorm @ramon")
    send_message(orf309_id, joanna_id, "Orci ac auctor augue mauris augue neque. Proin sagittis nisl rhoncus mattis rhoncus urna. @joseph", speakerid=joseph_id)
    send_message(orf309_id, joanna_id, "Proin libero nunc consequat interdum varius sit amet. @joseph", speakerid=joseph_id)
    send_message(orf309_id, joanna_id, "Id venenatis a condimentum vitae. Mattis molestie a iaculis at erat pellentesque adipiscing. @joseph", speakerid=joseph_id)
    
    # messages in ppe verbatims
    send_message(ppe_id, joseph_id, "hot take y'all beethoven is mid @andrew", speakerid=andrew_id)
    send_message(ppe_id, michelle_id, "Nibh tortor id aliquet lectus proin nibh nisl condimentum. Aliquam etiam erat velit scelerisque in. In hac habitasse platea dictumst. @joseph", speakerid=joseph_id)
    send_message(ppe_id, edward_id, "Blandit cursus risus at ultrices mi tempus imperdiet. @joseph", speakerid=joseph_id)
    send_message(ppe_id, andrew_id, "Magnis dis parturient montes nascetur ridiculus mus mauris vitae. Diam quis enim lobortis scelerisque. @joseph", speakerid=joseph_id)
    send_message(ppe_id, andrew_id, "Tincidunt arcu non sodales neque sodales ut etiam sit amet. Nisi vitae suscipit tellus mauris a diam. Vel pharetra vel turpis nunc eget lorem dolor. @joseph", speakerid=joseph_id)



    print(get_messages(little_id))
    print("-"*30)
    print(get_messages(cos333_id))
    print("-"*30)
    print(get_messages(orf309_id))
    print("-"*30)
    print(get_messages(ppe_id))

    little_user_ids = get_users(little_id)
    cos333_user_ids = get_users(cos333_id)
    orf309_user_ids = get_users(orf309_id)
    ppe_user_ids = get_users(ppe_id)
    
    print("-"*10 + "user ids per group" + "-"*10)
    print("little: " + str(little_user_ids))
    print("cos333: " + str(cos333_user_ids))
    print("orf309: "+ str(orf309_user_ids))
    print("ppe: " + str(ppe_user_ids))

    print("-"*10 + "bryan's channels" + "-"*10)
    # names of the channels that bryan is in
    print(get_userchannels(bryan_id))

    print("-"*10 + "get channelprops info" + "-"*10)
    print(get_channelprops(little_id))
    print(get_channelprops(cos333_id))
    print(get_channelprops(orf309_id))
    print(get_channelprops(ppe_id))

    print("-"*10 + "get_userinfo" + "-"*10)
    print(get_userinfo(joseph_id))

    print("-"*10 + "get_channelname" + "-"*10)
    print(get_channelname(little_id))

    # 0th message, idx 1 = messageid
    # at end: guesserid, speakerid
    print(submitguess(little_id, get_messages(little_id)[0][1], joseph_id, riri_id)) #True
    print(submitguess(little_id, get_messages(little_id)[0][1], riri_id, ethan_id)) #False


    print(submitguess(little_id, get_messages(little_id)[1][1], riri_id, ethan_id)) #True
    print(submitguess(little_id, get_messages(little_id)[1][1], joseph_id, ethan_id)) #True

    submitguess(ppe_id, get_messages(ppe_id)[0][1], joseph_id, andrew_id) #True


    print(get_gratio_by_channel(joseph_id, little_id)) #1
    print(get_gratio_by_channel(riri_id, little_id)) # 0.5
    print(get_gratio_by_channel(ethan_id, little_id)) #0
    print(get_gratio_by_channel(joseph_id, ppe_id)) #1
    print(get_gratio_by_channel(michelle_id, ppe_id)) #0

    print(get_gratio_aggregate(joseph_id)) #1

    print(get_idratio_by_channel(riri_id, little_id)) #1
    print(get_idratio_by_channel(ethan_id, little_id)) #.6666
    print(get_idratio_by_channel(joseph_id, orf309_id)) #0

    print(get_correct_guessers(little_id, get_messages(little_id)[0][1])) # joseph xu
    print(get_correct_guessers(little_id, get_messages(little_id)[1][1])) # riri jiang, joseph xu

    # test for frontend 
    print('cos333 id: %s' % cos333_id)
    print(submitguess(cos333_id, get_messages(cos333_id)[0][1], joseph_id, bryan_id)) # True
    print(submitguess(cos333_id, get_messages(cos333_id)[0][1], joanna_id, joseph_id)) # False

    print(get_correct_guessers(cos333_id, get_messages(cos333_id)[0][1])) # [(joseph, xu)]
    print(get_correct_guessers(cos333_id, get_messages(cos333_id)[1][1])) # []

    print(has_guessed(joseph_id, cos333_id, get_messages(cos333_id)[0][1])) #True
    print(has_guessed(joseph_id, cos333_id, get_messages(cos333_id)[0][2])) #False

    print(upload_user_pfp(joseph_id, 'https://www.gstatic.com/webp/gallery/1.jpg'))
    print(get_user_pfp(joseph_id))

    print(upload_channel_pfp(little_id, 'https://www.gstatic.com/webp/gallery/2.jpg'))
    print(get_channel_pfp(little_id))

    make_moderator(cos333_id, joseph_id)
    make_moderator(little_id, riri_id)

    print(get_messages_by_content(little_id, 'do'))


if __name__ == '__main__':
    main()
