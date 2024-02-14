#!/usr/bin/env python

#-----------------------------------------------------------------------
# verbatims.py
# Author: Bryan Wang, Joanna Tang, Joseph Xu
#-----------------------------------------------------------------------

from flask import Flask, request, make_response, redirect, url_for
from flask import render_template, send_from_directory
from keys import APP_SECRET_KEY
from html import escape

from db import *

#-----------------------------------------------------------------------
app = Flask(__name__, template_folder='./templates')

@app.before_request
def before_request():
    if not request.is_secure:
        url = request.url.replace('http://', 'https://', 1)
        return redirect(url, code=301)
 
app.secret_key = APP_SECRET_KEY

import auth

#-----------------------------------------------------------------------
@app.route('/static/<path:path>')

def send_static_file(path):
    return send_from_directory('static', path)

#-----------------------------------------------------------------------
@app.route('/', methods=['GET'])
@app.route('/index', methods=['GET']) #login page

def index():
    username = auth.authenticate().strip()

    # if new user login, redirect to new_user_page to ask for basic info
    # otherwise, redirect to channels page
    userexists = userid_exists(username)
    if (userexists):
        response = redirect(url_for('get_channel'))
    else:
        response = redirect(url_for('splash'))
            
    return response

#-----------------------------------------------------------------------
@app.route('/channel', methods=['POST'])

def add_message_to_database():
    username = auth.authenticate().strip()
    userid = get_userid(username)

    channelid = int(request.cookies.get("channelid"))
    new_message = request.args.get('content')
    # speaker is the username of the speaker
    speaker = request.args.get('speaker')

    if speaker != 'other':
        speakerid = get_userid(speaker)
    else: 
        speakerid = -1

    send_message(channelid, userid, new_message, speakerid)

    return "Message sent to database"

#-----------------------------------------------------------------------
@app.route('/channel', methods=['GET'])

def get_channel(): 
    # if the user does not exist, should redirect to splash page
    username = auth.authenticate().strip()
    userexists = userid_exists(username)
    if (not userexists):
        response = redirect(url_for('splash'))
    else:
        try:
            userid = get_userid(username)

            # dictionary for channel profile pics
            channelpfps = {}
            # dictionary of channel id and list of str messages
            messages = {}
            hasGuessedDict = {}
            channelid = request.cookies.get('channelid')
            user_gratio_channel = 0
            user_idratio_channel = 0
            current_channelname = '',
            members = []
            memberids = {}
            moderator = False
            groupcode = None
            numMod = 0
            userpfp = ''
            userchannels = []
            currchannelpfp = ''
            channelpfps = {}

            # get user's pfp
            userpfp = get_user_pfp(userid)
            userchannels = get_userchannels(userid)

            cid_elements = [a_tuple[0] for a_tuple in userchannels]
            if len(userchannels) != 0:

                if channelid is None or channelid == '':
                    channels = home_to_channels()

                    channelid = str(next(iter(channels)))
                if not channelid.isnumeric() or int(channelid) not in cid_elements:
                    channels = home_to_channels()
                    channelid = str(next(iter(channels)))

                moderator = is_moderator(channelid, userid)

                groupcode = get_channelprops(channelid)['groupcode']

                for g in userchannels:
                    channelpfps[str(g[0])] = get_channel_pfp(g[0])
                    messageinfo = get_messages(g[0])
                    messages[str(g[0])] = messageinfo
                for msg in messages[str(channelid)]:
                    messageid = msg[1]
                    hasGuessedDict[messageid] = has_guessed(userid, channelid, messageid)

                for sublist in userchannels:
                    if str(sublist[0]) == str(channelid):
                        current_channelname = sublist[1]
                        break
                # get the membersof the current channel 
                memberids = get_users(channelid)

                for memberid in memberids:
                    members.append(get_userinfo(memberid))
                    if memberids[memberid] == True:
                        numMod = numMod + 1
            
                user_gratio_channel = get_gratio_by_channel(userid, int(channelid))
                user_idratio_channel = get_idratio_by_channel(userid, int(channelid))

            if channelid is None or channelid == 'None' or not channelid.isnumeric() or int(channelid) not in cid_elements:
                currchannelpfp = 'https://engineering.princeton.edu/wp-content/uploads/2021/08/dondero_450x600_1-1.jpg'
            else:
                currchannelpfp = channelpfps[channelid]
            
            html = render_template('channel.html',
                current_group = current_channelname,
                userid = userid,
                userchannels = userchannels, 
                channelid = channelid,
                groupcode = groupcode, 
                members = members,
                guessDict = hasGuessedDict,
                currchannelpfp = currchannelpfp,
                channelpfps = channelpfps,
                curruserpfp = userpfp,
                user_gratio_channel = user_gratio_channel,
                user_idratio_channel = user_idratio_channel, 
                moderator = moderator,
                memberids = memberids,
                numMod = numMod, 
                userexists = userexists
                )

            response = make_response(html)
            response.set_cookie('channelid', str(channelid))
        except Exception as ex:
            print("Exception: %s" % ex)
            response = redirect(url_for('error_page', error_msg=ex))
            return response
     
    return response
#-----------------------------------------------------------------------
"""
Endpoint for ajax request that updates all of the messages
"""
@app.route('/all_messages', methods=['POST'])
def get_all_messages(): 
    username = auth.authenticate().strip()
    userid = get_userid(username)

    userchannels = []
    messages = {}
    hasGuessedDict = {}
    channelid = request.cookies.get('channelid')
    members = []
    moderator = False
    memberids = {}

    userchannels = get_userchannels(userid)

    if len(userchannels) != 0:

        if channelid is None or channelid == '':
            channels = home_to_channels()

            channelid = str(next(iter(channels)))
        cid_elements = [a_tuple[0] for a_tuple in userchannels]
      
        if not channelid.isnumeric() or int(channelid) not in cid_elements:
            channels = home_to_channels()
            channelid = str(next(iter(channels)))

        moderator = is_moderator(channelid, userid)

        for g in userchannels:
            if 'content' in request.args:
                messageinfo = get_messages_by_content(g[0], request.args.get('content'))
            else:
                messageinfo = get_messages(g[0])
            messages[str(g[0])] = messageinfo
        for msg in messages[str(channelid)]:
            messageid = msg[1]
            hasGuessedDict[messageid] = has_guessed(userid, channelid, messageid)
        memberids = get_users(channelid)

        for memberid in memberids:
            members.append(get_userinfo(memberid))
    return {
        'userid': userid,
        'messages_dictionary': messages,
        'channelid': channelid,
        'members': members,
        'guessDict': hasGuessedDict,
        'moderator': moderator, 
        'memberids': memberids,
    }

#-----------------------------------------------------------------------
@app.route('/error', methods=['GET'])

def error_page():

    error_msg = request.args.get('error_msg')
    html = render_template('errorpage.html',
        error_msg = error_msg
        )
    response = make_response(html)
    return response

#-----------------------------------------------------------------------
@app.route('/create_channel', methods=["POST"])
 
def createchannel():
   username = auth.authenticate().strip()
   userid = get_userid(username)
   # retrieve cookie information
   name = request.form['channelname']
   channelid = create_channel(name)
 
   # add user to channel
   add_user_to_channel(channelid, userid)
 
   # add moderator
   make_moderator(channelid, userid)

   # upload default photo
   upload_channel_pfp(channelid, "./static/verbatims_splash_design-6.jpg")
 
   # create response object
   response = redirect(url_for('get_channel'))
 
   # set channelid cookie
   response.set_cookie('channelid', str(channelid))
 
   # channelid on success
   return response
 
#-----------------------------------------------------------------------
@app.route('/add_moderator', methods=["POST"])
 
def add_moderator():
    # takes a channelid and and userid as params
    username = auth.authenticate().strip()
    userid = get_userid(username)
    # retrieve params
    channelid = str(request.args.get('channelid'))
    idToAdd = str(request.args.get('userid'))

    make_moderator(channelid, idToAdd)

    userinfo = get_userinfo(userid)
    # success statement
    return "moderator %s has been made" % (userinfo["username"])

#-----------------------------------------------------------------------
@app.route('/delete_message', methods=["POST"])
 
def deletemessage():
   #takes a channelid and messageid as params
    username = auth.authenticate().strip()
    userid = get_userid(username)
    # retrieve params
    channelid = request.args.get('channelid')
    messageid = request.args.get('messageid')
    
    # delete message
    delete_message(channelid, messageid)
    
    # success statement
    return "message has been deleted"

#-----------------------------------------------------------------------
@app.route('/leave_channel', methods=["POST"])
 
def leavechannel():
    #takes a channelid and messageid as params
    username = auth.authenticate().strip()
    userid = get_userid(username)
    # retrieve params
    channelid = request.args.get('channelid')

    # leave in db
    leave_channel(channelid, userid)
    users = {}
    users = get_users(channelid)
    numUsers = len(users)
    
    # delete if no other members
    if numUsers == 0:
        delete_channel(channelid)
    elif numUsers == 1:
        make_moderator(channelid, next(iter(users)))
    
    # success statement
    return "message has been deleted"

#-----------------------------------------------------------------------
@app.route('/settings', methods=['GET'])

def settings():
    username = auth.authenticate().strip()

    userexists = userid_exists(username)
    if (not userexists):
        response = redirect(url_for('splash'))
    else:
        try: 
            userid = get_userid(username)
            idratio_agg = get_idratio_aggregate(userid)
            gratio_agg = get_gratio_aggregate(userid)
            
            userinfo = get_userinfo(userid)
            html = render_template('settings.html',
                name = userinfo["firstname"] + " " + userinfo["lastname"],
                userinfo = userinfo, 
                curruserpfp = userinfo['pfpurl'],
                idratio_agg = idratio_agg,
                gratio_agg = gratio_agg,
                userexists = userexists
                )
            response = make_response(html)
        except Exception as ex:
            print("Exception: %s" % ex)
            response = redirect(url_for('error_page', error_msg=ex)) 
    return response

#-----------------------------------------------------------------------
@app.route('/profile', methods=['GET'])
def profile():
    username = auth.authenticate().strip()

    userexists = userid_exists(username)
    if (not userexists):
        response = redirect(url_for('splash'))
    else:
        try:
            userid = request.cookies.get('viewprofileid')
            # if the user just created an account and manually goes to /profile
            if (userid is None):
                return redirect(url_for('error_page', error_msg = '403: Forbidden'))
            else:
                userid = int(userid)
                userinfo = get_userinfo(userid)
                idratio = get_idratio_aggregate(userid)
                gratio = get_gratio_aggregate(userid)
                html = render_template('profile.html',
                    name = userinfo["firstname"] + " " + userinfo["lastname"],
                    userinfo = userinfo, 
                    curruserpfp = get_user_pfp(get_userid(username)),
                    userexists = userexists, 
                    idratio = idratio,
                    gratio = gratio
                    )
                response = make_response(html)
        except Exception as ex:
            print("Exception: %s" % ex)
            response = redirect(url_for('error_page', error_msg=ex)) 
    return response

#-----------------------------------------------------------------------
@app.route('/change_userpfp', methods=['POST'])
def change_userpfp():
    username = auth.authenticate().strip()
    userid = get_userid(username)

    userpfp_url = request.args.get("userpfp_url")
    pfpid = request.args.get("pfpid")

    update_user_pfp(userid, pfpid, userpfp_url)  

    # send back url
    res = {}
    res['userpfp_url'] = userpfp_url
    return res

#-----------------------------------------------------------------------
@app.route('/changeuserinfo', methods=['POST'])

def change_user_info():
    username = auth.authenticate().strip()
    userid = get_userid(username)

    first = request.args.get("first")
    last = request.args.get("last")
    bio = request.args.get("bio")

    update_user(first, last, userid, bio)

    return "User info updated" 

#-----------------------------------------------------------------------
@app.route('/change_channelpfp', methods=['POST'])

def change_channelpfp():
    channelid = str(request.cookies.get('channelid'))

    channelpfp_url = request.args.get("channelpfp_url")
    pfpid = request.args.get("pfpid")

    update_channel_pfp(channelid, pfpid, channelpfp_url)

    # send back url
    res = {}
    res['channelpfp_url'] = channelpfp_url
    return res


#-----------------------------------------------------------------------
@app.route('/leaderboard', methods=['POST'])

def leaderboard():
    username = auth.authenticate().strip()

    userexists = userid_exists(username)
    if (not userexists):
        return redirect(url_for('splash'))
    else:
        userid = get_userid(username)
        channelid = str(request.cookies.get('channelid'))
        criteria = 'numrightguess'

        #list of members and score sorted by criteria DESCENDING
        sortedMembers = get_sorted_members(channelid, criteria)

        first, second, third = None, None, None
        personal = None

        for (memberid, score) in sortedMembers:
            if first is None:
                first = (memberid, score)
            elif second is None:
                second = (memberid, score)
            elif third is None:
                third = (memberid, score)
            if memberid == userid:
                personal = score
        
        if first[0] == userid or second[0] == userid or third[0] == userid:
            personal = "you are the absolute goat. \nCongrats on making the top three."
        print (first, second, third, personal)

        if first is not None:
            first = (get_username(first[0]),first[1])
            if second is not None:
                second = (get_username(second[0]),second[1])
                if third is not None:
                    third = (get_username(third[0]),third[1])

    return {"first":first, "second":second, "third":third, "personal":personal}

#-----------------------------------------------------------------------
@app.route('/groupcode', methods=['GET'])
def groupcode():
    username = auth.authenticate().strip()
    groupcode = request.args.get('code')
    if (groupcode is None or groupcode == ''):
        return redirect(url_for('error_page', error_msg = 'Missing groupcode'))

    channelid = get_channelid_from_groupcode(groupcode)
    if (isinstance(channelid, Exception)):
        response = redirect(url_for('error_page', error_msg = 'Invalid group code'))
        response.delete_cookie('groupcode')
        return response   

    userexists = userid_exists(username)
    if (not userexists):
        response = redirect(url_for('splash'))
    else:
        # try looking for channel with groupcode given
        try:
            userid = get_userid(username)
            add_user_to_channel(channelid, userid)
            response = redirect(url_for('get_channel'))
        except Exception as ex: 
            response = redirect(url_for('error_page', error_msg = ex))

    response.set_cookie('groupcode', str(groupcode))
    return response
    
#-----------------------------------------------------------------------
@app.route('/join_group', methods = ['POST'])

def join_group():
    username = auth.authenticate().strip()
    userid = get_userid(username)

    group_code = request.form['group_code'].upper()
    channelid = get_channelid_from_groupcode(group_code)
    if isinstance(channelid, Exception):
        return redirect(url_for('error_page', error_msg='Invalid group code'))
    if channelid is None:
        error_msg = 'No group code specified.'
        # we should make an error page
        return redirect(url_for('error_page', error_msg=error_msg))

    # otherwise, add user to the channel and redirect to the channel page
    # for the group user just joined
    add_user_to_channel(channelid, userid)
    response = redirect(url_for('get_channel'))
    response.set_cookie('channelid', str(channelid))

    return response

#-----------------------------------------------------------------------
@app.route('/get_corrects', methods=['POST'])

def get_corrects():
    username = auth.authenticate().strip()
    userid = get_userid(username)
    channelid = int(request.args.get('channelid'))
    messageid = int(request.args.get('messageid'))
    correct_guessers = get_correct_guessers(channelid, messageid)

    speakerid = get_speakerid(channelid, messageid)
    if speakerid == -1:
        speaker = None
    else:
        speaker = get_userinfo(get_speakerid(channelid, messageid))['username']

    guessers = []
    guessers = get_guessers(channelid, messageid)
    total_guessers = len(guessers)

    # should be the percentage of correct guessers
    successcount = 0
    for namepair in correct_guessers:
        successcount +=1

    if total_guessers == 0:
        percent = 0.0
    else:
        percent = round(successcount/total_guessers, 4) * 100

    return {
        'is_correct': True,
        'correct_guessers': correct_guessers,
        'percentage_correct': percent,
        'channelid': channelid,
        'speaker': speaker,
        'speakerid': speakerid
        }

#-----------------------------------------------------------------------
@app.route('/guess', methods=['POST'])

def guess():
    # messageid
    username = auth.authenticate().strip()
    speakerid = int(request.args.get('user_guessid'))
    channelid = int(request.cookies.get('channelid'))
    guesserid = int(get_userid(username))
    messageid = int(request.args.get('messageid'))

    is_correct = submitguess(channelid, messageid, guesserid, speakerid)
    correct_guessers = get_correct_guessers(channelid, messageid)

    guessers = []
    guessers = get_guessers(channelid, messageid)
    total_guessers = len(guessers)

    # should be the percentage of correct guessers
    successcount = 0
    for namepair in correct_guessers:
        successcount +=1

    percent = round(successcount/total_guessers, 4) * 100
    speaker = get_userinfo(get_speakerid(channelid, messageid))['username']
    idratio = get_idratio_by_channel(guesserid, channelid)
    gratio = get_gratio_by_channel(guesserid, channelid)

    return {
        'is_correct': is_correct,
        'correct_guessers': correct_guessers,
        'percentage_correct': percent,
        'channelid': channelid,
        'speaker': speaker,
        'idratio_channel': idratio, 
        'gratio_channel': gratio
    }

#-----------------------------------------------------------------------
@app.route('/searchgroupresults', methods=["POST"])

def search_group_results():
    username = auth.authenticate().strip()
    userid = get_userid(username)
    # retrieve cookie information

    channelid = request.cookies.get('channelid')
    if channelid is None or channelid == 'None':
        userchannels = []
    else:
        userchannels = get_userchannels(userid)
    userinput = request.args.get('group')

    html = ''
    bold = ''
    for chan in userchannels:
        if str(chan[0]) == channelid:
            bold = 'fw-bolder'
        # remove test channel creation because (channel id, (None)) stored in database
        if chan[1] is None:
            continue
        if chan[1].startswith(userinput):
            html += '<div class="w-100">'
            html += '<form action="channel" method="get">'
            html += '<a class="btn text-start text-decoration-none ' + bold + '" '
            html += 'onclick="channel_cookie( ' + str(chan[0]) + ' )" href="channel">'
            html += '<div class="d-flex flex-row align-items-center justify-content-start">'
            html += '<div>'
            html += '<img width="50" height="50" class="shadow-sm profile-image border border-1 rounded-circle me-2" src="' + get_channel_pfp(chan[0]) + '" alt="group2 img">'
            html += '</div>'
            html += '<div class="w-100">'
            html += '<span class="text-black h5 text-wrap text-start" id="group" >'
            html += escape(chan[1])
            html += '</span></div></div></a></form><hr></div>'
        bold = ''

    response = make_response(html)
    return response

#-----------------------------------------------------------------------
@app.route('/create_new_user', methods=['POST'])

def create_new_user():
    username = auth.authenticate().strip()
    firstname = request.form['userfirstname']
    lastname = request.form['userlastname']
    bio = request.form['userbio']
    
    if bio is None:
        bio = ''

    # add user to database
    userid = create_user(firstname, lastname, username, bio)

    # upload default photo
    upload_user_pfp(userid, "./static/defaultphoto.jpeg")

    if (('groupcode' in request.cookies) and (isValid(request.cookies['groupcode']))):
        channelid = get_channelid_from_groupcode(request.cookies['groupcode'])
        add_user_to_channel(channelid, userid)

    response = redirect(url_for('get_channel'))
    response.delete_cookie('groupcode')

    return response

#-----------------------------------------------------------------------
@app.route('/new_user_page', methods=['GET'])

def new_user_page():
    username = auth.authenticate().strip()

    userexists = userid_exists(username)
    # if the user does not exist in the db, go to splash page
    # otherwise, user exists, go directly to the channels page
    if (userexists):
        response = redirect(url_for('get_channel'))
    else:
        html = render_template('newuser.html', 
            #username = username
        )
        response = make_response(html)
        response.delete_cookie('channelid')

    return response

#-----------------------------------------------------------------------
@app.route('/splash', methods=['GET']) #splash page
def splash():
    try:
        username = auth.authenticate().strip()
        # userchannels is a list of (channelid, channelname)
        html = render_template('splash.html')
        response = make_response(html)
    except Exception as ex:
        print("Exception: %s" % ex)
        response = redirect(url_for('error_page', error_msg=ex)) 
    return response

#-----------------------------------------------------------------------
@app.route('/faq', methods=['GET']) #faq page
def faq():
    username = auth.authenticate().strip()
    userexists = userid_exists(username)
    # if the user does not exist in the db, still show faq page with profile pic as default
    if (not userexists):
        userpfp = "./static/defaultphoto.jpeg"
        
    else:
        try:
            userid = get_userid(username)
            userpfp = get_user_pfp(userid)
        except Exception as ex:
            print("Exception: %s" % ex)
            response = redirect(url_for('error_page', error_msg=ex)) 
    
    html = render_template('faq.html',
                curruserpfp = userpfp,
                userexists = userexists
                )
    response = make_response(html)
    return response

#-----------------------------------------------------------------------
def home_to_channels():
    username = auth.authenticate().strip()
    userid = get_userid(username)

    # retrieve channels, if they exist
    channelnames = get_userchannels(userid)

    channeldict = {}
    for g in channelnames:
        channeldict[g[0]] = g[1]
    
    # dictionary where key is channel id and value is channel names
    return channeldict

#-----------------------------------------------------------------------
