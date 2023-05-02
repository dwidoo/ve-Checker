import time
import streamlit as st
import yaml
import requests
import pandas as pd
import os
from web3 import Web3
import jmespath
import concurrent.futures
import time

# App
st.set_page_config(
    page_title="🌊 OpenSea Listings",
    page_icon="icons/thena.png",
    layout="wide",
)

# Params
params_path = "params.yaml"


def read_params(config_path):
    with open(config_path) as yaml_file:
        config = yaml.safe_load(yaml_file)
    return config


config = read_params(params_path)

# Title
st.title("🌊 OpenSea Listings")

try:
    listings_api = config["data"]["listings_api"]
    provider_url = config["data"]["provider_url"]
    w3 = Web3(Web3.HTTPProvider(provider_url))
    abi1 = config["data"]["abi1"]
    contract_address1 = config["data"]["contract_address1"]
    contract_instance1 = w3.eth.contract(address=contract_address1, abi=abi1)
except Exception as e:
    print(e)

try:
    # Get BNB Price
    response = requests.get("https://api.thena.fi/api/v1/assets")
    pricedict = response.json()
    THE_price = jmespath.search("data[?name=='THENA'].price", pricedict)[0]
    BNB_price = jmespath.search("data[?name=='Wrapped BNB'].price", pricedict)[0]
except Exception as e:
    print(e)


# Listings Data
try:
    ## Requests
    credentials = os.environ["OKEY"]
    credentials = json.loads(credentials)
    headers = {"accept": "application/json", "X-API-KEY": credentials}
    response = requests.get(listings_api, headers=headers)
  
    ## Pandas Manipulation
    df = pd.json_normalize(response.json()['listings'])
    df.drop(['order_hash', 'chain', 'type', 'protocol_address', 'price.current.currency', 'price.current.decimals', 'protocol_data.parameters.offerer', 'protocol_data.parameters.consideration', 'protocol_data.parameters.startTime', 'protocol_data.parameters.endTime', 'protocol_data.parameters.orderType', 'protocol_data.parameters.zone', 'protocol_data.parameters.zoneHash', 'protocol_data.parameters.salt', 'protocol_data.parameters.conduitKey', 'protocol_data.parameters.totalOriginalConsiderationItems', 'protocol_data.parameters.counter', 'protocol_data.signature'], axis=1, inplace=True)
    df['protocol_data.parameters.offer'] = df['protocol_data.parameters.offer'].str[0]
    df['id'] = pd.json_normalize(df['protocol_data.parameters.offer'])['identifierOrCriteria']
    df.drop(['protocol_data.parameters.offer'], axis=1, inplace=True)
    df['price.current.value'] = df['price.current.value'].astype(float)/1000000000000000000
    df['id'] = df['id'].astype(int)
except Exception as e:
    print(e)

## Web3
try:
    tokenids = df['id']
    tokendata = []
    def get_veTHE_data(tokenid):
        try:
            # Locked veTHE
            locked = round(
                contract_instance1.functions.locked(tokenid).call()[0] / 1000000000000000000,
                4,
            )

            # Balance veTHE
            bal = round(
                contract_instance1.functions.balanceOfNFT(tokenid).call() / 1000000000000000000,
                4,
            )

            # Lock End Date
            lockend = time.strftime(
                "%Y-%m-%d",
                time.gmtime(int(contract_instance1.functions.locked(tokenid).call()[1])),
            )

            # Voted Last Epoch
            voted = contract_instance1.functions.voted(tokenid).call()

            tokendata.append({"🔢 Token ID": tokenid, "🔒 Locked THE": locked, "🧾 veTHE Balance": bal, "🤑 veTHE Value in USD": round(THE_price * locked, 4), "⏲️ Lock End Date": lockend, "✔️ Vote Reset": ["No" if voted == True else "Yes"][0]})
        except Exception as e:
            print(e)

    with concurrent.futures.ThreadPoolExecutor() as ex:
        ex.map(get_veTHE_data, tokenids)
except Exception as e:
    print(e)
    
## Pandas Manipulation
try:
    listings_df = pd.DataFrame(tokendata)
    listings_df = listings_df[listings_df["🔒 Locked THE"] >= 1]
    listings_df = listings_df[listings_df["✔️ Vote Reset"] == "Yes"]
    listings_df = listings_df.merge(df, how="left", left_on="🔢 Token ID", right_on="id").drop(columns="id")
    listings_df.rename(columns = {"price.current.value":"🟨 Sale Price in BNB"}, inplace = True)
    listings_df["💰 Sale Price in USD"] = listings_df["🟨 Sale Price in BNB"] * BNB_price
    listings_df["💸 Potential Profit in USD"] = listings_df["🤑 veTHE Value in USD"] - listings_df["💰 Sale Price in USD"]
    listings_df["🛒 Discount %"] = (listings_df["🤑 veTHE Value in USD"] - listings_df["💰 Sale Price in USD"]) / listings_df["🤑 veTHE Value in USD"] * 100
    listings_df["🔗 OS Link"] = listings_df["🔢 Token ID"].apply(lambda x: '<a href="https://opensea.io/assets/bsc/0xfbbf371c9b0b994eebfcc977cef603f7f31c070d/' + str(x) + '">OS Link</a>')
    listings_df.drop(columns=["✔️ Vote Reset"], inplace=True)
    listings_df.sort_values(by="🛒 Discount %", ascending=False, inplace=True)
except Exception as e:
    print(e)

# creating a single-element container
placeholder = st.empty()

# Empty Placeholder Filled
with placeholder.container():
    st.write(listings_df.to_html(escape=False, index=False, float_format="{:10.2f}".format), unsafe_allow_html=True)


# Note
st.markdown("#")
st.markdown("#")
st.caption(
    """
NFA, DYOR -- This web app is in beta, I am not responsible for any information on this page.

:red[The above list excludes veTHE which has not been vote reset or the locked value is very little or dust.]

:red[Negative Discount/Profit = Bad Deal = ngmi]
    
:violet[If you found this useful you can buy me aka ALMIGHTY ABE a :coffee: at 0x5783Fb2f3d93364041d49097b66086703527AeaC]
            """
)
