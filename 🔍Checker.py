from web3 import Web3
from datetime import datetime, date, timezone
from dateutil.relativedelta import relativedelta, TH
import time
import streamlit as st
from st_btn_select import st_btn_select
import yaml
import requests
import jmespath
import pandas as pd

# App
st.set_page_config(
    page_title="🔍 veCHR Checker",
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
st.title("🔍 veCHR Checker")

# Select Button
selection = st_btn_select(("Token ID", "Address"))

# THE Price
# params = {
#     "from": "0xF4C8E32EaDEC4BFe97E0F595AdD0f4450a863a11",
#     "to": "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56",
#     "amount": "1000000000000000000",
# }

# try:
#     response = requests.get("https://router.firebird.finance/bsc/route", params=params)
#     THE_price = response.json()["maxReturn"]["tokens"]["0xf4c8e32eadec4bfe97e0f595add0f4450a863a11"]["price"]
# except Exception as e:
#     print(e)


try:
    response = requests.get("https://coins.llama.fi/prices/current/arbitrum:0x15b2fb8f08E4Ac1Ce019EADAe02eE92AeDF06851?searchWidth=1h")
    pricedict = response.json()
    CHR_price = jmespath.search("data[?Symbol=='CHR'].Price", pricedict)[0]
except Exception as e:
    print(e)

try:
    provider_url = config["data"]["provider_url"]
    w3 = Web3(Web3.HTTPProvider(provider_url))

    abi1 = config["data"]["abi1"]
    contract_address1 = config["data"]["contract_address1"]
    contract_instance1 = w3.eth.contract(address=contract_address1, abi=abi1)

    abi2 = config["data"]["abi2"]
    contract_address2 = config["data"]["contract_address2"]
    contract_instance2 = w3.eth.contract(address=contract_address2, abi=abi2)

    abi3 = config["data"]["abi3"]
    contract_address3 = config["data"]["contract_address3"]
    contract_instance3 = w3.eth.contract(address=contract_address3, abi=abi3)

    # Total Supply
    totalSupply = contract_instance3.functions.balanceOf("0x9A01857f33aa382b1d5bb96C3180347862432B0d").call() / 1000000000000000000

    todayDate = datetime.utcnow()
    lastThursday = todayDate + relativedelta(weekday=TH(-1))
    my_time = datetime.min.time()
    my_datetime = datetime.combine(lastThursday, my_time)
    currentepoch = int(my_datetime.replace(tzinfo=timezone.utc).timestamp())

except Exception as e:
    print(e)

# Token ID Search
if selection == "Token ID":
    tokenid = st.number_input("Your veCHR Token ID", min_value=1, format="%d")

    # Read Data
    try:
        # Balance veCHR
        bal = round(
            contract_instance1.functions.balanceOfNFT(tokenid).call() / 1000000000000000000,
            4,
        )

        # Locked veCHR
        locked = round(
            contract_instance1.functions.locked(tokenid).call()[0] / 1000000000000000000,
            4,
        )

        # Lock End Date
        lockend = time.strftime(
            "%Y-%m-%d",
            time.gmtime(int(contract_instance1.functions.locked(tokenid).call()[1])),
        )

        # Voted Last Epoch
        voted = contract_instance1.functions.voted(tokenid).call()

        # Voted Current Epoch
        votedcurrentepoch = contract_instance2.functions.lastVoted(tokenid).call() > currentepoch

        # creating a single-element container
        placeholder = st.empty()

        # Empty Placeholder Filled
        with placeholder.container():
            if tokenid:
                st.markdown("🔒 Locked CHR: " + str(locked))
                st.markdown("🧾 veCHR Balance: " + str(bal))
                st.markdown("🤑 Estimated BUSD Value: $" + str(round(CHR_price * locked, 4)))
                st.markdown("⏲️ Lock End Date: " + str(lockend))
                st.markdown("🗳️ Vote Share: " + str(round(bal / totalSupply * 100, 4)) + "%")
                st.markdown("✔️ Vote Reset: " + ["No" if voted == True else "Yes"][0])
                st.markdown("⚡ Voted Current Epoch: " + ["No" if votedcurrentepoch == False else "Yes"][0])

        # Note
        st.markdown("#")
        st.markdown("#")
        st.caption(
            """
    NFA, DYOR -- This web app is in beta, I am not responsible for any information on this page.
            
    BUSD Value is just an estimate of CHR Price pulled from Firebird API.
            
    :red[If "Vote Reset" is No you cannot sell your veCHR unless you reset your vote.]
    
    :violet[If you found this useful you can buy me aka ALMIGHTY ABE a :coffee: at 0x5783Fb2f3d93364041d49097b66086703527AeaC]
            """
        )

    except Exception as e:
        print(e)
        st.markdown("Error Please Try Again")

# Address Search
if selection == "Address":
    wallet_address = st.text_input(
        label="Your wallet address",
        placeholder="Enter your wallet address",
        max_chars=42,
    )

    if wallet_address:
        # Read Data
        try:
            # Checksum Address
            wallet_address = Web3.toChecksumAddress(wallet_address)

            # veCHR Owner
            tokenids = []
            for index in range(100):
                veCHR = contract_instance1.functions.tokenOfOwnerByIndex(wallet_address, index).call()
                if veCHR > 0:
                    tokenids.append(veCHR)
                else:
                    break

            # veCHR DF
            tokendata = []
            for tokenid in tokenids:
                # Balance veCHR
                bal = round(
                    contract_instance1.functions.balanceOfNFT(tokenid).call() / 1000000000000000000,
                    4,
                )

                # Locked veCHR
                locked = round(
                    contract_instance1.functions.locked(tokenid).call()[0] / 1000000000000000000,
                    4,
                )

                # Lock End Date
                lockend = time.strftime(
                    "%Y-%m-%d",
                    time.gmtime(int(contract_instance1.functions.locked(tokenid).call()[1])),
                )

                # Voted Last Epoch
                voted = contract_instance1.functions.voted(tokenid).call()

                # Voted Current Epoch
                votedcurrentepoch = contract_instance2.functions.lastVoted(tokenid).call() > currentepoch

                tokendata.append(
                    {
                        "🔢 Token ID": tokenid,
                        "🔒 Locked CHR": locked,
                        "🧾 veCHR Balance": bal,
                        "🤑 Estimated BUSD Value": round(CHR_price * locked, 4),
                        "⏲️ Lock End Date": lockend,
                        "🗳️ Vote Share %": round(bal / totalSupply * 100, 4),
                        "✔️ Vote Reset": ["No" if voted == True else "Yes"][0],
                        "⚡ Voted Current Epoch": ["No" if votedcurrentepoch == False else "Yes"][0],
                    }
                )

            veCHR_df = pd.DataFrame(tokendata)
            veCHR_df.sort_values(by="🔢 Token ID", axis=0, inplace=True)

            # creating a single-element container
            placeholder = st.empty()

            # Empty Placeholder Filled
            with placeholder.container():
                if wallet_address:
                    st.dataframe(veCHR_df)

            # Note
            st.markdown("#")
            st.markdown("#")
            st.caption(
                """
        NFA, DYOR -- This web app is in beta, I am not responsible for any information on this page.
                
        BUSD Value is just an estimate of CHR Price pulled from Firebird API.
                
        :red[If "Vote Reset" is No you cannot sell your veCHR unless you reset your vote.]
        
        :violet[If you found this useful you can buy me aka ALMIGHTY ABE a :coffee: at 0x5783Fb2f3d93364041d49097b66086703527AeaC]
                """
            )

        except Exception as e:
            print(e)
            st.markdown("Error Please Try Again")
