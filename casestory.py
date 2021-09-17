# Copyright 2021 DataStax, Inc

import asyncio
from io import StringIO
import os
import logging
from datetime import timezone

import requests
from aiosfstream import Client, RefreshTokenAuthenticator, PasswordAuthenticator
from simple_salesforce import Salesforce, SalesforceExpiredSession

# visualization
import plotly.express as px
import pandas as pd


username = ""
password = ""
token = ""
client_id = ""
client_secret = ""
refresh_token = ""
sandbox = False  # change if using the production version of salesforce

agent_dict = {}

with open("agents.txt") as f:
    lines = f.readlines()
    for line in lines:
        result = [x.strip() for x in line.split(",")]
        agent_dict[result[1]] = result[0]


class Extract:
    def __init__(self):
        self.sf_auth()

    def sf_auth(self):
        domain = "test" if sandbox else "login"
        if refresh_token is not None:
            params = {
                "grant_type": "refresh_token",
                "redirect_uri": f"https://{domain}.salesforce.com/",
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
            }
            url = f"https://{domain}.salesforce.com/services/oauth2/token"
            response = requests.post(url, params=params).json()
            print(response)
            self.sf = Salesforce(
                instance_url=response["instance_url"],
                session_id=response["access_token"],
            )
        else:
            self.sf = Salesforce(
                username=username,
                password=password,
                security_token=token,
                domain=domain,
            )

    def query(self, stmt, retry=True):
        try:
            return self.sf.query_all_iter(stmt)
        except SalesforceExpiredSession as ex:
            if not retry:
                raise ex
            self.sf_auth()
            return self.query(stmt, retry=False)


casenumber = input("Case Number: ")
try:
    val = int(casenumber)
except ValueError:
    raise RuntimeError("Please put in a valid CaseNumber")

caseid_stmt = f"""
    SELECT Id, CaseNumber FROM Case WHERE CaseNumber = '{casenumber}'
"""
sf = Extract()
sf.sf_auth()
caseidresult = sf.query(caseid_stmt)
caseid = " "
for result in caseidresult:
    caseid = result["Id"]
query_stmt = f"""
        SELECT Id, CreatedDate, Comment__c, Case__c, Public__c, CommentAuthor__c FROM Conversation__c WHERE Case__c = '{caseid}'
    """
raw_data = sf.query(query_stmt)
datastax_external = []
datastax_internal = []
customer = []
lastResponse = []
timestamp = []
date = []
date_bucket = []
total = []
external = []
internal = []
customerC = []

for comments in raw_data:
        count = 0
        counte = 0
        counti = 0
        countc = 0
        if comments["Public__c"] == False:
            datastax_internal.append(comments)
            timestamp.append(pd.to_datetime(comments["CreatedDate"]))
            date.append(pd.to_datetime(comments["CreatedDate"]).date())
            lastResponse.append('Support')
            count = count + 1
            total.append(count)
            counti = counti + 1
            internal.append(counti)
            counte = counte
            external.append(counte)
            countc = countc
            customerC.append(countc)

        if (
                str(comments["CommentAuthor__c"]) not in agent_dict
                and comments["Public__c"] == True
        ):
            # print(comments["Comment__c"])
            timestamp.append(pd.to_datetime(comments["CreatedDate"]))
            date.append(pd.to_datetime(comments["CreatedDate"]).date())
            lastResponse.append('Customer')
            customer.append(comments)
            count = count + 1
            total.append(count)
            countc = countc + 1
            customerC.append(countc)
            counte = counte
            external.append(counte)
            counti = counti
            internal.append(counti)

        else:
            timestamp.append(pd.to_datetime(comments["CreatedDate"]))
            date.append(pd.to_datetime(comments["CreatedDate"]).date())
            lastResponse.append('Support')
            datastax_external.append(comments)
            count = count + 1
            total.append(count)
            counte = counte + 1
            external.append(counte)
            counti = counti
            internal.append(counti)
            countc = countc
            customerC.append(countc)

print(datastax_external)
print(datastax_internal)
print(customer)
print(lastResponse)
print(date)

print(total)
print(external)
print(internal)
print(customerC)

#Visualization
d = {'date': date, 'timestamp': timestamp, 'external': external, 'internal': internal, 'customer': customerC, 'total': total , 'lastResponse': lastResponse}
df = pd.DataFrame(data=d)
print(df)
fig = px.bar(df, x='timestamp', y='total', title='Ticket story', color='lastResponse')
fig2 = px.bar(df, x='date', y='total', title='Ticket story', color='lastResponse')

import dash
import dash_core_components as dcc
import dash_html_components as html

app = dash.Dash()

app.layout = html.Div([
    dcc.Graph(figure=fig),
    dcc.Graph(figure=fig2)
])
app.run_server(debug=True, use_reloader=False)