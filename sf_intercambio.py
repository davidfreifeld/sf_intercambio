import pandas as pd
from datetime import datetime
from simple_salesforce import Salesforce

class Campaign:
    
    def __init__(self, name, date):
        self.name = name
        self.date = date

class Opportunity:
    
    def __init__(self, date, amount):
        self.date = date
        self.amount = amount

class Query:

    def __init__(self, username, password, start_date_str):

        self.sf = Salesforce(
            username=username,
            password=password,
            security_token='***REMOVED***',
            domain='login'
        )

        self.start_date_str = start_date_str

        try:
            datetime.strptime(self.start_date_str, "%Y-%m-%d")
            self.date_operator = '>='
        except:
            self.date_operator = '='
        

    def run(self):

        campaign_query = """
            SELECT 
                Name, 
                StartDate,
                Id,
                (Select Name, CompanyOrAccount, ContactId from CampaignMembers) 
            FROM Campaign
            WHERE StartDate {date_operator} {start_date_str} AND (Type = 'Conference' OR Type = 'Conference Table' OR Type = 'Conference Workshop')
        """.format(date_operator=self.date_operator, start_date_str=self.start_date_str)

        campaign_results = self.sf.query_all(campaign_query)

        account_query = """
            SELECT 
                Name, 
                Id,
                (SELECT Id, Name, CloseDate, Amount FROM Opportunities WHERE CloseDate {date_operator} {start_date_str} AND Amount > 0 AND RecordTypeId = '01280000000UBy3AAG'),
                (SELECT Name, Id FROM Contacts)
            FROM Account
            WHERE Id in (SELECT AccountId FROM Opportunity WHERE CloseDate {date_operator} {start_date_str} AND Amount > 0 AND RecordTypeId = '01280000000UBy3AAG')
            ORDER BY 
                Name
        """.format(date_operator=self.date_operator, start_date_str=self.start_date_str)

        account_results = self.sf.query_all(account_query)

        print(campaign_query)
        print('\n\n\n')
        print(account_query)

        print('\n\n\n')
        print(len(campaign_results['records']))
        print(len(account_results['records']))
        print('\n\n\n')

        contact_to_campaigns_map = {}
        meta_campaign_map = {}

        for campaign_result in campaign_results['records']:
            
            if campaign_result['CampaignMembers'] is not None:
                contacts = campaign_result['CampaignMembers']['records']
                campaign_id = campaign_result['Id']
                campaign_name = campaign_result['Name']
                campaign_date = datetime.strptime(campaign_result['StartDate'], '%Y-%m-%d').date()
                
                meta_campaign_map[campaign_id] = Campaign(name=campaign_name, date=campaign_date)

                for contact in contacts:

                    contact_id = contact['ContactId']

                    if contact_id in contact_to_campaigns_map:
                        contact_to_campaigns_map[contact_id].add(campaign_id)
                    else:
                        contact_to_campaigns_map[contact_id] = { campaign_id } # a set

        account_to_campaigns_map = {}
        account_to_opps_map = {}
        meta_account_map = {}

        for i_a, account_result in enumerate(account_results['records']):
            
            if account_result['Contacts'] is not None and account_result['Opportunities'] is not None:
                
                account_name = account_result['Name']
                account_id = account_result['Id']
                meta_account_map[account_id] = account_name
                
                print(f"Processing Org ({i_a}): {account_id}: {account_name}")
                
                # Contacts / Campaigns
                contacts = account_result['Contacts']['records']
                account_to_campaigns_map[account_id] = set()
                
                for contact in contacts:
                    
                    contact_id = contact['Id']
                    contact_name = contact['Name']
                    
                    if contact_id in contact_to_campaigns_map:
                        
                        print(f"Contact {contact_id}: {contact_name} attended Campaigns: {contact_to_campaigns_map[contact_id]}\n")
                        
                        account_to_campaigns_map[account_id].update(contact_to_campaigns_map[contact_id])
                        
                
                if len(account_to_campaigns_map[account_id]) == 0:
                    
                    account_to_campaigns_map.pop(account_id)
                    
                else:
                    
                    # Opportunities
                    opps = account_result['Opportunities']['records']
                    account_to_opps_map[account_id] = []

                    for opp in opps:

                        opp_date = datetime.strptime(opp['CloseDate'], '%Y-%m-%d').date()
                        opp_amount = opp['Amount']

                        this_opp = Opportunity(date=opp_date, amount=opp_amount)

                        account_to_opps_map[account_id] += [ this_opp ]

        # go through both dictionaries
        # dataframe has: Account Name, Campaign Name, Campaign Start Date, Spend
        result_df = pd.DataFrame(columns=['Account Name', 'Campaign Name', 'Campaign Start Date', 'Spend Since Campaign'])

        for account_id, campaign_ids in account_to_campaigns_map.items():
            
            account_name = meta_account_map[account_id]
            
            # print(f"Processing Account {account_id}: {account_name}")
            
            opps = account_to_opps_map[account_id]
            
            for campaign_id in campaign_ids:
            
                spend_since_campaign = 0
                campaign = meta_campaign_map[campaign_id]
                
                # print(f"Processing Campaign {campaign_id}: {campaign.name}")
            
                for opp in opps:
                    if opp.date > campaign.date:
                        spend_since_campaign += opp.amount
                        
                result_df.loc[len(result_df.index)] = [account_name, campaign.name, campaign.date, spend_since_campaign]  

        return result_df