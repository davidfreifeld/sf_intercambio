import streamlit as st
from datetime import datetime
from sf_intercambio import Query

def on_run_query_click():
    query = Query(username, password, start_date_str)
    result_df = query.run()
    
    st.session_state.result_csv_string = result_df.to_csv(index=False).encode("utf-8")
    st.session_state.run_query_clicked = True

if 'run_query_clicked' not in st.session_state:
    st.session_state.run_query_clicked = False 
if 'result_csv_string' not in st.session_state:
    st.session_state.result_csv_string = ''

title = 'Intercambio Salesforce Query Engine'
st.set_page_config(page_title=title) # , layout='wide')
st.title(title)

left_col, right_col = st.columns(2)

with left_col:

    username = st.text_input("Username", value='rachel@intercambio.org')
    password = st.text_input("Password", type="password")

with right_col:

    start_date_str = st.text_input("Start Date (e.g. THIS_FISCAL_YEAR or 2024-01-26)", value='THIS_FISCAL_YEAR')
    st.markdown('See [here](%s) for more details about date inputs.' % 'https://developer.salesforce.com/docs/atlas.en-us.soql_sosl.meta/soql_sosl/sforce_api_calls_soql_select_dateformats.htm')

st.button('Run Query', on_click=on_run_query_click, type="primary")

if st.session_state.run_query_clicked:
    st.download_button(
        label="Download Results",
        data=st.session_state.result_csv_string,
        file_name="spend_since_campaign_" + datetime.strftime(datetime.now(), '%Y-%m-%d-%H-%M') + ".csv",
        mime='text/csv'
    )