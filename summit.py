#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#----------------------------------------------------------------------------
# Created By  : Craig Ots-Maher (Github: ThoughtPaper) 
# Created Date: 2022-03-01
# version = 1.0
# ---------------------------------------------------------------------------
""" Extracts data from the Scouts|Terrain web api and sends a report of changes """
# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
import json
import requests
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib,string,time

# Requires the following libraries:
#    python -m pip install requests
# 

lookback_days = 7
settings_file="summit_profiles.json"

#########
#   Terrain API endpoints, as at 15-Jan-2022 see (https://terrain.scouts.com.au/config.json)
#      achievements.terrain.scouts.com.au
#      events.terrain.scouts.com.au
#      agenda.terrain.scouts.com.au
#      events.terrain.scouts.com.au
#      members.terrain.scouts.com.au
#      metrics.terrain.scouts.com.au
#      templates.terrain.scouts.com.au
#
token_url = "https://cognito-idp.ap-southeast-2.amazonaws.com/"
origin_url = "https://terrain.scouts.com.au"
client_id =  "6v98tbc09aqfvh52fml3usas3c"
#overall metrics url does not work any more = 'https://metrics.terrain.scouts.com.au/units/{0}/members?limit=999&force=1'.format(unit_id)
# so we need to look up members and loop through them???
members_url = 'https://members.terrain.scouts.com.au/units'
metrics_url = 'https://metrics.terrain.scouts.com.au/units'
achievements_url = 'https://achievements.terrain.scouts.com.au/members' # /{memberid}/achievements
agenda_url = 'https://agenda.terrain.scouts.com.au/units'
#########

achievements = {
    'intro_scouting' : 'Introduction to Scouting',
    'intro_section' : 'Introduction to Section',
    'milestone' : 'Milestone',
    'outdoor_adventure_skill' : 'OAS',
    'special_interest_area' : 'SIA',
    'course_reflection' : 'Personal Development Course',
    'adventurous_journey' : 'Adventurous Journey',
    'personal_reflection' : 'Personal Reflection',
    'peak_award' : 'Peak Award',
    'sia_stem_innovation' : 'STEM & Innovation',
    'sia_art_literature' : 'Arts & Literature',
    'sia_adventure_sport' : 'Adventure & Sport',
    'sia_better_world' : 'Creating a Better World',
    'sia_environment' : 'Environment',
    'sia_growth_development' : 'Growth & Development',
    'bushcraft' : 'Bushcraft',
    'camping' : 'Camping',
    'bushwalking' : 'Bushwalking',
    'aquatics' : 'Aquatics',
    'vertical' : 'Vertical',
    'alpine' : 'Alpine',
    'paddling' : 'Paddling',
    'boating' : 'Boating',
    'cycling' : 'Cycling' }

milestone_targets = {
    '1' : {'p' : 24, 'a' : 2, 'l' : 1},
    '2' : {'p' : 20, 'a' : 3, 'l' : 2},
    '3' : {'p' : 16, 'a' : 4, 'l' : 4} }

def get_token(username, password):
    headers = {'Origin': origin_url,
      'Referer': origin_url,
      'Content-Type': 'application/x-amz-json-1.1',
      'x-amz-target': 'AWSCognitoIdentityProviderService.InitiateAuth',
    }
    body = {'AuthFlow': 'USER_PASSWORD_AUTH',
      'ClientId': client_id,
      'AuthParameters': { 'USERNAME': username, 'PASSWORD': password },
      'ClientMetadata': {},
    }
    response = requests.post(token_url, headers=headers, json=body)
    if response.status_code >= 500:
        print('[!] [{0}] Server Error'.format(response.status_code))
        return None
    elif response.status_code == 404:
        print('[!] [{0}] URL not found: [{1}]'.format(response.status_code,origin_url))
        return None
    elif response.status_code == 401:
        print('[!] [{0}] Authentication Failed'.format(response.status_code))
        return None
    elif response.status_code >= 400:
        print('[!] [{0}] Bad Request'.format(response.status_code))
        print(ssh_key )
        print(response.content )
        return None
    elif response.status_code >= 300:
        print('[!] [{0}] Unexpected redirect.'.format(response.status_code))
        return None
    elif response.status_code == 201 or response.status_code == 200:
        token = json.loads(response.content.decode('utf-8'))
        return token
    else:
        print('[?] Unexpected Error: [{0}]: Content: {1}'.format(response.status_code, response.content))
        return None

def get_unit_members(token, unit_id):
    headers = { 'authorization': token }
    response = requests.get('{0}/{1}/members'.format(members_url,unit_id), headers=headers, timeout=60)
    if response.status_code >= 502:
        print('[!] Server Error - timeout??: [{0}]: Content: {1}'.format(response.status_code, response.content))
    if response.status_code == 200:
        return json.loads(response.content.decode('utf-8'))
    else:
        return None

def get_member_metrics(token, unit_id, id):
    headers = { 'authorization': token }
    response = requests.get('{0}/{1}/members/{2}'.format(metrics_url,unit_id,id), headers=headers, timeout=60)
    if response.status_code >= 502:
        print('[!] Server Error - timeout??: [{0}]: Content: {1}'.format(response.status_code, response.content))
    if response.status_code == 200:
        return json.loads(response.content.decode('utf-8'))
    else:
        return None        

def get_member_achievements(token, id):
    headers = { 'authorization': token }
    response = requests.get('{0}/{1}/achievements'.format(achievements_url,id), headers=headers, timeout=60)
    if response.status_code >= 502:
        print('[!] Server Error - timeout??: [{0}]: Content: {1}'.format(response.status_code, response.content))
    if response.status_code == 200:
        return json.loads(response.content.decode('utf-8'))
    else:
        return None       

def get_agenda(token, unit_id):
    headers = { 'authorization': token }
    response = requests.get('{0}/{1}/member-agenda'.format(agenda_url,unit_id), headers=headers, timeout=60)
    if response.status_code >= 502:
        print('[!] Server Error - timeout??: [{0}]: Content: {1}'.format(response.status_code, response.content))
    if response.status_code == 200:
        return json.loads(response.content.decode('utf-8'))
    else:
        return None

def check_missing_credits(name, milestone, p_total, a_total, l_total, type):
    result = ''
    p_target = milestone_targets[str(milestone)]["p"]
    a_target = milestone_targets[str(milestone)]["a"]
    l_target = milestone_targets[str(milestone)]["l"]
    #print('the targets are {0} participates, {1} assists, {2} leads'.format(p_target,a_target,l_target))
    if p_total >= p_target:
        if type == 'assists':
            if a_total < a_target:
                result = '{0} ({1}) needs {2}<br>'.format(name,milestone,int(a_target-a_total))
        if type == 'leads':
            if l_total < l_target:
                result = '{0} ({1}) needs {2}<br>'.format(name,milestone,int(l_target-l_total))
    return result

def lookup_achievement(short_text):
    return achievements.get(short_text, short_text)

def run_report(username, password, unit_id, report_recipients,smtp_server,smtp_port,emailuser,emailpass):
    report_start = datetime.datetime.today().astimezone() - datetime.timedelta(days=lookback_days)
 
    token = get_token(username, password)
 
    if token is not None:
        # set up report placeholders
        report_content = ''
        approvals_content = ''
        assists_content = ''
        leads_content = ''
        
        # query for list of members and then collect the achievement info for each member
        user_info = get_unit_members(token["AuthenticationResult"]["IdToken"], unit_id)
        if user_info is not None:
            for x in user_info["results"]:
                current_member = '{0} {1}'.format(x["first_name"],x["last_name"])
                short_name = '{0} {1}'.format(x["first_name"],x["last_name"][:1])
                member_content = ''
                achievement_info = get_member_achievements(token["AuthenticationResult"]["IdToken"],x["id"])
                if achievement_info is not None: 
                    for y in achievement_info["results"]:
                        update_time = datetime.datetime.fromisoformat(y["status_updated"]).astimezone()
                        if y["type"]=='milestone' and y["status"]=='in_progress' and y["milestone_requirement_status"]=='complete':
                            type = '{0} {1}'.format(lookup_achievement(y["type"]),lookup_achievement(y["achievement_meta"]["stage"]))
                            member_content+='  {0} - Ready for review<br>'.format(type)
                            #print('{0} - {1} {2})'.format(type,y["status"],y["status_updated"]))
                        if update_time > report_start:
                            # status options: awarded, not_required, in_progress, draft_review, feedback_review ..
                            if y["status"]=='awarded':
                                type = lookup_achievement(y["type"])
                                if y["type"]=='milestone':
                                    type = '{0} {1}'.format(lookup_achievement(y["type"]),lookup_achievement(y["achievement_meta"]["stage"]))
                                if y["type"]=='special_interest_area':
                                    type = '{0} {1}'.format(lookup_achievement(y["type"]),lookup_achievement(y["answers"]["special_interest_area_selection"]))
                                if y["type"]=='outdoor_adventure_skill':
                                    type = '{0} {1} {2}'.format(lookup_achievement(y["type"]),lookup_achievement(y["achievement_meta"]["stream"]),lookup_achievement(y["achievement_meta"]["stage"]))
                                member_content+='  {0}<br>'.format(type)
                                #print('{0} - {1} ({2})'.format(type,y["status"],y["status_updated"]))
                        if y["type"]=='milestone' and y["status"]=='in_progress' and y["milestone_requirement_status"]=='incomplete':
                            milestone = y["achievement_meta"]["stage"]
                            p_total = (float(y["event_count"]["participant"]["community"]) + 
                                float(y["event_count"]["participant"]["outdoors"]) + 
                                float(y["event_count"]["participant"]["creative"]) + 
                                float(y["event_count"]["participant"]["personal_growth"]))
                            a_total = (float(y["event_count"]["assistant"]["community"]) + 
                                float(y["event_count"]["assistant"]["outdoors"]) + 
                                float(y["event_count"]["assistant"]["creative"]) + 
                                float(y["event_count"]["assistant"]["personal_growth"]))
                            l_total = (float(y["event_count"]["leader"]["community"]) + 
                                float(y["event_count"]["leader"]["outdoors"]) + 
                                float(y["event_count"]["leader"]["creative"]) + 
                                float(y["event_count"]["leader"]["personal_growth"]))
                            #print(' {0} has {1} participates, {2} assists, {3} leads on milestone {4}'.format(short_name,p_total,a_total,l_total,milestone))
                            assists_content+=check_missing_credits(short_name,milestone,p_total,a_total,l_total,'assists')
                            leads_content+=check_missing_credits(short_name,milestone,p_total,a_total,l_total,'leads')
                    if member_content:
                        report_content+='<p><b>{0}</b><br>{1}</p>'.format(current_member,member_content)
                else:
                    print('[!] Achievements data request failed')
        else:
            print('[!] Members data request failed')
        
        # look for any outstanding approvals
        approvals_info = get_agenda(token["AuthenticationResult"]["IdToken"], unit_id)
        if approvals_info is not None:
            for z in approvals_info["items"]:
                approvals_content+= '  {0}<br>'.format(z["title"].replace(" is awaiting approval", ""))
            if approvals_content:
                report_content+='<p><b>Outstanding approvals</b><br>{0}</p>'.format(approvals_content)
        else:
            print('[!] Agenda data request failed')

        # finally add notes re leadership credits
        if assists_content or leads_content:
            if assists_content:
                assists_content = '<i>Assists</i><br>' + assists_content
            if leads_content:
                leads_content = '<i>Leads</i><br>' + leads_content
            report_content+='<p><b>Members needing leadership credits</b> (participation target has been met)<br>{0}<br>{1}</p>'.format(assists_content, leads_content)
            
        # Now print and send report
        if report_content:
            report_content = 'Terrain achievements recorded in the last {0} days<br><br>'.format(lookback_days) + report_content       
            print(report_content)
            send_email(smtp_server, smtp_port, emailuser, emailpass, report_recipients, report_content)
            
    else:
        print('[!] Token Request Failed')

def send_email(server, port, user, password, recipients, message):
    # Try to log in to server and send email
    try:
        email = MIMEMultipart('alternative')
        email['subject'] = "Terrain achievements report"
        email['to'] = ", ".join(recipients)
        email['from'] = emailuser
        body = MIMEText(message,'html')
        email.attach(body)
        server = smtplib.SMTP(server,port)
        server.login(user,password)
        server.sendmail(email['from'],recipients,email.as_string())
    except Exception as e:
        # Print any error messages to stdout
        print(e)
    finally:
        server.quit() 
        

###############################################################################
#  Summit Terrain weekly update email reporting tool
###############################################################################

with open(settings_file) as json_file:
   settings = json.load(json_file)
   smtp_server = settings["smtp_server"]
   smtp_port = settings["smtp_port"]
   emailuser = settings["smtp_user"]
   emailpass = settings["smtp_pass"]
   print('Output server details: {0}:{1}, user={2}'.format(smtp_server,smtp_port,emailuser))

   for profile in settings["profiles"]:
      print('Running report for: {}'.format(profile["name"]))
      #run repot tool
      run_report(profile["username"],profile["password"],profile["unit_id"],profile["report_recipients"],smtp_server,smtp_port,emailuser,emailpass)
