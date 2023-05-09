import time
import streamlit as st
import yaml
import requests
import pandas as pd
from web3 import Web3
from web3.middleware import validation
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
    validation.METHODS_TO_VALIDATE = []
    w3 = Web3(Web3.HTTPProvider(provider_url, request_kwargs={"timeout": 60}))
    abi1 = config["data"]["abi1"]
    contract_address1 = config["data"]["contract_address1"]
    contract_instance1 = w3.eth.contract(address=contract_address1, abi=abi1)
except Exception as e:
    print(e)

try:
    # Get CHR & ETH Price
    response = requests.get(
        "https://coins.llama.fi/prices/current/arbitrum:0x15b2fb8f08E4Ac1Ce019EADAe02eE92AeDF06851?searchWidth=1h")
    pricedict = response.json()
    #CHR_price = jmespath.search("data[?symbol=='CHR'].price", pricedict)[0]
    CHR_price = pricedict["coins"]["arbitrum:0x15b2fb8f08E4Ac1Ce019EADAe02eE92AeDF06851"]["price"]
    response2 = requests.get(
        "https://coins.llama.fi/prices/current/ethereum:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2?searchWidth=1h")
    pricedict2 = response.json()
    ETH_price = pricedict2["coins"]["ethereum:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"]["price"]
except Exception as e:
    print(e)


# Listings Data
try:
    # Requests
    headers = {"accept": "application/json", "X-API-KEY": st.secrets['OKEY']}
    response = requests.get(listings_api, headers=headers)

    # Pandas Manipulation
    df = pd.json_normalize(response.json())
    df = df[['Orders Price Amount Native', 'Orders Criteria Data Token Tokenid']]
    df.rename(columns={'Orders Price Amount Native': 'price.current.value',
              'Orders Criteria Data Token Tokenid': 'id'}, inplace=True)
    df['price.current.value'] = df['price.current.value'].astype(float)
    df['id'] = df['id'].astype(int)
    df.drop_duplicates(subset=["id"], keep='last', inplace=True)
except Exception as e:
    print(e)

# Web3
try:
    tokenids = df['id']
    tokendata = []

    def get_veCHR_data(tokenid):
        try:
            # Locked veCHR
            locked = round(
                contract_instance1.functions.locked(
                    tokenid).call()[0] / 1000000000000000000,
                4,
            )

            if locked <= 1:
                return

            # Voted Last Epoch
            voted = contract_instance1.functions.voted(tokenid).call()

            if voted == True:
                return

            # Balance veCHR
            bal = round(
                contract_instance1.functions.balanceOfNFT(
                    tokenid).call() / 1000000000000000000,
                4,
            )

            # Lock End Date
            lockend = time.strftime(
                "%Y-%m-%d",
                time.gmtime(
                    int(contract_instance1.functions.locked(tokenid).call()[1])),
            )

            tokendata.append({"🔢 Token ID": tokenid, "🔒 Locked CHR": locked, "🧾 veCHR Balance": bal, "🤑 veCHR Value in USD": round(
                CHR_price * locked, 4), "⏲️ Lock End Date": lockend, "✔️ Vote Reset": ["No" if voted == True else "Yes"][0]})
        except Exception as e:
            print(e)

    with concurrent.futures.ThreadPoolExecutor() as ex:
        ex.map(get_veCHR_data, tokenids)
except Exception as e:
    print(e)


# Pandas Manipulation
try:
    listings_df = pd.DataFrame(tokendata)
#     listings_df = listings_df[listings_df["🔒 Locked CHR"] >= 1]
#     listings_df = listings_df[listings_df["✔️ Vote Reset"] == "Yes"]
    listings_df = listings_df.merge(
        df, how="left", left_on="🔢 Token ID", right_on="id").drop(columns="id")
    listings_df.rename(
        columns={"price.current.value": "🟨 Sale Price in ETH"}, inplace=True)
    listings_df["💰 Sale Price in USD"] = listings_df["🟨 Sale Price in ETH"] * ETH_price
    listings_df["💸 Potential Profit in USD"] = listings_df["🤑 veCHR Value in USD"] - \
        listings_df["💰 Sale Price in USD"]
    listings_df["🛒 Discount %"] = (listings_df["🤑 veCHR Value in USD"] -
                                   listings_df["💰 Sale Price in USD"]) / listings_df["🤑 veCHR Value in USD"] * 100
    listings_df["🔗 OS Link"] = listings_df["🔢 Token ID"].apply(
        lambda x: '<a href="https://opensea.io/assets/bsc/0x9A01857f33aa382b1d5bb96C3180347862432B0d/' + str(x) + '">OS Link</a>')
    listings_df.drop(columns=["✔️ Vote Reset"], inplace=True)
    listings_df.sort_values(by="🛒 Discount %", ascending=False, inplace=True)


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

:red[The above list excludes veCHR which has not been vote reset or the locked value is very little or dust.]

:red[Negative Discount/Profit = Bad Deal = ngmi]
    
:violet[If you found this useful you can buy me aka ALMIGHTY ABE a :coffee: at 0x5783Fb2f3d93364041d49097b66086703527AeaC]
            """
)

except Exception as e:
    print(e)

