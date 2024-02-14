function channel_cookie(channelid) {
    document.cookie = "channelid=" + channelid;
}

let request_search = null
let speakerusername = ''

// use javascript to check if guess is correct
function updateVerbatimDisplay(response, messageid, guess) {
    // disable guess button if already guessed
    let guessbuttonid = response['channelid'] + "-" + messageid + "-guess-button";
    $('#'+guessbuttonid).addClass('d-none');
    // format of response: dict
    // {is_correct: boolean, correct_guessers: list of correct_guessers}
    // correct_guessers is list of tuples (firstName, lastName)
    let correct_guessers = response['correct_guessers'];

    let display_correct = '<div class="row no-gutters w-100 pe-0 me-0">';
    display_correct += '<div class="col-sm-12 ps-3 pe-3 text-wrap me-0">';
    for (let index = 0; index < correct_guessers.length; index++) {
        display_correct += htmlEncode(correct_guessers[index][0]) + " " + htmlEncode(correct_guessers[index][1]);
        if (index < correct_guessers.length - 1) {
            display_correct += ', ';
        }
    }
    if (correct_guessers.length >= 4) {
        display_correct += ' + ' + (correct_guessers.length - 3);
    }
    display_correct += '</div></div>'
    let vertid = 'guess-side-of-' + messageid;
    let vertcardid = 'verbatim-card-' + messageid;
    let vertpercentage = messageid + '-percentage';
    // change the right side of verbatim (initially dropdown for guessing the speaker) to display the users that have guessed correctly
    $('#' + vertid).html(display_correct);
    // $('#' + vertcardid).removeClass('bg-powder-blue'); 139, 144, 167, | 255, 228, 252,
    $('#' + vertid).css('background-color', 'rgba(172, 218, 233, ' + (response["percentage_correct"] / 100) + ')');


    // on top of the names of correct guessers
    $('#' + vertpercentage).html(response["percentage_correct"] + '% correct');

    // add the speaker to the other side
    let messagespanid = response['channelid'] + "-" + messageid;
    let speaker = ' <a class=" hover text-decoration-underline link-dark" onclick="view_profile(' + response['speakerid'] +')" href="#">@' + htmlEncode(response['speaker']) + '</a>';
    $('#' + messagespanid).append(speaker);

}

let request_guess = null;
function sendGuess(messageid, guess) {
    let url = '/guess?messageid=' + encodeURIComponent(messageid) + '&user_guessid=' + encodeURIComponent(guess)
    request_guess = $.ajax(
        {
            type: 'POST',
            url: url,
            success: function (res) {
                updateVerbatimDisplay(res, messageid, guess);
                let idratio = (res['idratio_channel'] * 100).toFixed(2)
                $('#user-idratio-channel').html(idratio)
                let gratio = (res['gratio_channel'] * 100).toFixed(2)
                $('#user-gratio-channel').html(gratio)

                let channelid = res['channelid']
                showLeaderboard(channelid)
                // add an animation if correct
                if (res['is_correct']) {
                    $('#correctReward-'+ messageid).removeClass("invisible");
                    $('#correctReward-'+ messageid).addClass("d-block");
                    $('#correctReward-'+ messageid).addClass('animate__animated animate__fadeInLeft');
                    setTimeout( function() {
                        $('#correctReward-'+ messageid).removeClass('animate__animated animate__fadeInLeft');
                        $('#correctReward-'+ messageid).addClass('animate__animated animate__fadeOutRight');
                    }, 2000);
                }
            }
        }
    );
}

// post a verbatim 
let request_post = null;
function post_verbatim() {
    // sanitize input field to delete all html tags
    $('#post-button').addClass('disabled');
    $("#new_message").prop('disabled', true);
    let verbatim = $('#new_message').val().trim();
    let speaker = speakerusername
    if (verbatim === '' || speaker === '') {
        alert('missing verbatim and/or speaker');
        $('#post-button').removeClass('disabled');
        $("#new_message").prop('disabled', false);
    } else {
        $("#new_message").prop('disabled', true);
        $('#post-button').addClass('disabled');
        let url = "/channel?content=" + encodeURIComponent(verbatim)  + "&speaker=" + encodeURIComponent(speaker);
        request_post = $.ajax(
            {
                method: "POST",
                url: url,
                success: () => {
                    $('#post-button').removeClass('disabled');
                    $("#new_message").val("");
                    $('#dropdownMenuSpeakers').html("Speaker");
                    $("#charCounter").html('');
                    getMessages();
                    speakerusername = '';
                    $("#new_message").prop('disabled', false);
                },
            }
        );
    }
}

$("#new_message").on('keyup', function (e) {
    if (e.key === 'Enter' || e.keyCode === 13) {
        $("#new_message").prop('disabled', true);
        console.log("here keyup")
        $("#post-button").click();
    }
});

function selectSpeaker(speaker) {
    let speakerdropdownusername = 'speaker-' + speaker;
    let speakername = $('#' + speakerdropdownusername).text();
    speakername = speakername.replace(/\s\s+/g, ' ');
    if (speakername.length > 20) {
        speakername = speakername.substring(0, 20)
        speakername += '...'
    }
    $('#dropdownMenuSpeakers').html(htmlEncode(speakername));
    speakerusername = speaker;
}

// show channel stats and settings
function showChannelSettings(channelid) {
    $("#channelSettingsModal").modal('show');
}

// show leaderboard on channels page
function showLeaderboard(channelid) {
    getBoard(channelid);
}

// settings page
// if the user changes something, remove disabled class on update button
function setupSettings (ogFirst, ogLast, ogBio) {
    let first = ogFirst;
    let last = ogLast;
    let bio = ogBio
    let updatedfirstname = $('#userfirstnameedit').val().trim();
    let updatedlastname = $('#userlastnameedit').val().trim();
    let updatedbio = $('#userbioedit').val().trim();
    let firstchanged = (updatedfirstname !== first)
    let lastchanged = (updatedlastname !== last)
    let biochanged = (updatedbio !== bio)
    let otherfieldschanged = false;

    $('#userfirstnameedit').on('input', function() {
        updatedfirstname = $('#userfirstnameedit').val().trim();
        if ((updatedfirstname !== '') && (updatedlastname !== ''))
        {
            otherfieldschanged = lastchanged || biochanged
            console.log("otherfields changed a " + otherfieldschanged)
            firstchanged = changeUpdateButtonStatus('update-user-info-button', ogFirst, updatedfirstname, otherfieldschanged)
        }
        if (updatedlastname === '' || updatedfirstname === '') {
            $('#update-user-info-button').addClass('disabled');
        }
    });
    $('#userlastnameedit').on('input', function() {
        updatedlastname = $('#userlastnameedit').val().trim();
        if ((updatedlastname !== '') && (updatedfirstname !== '')) {
            otherfieldschanged = firstchanged || biochanged
            lastchanged = changeUpdateButtonStatus('update-user-info-button', ogLast, updatedlastname, otherfieldschanged)
        }
        if ((updatedlastname === '') || (updatedfirstname === '')) {
            $('#update-user-info-button').addClass('disabled');
        }
    });
    $('#userbioedit').on('input', function() {
        updatedbio = $('#userbioedit').val().trim();
        otherfieldschanged = lastchanged || firstchanged
        biochanged = changeUpdateButtonStatus('update-user-info-button', ogBio, updatedbio, otherfieldschanged)
        if ((updatedlastname === '') || (updatedfirstname === '')) {
            $('#update-user-info-button').addClass('disabled');
        }
    });
}

function readURL(input) {
    if (input.files && input.files[0]) {
      var reader = new FileReader();
      reader.onload = function (e) {
        $('#pfp')
          .attr('src', e.target.result)
          .width(70)
          .height(70);
      };
      reader.readAsDataURL(input.files[0]);
      
    }
}
  
  // copy link to clipboard for invite
function copyInviteLinkToClipboard(groupcode) {
    // get link to copy
    let invitelink = "https://verbatims.herokuapp.com/groupcode?code=" + encodeURI(groupcode)
      
     /* Copy the text inside the text field */
    navigator.clipboard.writeText(invitelink);
}


// display guessing dropdown
function displayGuessingDropdown(messageid) {
    let elem = "#verbatim-"+ messageid;
    $(elem).removeClass('invisible');

}

function disableButton(btnid) {
    $('#' + btnid).addClass('disabled');

}


function convertToLocalTime(date) {
    return new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate(), date.getHours(), date.getMinutes(), date.getSeconds()));
}


function htmlEncode(str) {
    return String(str).replace(/[^\w. ]/gi, function (c) {
        return '&#' + c.charCodeAt(0) + ';';
    });
}

// settings.html page

let request_userpfp_url = null
function send_over_userpfp_url(pfpid_result, url_result) {
    let url = '/change_userpfp?userpfp_url=' + encodeURIComponent(url_result) + '&pfpid=' + encodeURIComponent(pfpid_result)
    request_userpfp_url = $.ajax(
        {
            type: 'POST',
            url: url,
            success: function (res) {
                $(".userpfp").attr("src", res['userpfp_url'])
                //console.log("userpfp url uploaded")
            }
        }
    );
}

// helper function 
// if the input value has changed, activate update button
// otherwise, disable the update button
function changeUpdateButtonStatus(buttonid, og, currentval, otherfieldschanged) {
    console.log ("in change function " + ((og != currentval) || otherfieldschanged))
    if ((og != currentval) || otherfieldschanged) {
        console.log("here")
        $('#'+buttonid).removeClass('disabled');
        return og != currentval;
    } else {
        $('#'+buttonid).addClass('disabled');
        return false;
    }
}

let request_update_userinfo = null;

// update user info
function updateUserInfo() {
    $('#update-user-info-button').addClass('disabled');
    let first = $('#userfirstnameedit').val().trim();
    let last = $('#userlastnameedit').val().trim();
    let bio = $('#userbioedit').val().trim();
    let url = '/changeuserinfo?first='+ encodeURIComponent(first)  + "&last=" + encodeURIComponent(last) + "&bio=" + encodeURIComponent(bio);
    
    request_update_userinfo = $.ajax(
        {
            type: 'POST',
            url: url,
            success: function (res) {
                $('#update-user-info-button').removeClass('disabled');
                location.reload();
            }
        }
    );
}

const myWidget_userpfp = cloudinary.createUploadWidget({
    cloudName: 'verbatims',
    uploadPreset: 'e2qmzyfe',
    cropping: true
},
    (error, result) => {
        if (!error && result && result.event === "success") {
            send_over_userpfp_url(result.info.public_id, result.info.secure_url);
        }
    }
)

// channel.html 
// change channelurl 
let added_moderator = false;

let request_channelpfp_url = null
function send_over_channel_url(pfpid_result, url_result) {
    let url = '/change_channelpfp?channelpfp_url=' + encodeURIComponent(url_result) + '&pfpid=' + encodeURIComponent(pfpid_result)
    request_userpfp_url = $.ajax(
        {
            type: 'POST',
            url: url,
            success: function (res) {
                $(".curr-channel-profile-image").attr("src", res['channelpfp_url'])
            }
        }
    );
}

let request_moderator = null;
function add_moderator(channelid, userid) {
    let url = '/add_moderator?channelid=' + encodeURIComponent(channelid) + "&userid=" + encodeURIComponent(userid);
    request_moderator = $.ajax(
        {
            type: 'POST',
            url: url,
            success: function (res) {
                $('#memname-' + userid).append(' (moderator)');
                $('#moderator-' + userid).addClass('disabled');
                document.cookie = "addedModerator=" + true;

            }
        }
    );
}

let request_delete = null;
function delete_message(channelid, messageid) {
    // disable the trash can if user has already clicked delete
    if (!confirm('Are you sure?')) {
        return;
    }
    let deletebuttonid = channelid + '-' + messageid + "-delete-msg-button";
    $('#' + deletebuttonid).addClass('disabled');
    // create url for post request
    let url = '/delete_message?channelid=' + encodeURIComponent(channelid) + "&messageid=" + encodeURIComponent(messageid);
    request_delete = $.ajax(
        {
            type: 'POST',
            url: url,
            success: function (res) {
                getMessages()
            }
        }
    );
}

let request_leave = null;
function leave_channel(channelid, mod, dictCount, modCount) {
    if (!confirm('Are you sure?')) {
        return;
    }
    // if there are no moderators left and there is more than 1 user left, make user choose a moderator
    if (mod === "True") {
        if (modCount == 1) {
            const cookieValue = document.cookie.split('; ').find(row => row.startsWith('addedModerator=')).split('=')[1];
            if (cookieValue == "false" && dictCount > 1) {
                window.alert("Please select another moderator before you leave the channel.");
                return;
            }
        }
    }

    $('#leave_channel').addClass('disabled');
    // create url for post request
    let url = '/leave_channel?channelid=' + encodeURIComponent(channelid);
    request_leave = $.ajax(
        {
            type: 'POST',
            url: url,
            success: function (res) {
                $('#leave_channel').removeClass('disabled');
                location.href = 'index'
            }
        }
    );

}

function view_profile(userid) {
    document.cookie = "viewprofileid=" + userid;
    // create url for get request
    location.href = 'profile';
}

let request_board = null;
function getBoard(channelid) {
    let url = '/leaderboard?channelid=' + encodeURIComponent(channelid);
    request_board = $.ajax(
        {
            type: 'POST',
            url: url,
            success: function (res) {
                let html_board = '';

                html_board += '<h3>Best guessers</h3>';
                if (res['personal'] == "you are the absolute goat. \nCongrats on making the top three.") {
                    html_board += '<strong>' + htmlEncode(res['personal']) + '</strong>';
                } else {
                    html_board += '<strong>Your score: ' + htmlEncode(res['personal']) + '</strong>';
                }

                html_board += '<div>';
                if (res['first'] != null) {
                    html_board += '<span>' + htmlEncode(res['first'][0]) + ": " + htmlEncode(res['first'][1]) + '</span><br>';
                }
                if (res['second'] != null) {
                    html_board += '<span>' + htmlEncode(res['second'][0]) + ": " + htmlEncode(res['second'][1]) + '</span><br>';
                }
                if (res['third'] != null) {
                    html_board += '<span>' + htmlEncode(res['third'][0]) + ": " + htmlEncode(res['third'][1]) + '</span><br>';
                }
                html_board += '</div>'
                $('#leaderboard-div').html(html_board);
            }
        }
    );
}

// }
let request_messages_by_content = null;
function getMesssagesByContent(content) {
    // todo: rename all_messages
    let url = '/all_messages?content=' + encodeURIComponent(content);
    // todo: modularize
    if (request_messages_by_content != null) {
        request_messages_by_content.abort()
    }
    request_messages_by_content = $.ajax(
        {
            type: 'POST',
            url: url,
            success: function (res) {
                displayMessages(res);
            }
        }
    );

}

function getMessages() {
    let url = '/all_messages';

    // TODO: add abort
    request_messages = $.ajax(
        {
            type: 'POST',
            url: url,
            success: function (res) {
                displayMessages(res);
            }
        }
    );
}


function displayMessages(res) {
    let today = new Date();
    // get date and time exactly 24 hours ago 
    let yesterday = new Date((new Date()).valueOf() - 1000 * 60 * 60 * 24);
    // toLocaleString is of the form mm/dd/yyyy, 00:00:00 AM
    let yesterdaydate = yesterday.toLocaleString().split(", ")[0];
    let currdate = today.toLocaleString().split(", ")[0];
    let prevdate = '';

    // dictionary of members with userids as keys and moderator boolean as values
    let memberids = res['memberids']
    channelid = res['channelid']

    let verbatims_html = ''
    let currchannel_messages = res['messages_dictionary'][channelid]
    let vert;
    let local;
    let localtime;
    let msgdate;
    let msgtime;
    for (let index = 0; index < currchannel_messages.length; index++) {
        vert = currchannel_messages[index];
        local = new Date(Date.parse(vert[4]));
        localtime = local.toLocaleString().split(", ");
        msgdate = localtime[0];
        msgtime = local.toLocaleString('en-US', { hour: 'numeric', minute: 'numeric', hour12: true });

        // if diff date, display it
        if (msgdate !== prevdate) {
            verbatims_html += '<span class=" pb-1 text-center text-dark">';
            if (prevdate === yesterdaydate) {
                verbatims_html += 'Yesterday';
                // } else if (msgdate === yesterdaydate) {
                //     verbatims_html += 'Yesterday';
            }
            else {
                verbatims_html += prevdate;
            }
            verbatims_html += '</span>';
            verbatims_html += '<hr>';
            verbatims_html += '<br>'
            prevdate = msgdate;
        } else {
            verbatims_html += '<br>';
        }

        // block that shows the message
        verbatims_html += '<div class="row">'
        verbatims_html += '<div class="col-md-7">'
        verbatims_html += '<div class="row h-100 no-gutters p-2 pb-0 pe-0 ps-0 position-relative" id="verbatim-card-' + vert[1] + '">'
        verbatims_html += '<div class="col-md-8 text-wrap m-1 d-flex flex-row align-items-center verbatim-bigger-div">';
        verbatims_html += '<div class="shadow vert-bg-color text-break text-wrap border border-dark p-2 verbatim-bubble talkbubble mw-100" style="width:fit-content" id="' + channelid + '-' + vert[1] + '">'
        verbatims_html += htmlEncode((vert[3]));
        verbatims_html += '</div>'

        // dis is for the disabled class, will be empty string if button should NOT be disabled, and 'disabled' otherwise
        let dis = '';
        let disabled = ' disabled ';
        let dontdisplayguess = false;
        verbatims_html += '<div class="verbatim-bubble-more d-flex flex-row">';

        // dont display guess button if you posted or if speaker is no longer in channel
        if ((vert[2] === res['userid']) || !(vert[5] in res['memberids'])) {
            dis = ' d-none ';
            getCorrects(channelid, vert[1]);
            dontdisplayguess = true;
        } else {
            disabled = ''
        }

        verbatims_html += '<button class="btn btn-sm ms-1 ps-2' + dis + disabled + '" id="' + channelid + '-' + vert[1] + '-guess-button" onclick="displayGuessingDropdown(' + vert[1] + ')">'
        verbatims_html += '<small class="guess-button rounded-pill border border-dark ps-1 pe-1 pt-0 pb-0">Guess</small>'
        verbatims_html += '</button>'

        if (res['moderator']) {
            verbatims_html += '<button class="btn btn-small ps-0"'
            verbatims_html += ' id="' + res['channelid'] + '-' + vert[1] + '-delete-msg-button"'
            verbatims_html += 'onclick="delete_message(' + res['channelid'] + ', ' + vert[1] + ')"><span><i class="bi bi-trash ms-1"></i></span></button>'
        }

        verbatims_html += '</div>';
        verbatims_html += '</div>';
        verbatims_html += '<!-- timestamp of verbatim -->';
        verbatims_html += '<div class="row no-gutters">';
        verbatims_html += '<div class="d-flex col-sm-12">';
        verbatims_html += '<small class="text-muted ps-2">' + msgtime + '</small>';
        verbatims_html += '</div>';
        verbatims_html += '</div>';
        verbatims_html += '</div>';
        verbatims_html += '</div>';

        // +1 animation col
        verbatims_html += '<div id="correctReward-' + vert[1] + '" class=" invisible display-1 col-md-1 d-flex justify-content-center">'
        verbatims_html += '+1';
        verbatims_html += '</div>';

        // guessing col
        verbatims_html += '<div class="col-md-4">';
        verbatims_html += '<div class="row mt-0 p-0">';
        verbatims_html += '<div class="col-sm-6"><small class="me-auto me-1">Correct Guessers:</small></div>'
        verbatims_html += '<div class="col-sm-6 text-end">';
        verbatims_html += '<small class="ms-auto pe-0" id="' + vert[1] + '-percentage"></small>'
        verbatims_html += '</div></div>';
        verbatims_html += '<div class="row no-gutters text-wrap guessing-side position-relative" id="guess-side-of-' + vert[1] + '">';

        let currmsgid = vert[1];
        if (!dontdisplayguess && res['guessDict'][currmsgid]) {
            // show the correct guessers
            getCorrects(vert[0], vert[1]);
        }
        else {
            verbatims_html += '<select class="w-75 invisible btn btn-secondary dropdown-toggle" id="verbatim-' + vert[1] + '" name=guess_' + vert[1] + '"'
            verbatims_html += ' onChange="sendGuess(' + vert[1] + ', $(\'#verbatim-' + vert[1] + '\').children(\'option:selected\').val())">'
            verbatims_html += '<option disabled selected>Who said it?</option>';

            for (let m = 0; m < res['members'].length; m++) {
                let mem = res['members'][m];
                verbatims_html += '<option value="' + mem['userid'] + '" class="guess-option text-wrap text-break" id="guess-option-' + currmsgid + '-' + mem['userid'] + '">' + htmlEncode(mem['firstname']) + ' ' + htmlEncode(mem['lastname']) + '</option>';

            }
            verbatims_html += '</select>';
        }
        verbatims_html += '</div></div></div>';
    }
    // display last date
    if (msgdate !== undefined) {
        verbatims_html += '<span class="pb-1 text-center text-dark">';
        if (msgdate === currdate) {
            verbatims_html += 'Today';
        } else if (msgdate === yesterdaydate) {
            verbatims_html += 'Yesterday';
        } else {
            verbatims_html += msgdate;
        }
        verbatims_html += '</span>';
        verbatims_html += '<hr>';
        verbatims_html += '<br>'
        prevdate = msgdate;
    }
    verbatims_html += '<br>';
    toggleResponsive();
    $('#verbatims-display').html(verbatims_html);
}
    
function getCorrects(channelid, messageid) {
    let url = '/get_corrects?channelid=' + encodeURIComponent(channelid) + "&messageid=" + encodeURIComponent(messageid);
    guess = ''
    $.ajax(
        {
            type: 'POST',
            url: url,
            success: function (res) {
                if (res['speaker'] != null) {
                    updateVerbatimDisplay(res, messageid, guess);
                }
            },
            // error: function (res) {
            //     console.log(("Error with request"))
            // }
        }
    );
}
// input field for guesses
function toggleResponsive() {
    if ($(window).width() > 768) { // medium and up
        if ($(window).width() > 992) { // large
            $('#overflow-verbatims').css('height', '80%');
            $('#searchgroupresults').css('height', '80%');

        } else {
            $('#overflow-verbatims').css('height', '70%');
            $('#searchgroupresults').css('height', '70%');
        }

        $('#collapseChannels').removeClass('collapse');
        $('#collapseChannelsButton').addClass('disabled');
        $('#collapseChannelsButton').hide();
        $('#channels-column').css('height', '100%');
        $('#collapseChannels').css('height', '100%');
    }
    else { // small
        $('#collapseChannelsButton').removeClass('disabled');
        $('#collapseChannels').addClass('collapse');
        $('#collapseChannelsButton').show();
        $('#collapseChannels').css('height', '50%');
        $('#searchgroupresults').css('height', '50%');
        $('#overflow-verbatims').css('height', '50%');
        $('#channels-column').css('height', '');
    }
}

function setup_channel() {
    getMessages();
    getSearchGroupResults($('#search_group').val());
    toggleResponsive();
    // $('#search_group').on('input', function () {
    //     let group = $('#search_group').val();
    //     getSearchGroupResults(group)
    // });

    $('#search_group').on('input', function () {
        let group = $('#search_group').val();
        getMesssagesByContent(group)
    });
    $('#new_message').on('input', function () {
        let text = $('#new_message');
        var count = text.val().length;
        // Update that number in the div
        $("#charCounter").html(count + "/1000 characters used")
    });
    $(window).resize(function () {
        toggleResponsive();
    });

    collapseChannels.addEventListener('shown.bs.collapse', function () {
        $('#collapseChannels').css('height', '80%');
    })

    leaderboardcard.addEventListener('shown.bs.collapse', function () {
        $('#overflow-verbatims').css('height', '50%');
    })

    leaderboardcard.addEventListener('hidden.bs.collapse', function () {
        toggleResponsive();
    })

    document.cookie = "addedModerator=" + false;
}

// use this if speaker is text field and autocomplete 
// $("#speaker").on('keyup', function (e) {
//     if (e.key === 'Enter' || e.keyCode === 13) {
//         post_verbatim();
//     }
// });

// search group input field 
function handleSearchGroupResponse(response) {
    $('#searchgroupresults').html(response);
}

function getSearchGroupResults(g) {
    let group = '?group=' + encodeURIComponent(g)
    let url = '/searchgroupresults' + group

    if (request_search != null) request_search.abort();

    request_search = $.ajax(
        {
            type: 'POST',
            url: url,
            success: handleSearchGroupResponse
        }
    );
}

const myWidget_channelpfp = cloudinary.createUploadWidget({
    cloudName: 'verbatims',
    uploadPreset: 'e2qmzyfe',
    cropping: true
},
    (error, result) => {
        if (!error && result && result.event === "success") {
            send_over_channel_url(result.info.public_id, result.info.secure_url);
            // pass in empty string to get all channels
            getSearchGroupResults('');
        }
    }
)

