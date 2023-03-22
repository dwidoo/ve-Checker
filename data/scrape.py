# Import Packages
import os
import time
from datetime import datetime, date, timezone
from dateutil.relativedelta import relativedelta, TH
from pathlib import Path

import pandas as pd
import requests
import jmespath
import yaml
from web3 import Web3


from application_logging.logger import logger

params_path = "./params.yaml"

# THE Price
# params = {
#     "from": "0xF4C8E32EaDEC4BFe97E0F595AdD0f4450a863a11",
#     "to": "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56",
#     "amount": "1000000000000000000",
# }

# try:
#     response = requests.get("https://router.firebird.finance/bsc/route", params=params)
#     THE_price = response.json()["maxReturn"]["tokens"][
#         "0xf4c8e32eadec4bfe97e0f595add0f4450a863a11"
#     ]["price"]
# except Exception as e:
#     logger.error("Failed getting THE Price Error: %s" % e)

try:
    response = requests.get("https://api.thena.fi/api/v1/baseAssets")
    pricedict = response.json()
    THE_price = jmespath.search("data[?name=='THENA'].price", pricedict)[0]
except Exception as e:
    logger.error("Failed getting THE Price Error: %s" % e)


def read_params(config_path):
    with open(config_path) as yaml_file:
        config = yaml.safe_load(yaml_file)
    return config


config = read_params(params_path)

# Scrape Data and Save to CSV
try:
    logger.info("Scrape Started")

    # Params Data
    top_holders = pd.read_csv(config["data"]["top_holders_sheets_url"])

    provider_url = config["data"]["provider_url"]
    w3 = Web3(Web3.HTTPProvider(provider_url))

    abi1 = config["data"]["abi1"]
    contract_address1 = config["data"]["contract_address1"]
    contract_instance1 = w3.eth.contract(address=contract_address1, abi=abi1)

    abi2 = config["data"]["abi2"]
    contract_address2 = config["data"]["contract_address2"]
    contract_instance2 = w3.eth.contract(address=contract_address2, abi=abi2)

    # Epoch Check
    todayDate = datetime.utcnow()
    lastThursday = todayDate + relativedelta(weekday=TH(-1))
    my_time = datetime.min.time()
    my_datetime = datetime.combine(lastThursday, my_time)
    currentepoch = int(my_datetime.replace(tzinfo=timezone.utc).timestamp())

    tokendata = []
    for name, wallet_address in zip(top_holders["name"], top_holders["address"]):
        wallet_address = Web3.toChecksumAddress(wallet_address)

        # veTHE Owner
        tokenids = []
        for index in range(100):
            veTHE = contract_instance1.functions.tokenOfOwnerByIndex(wallet_address, index).call()
            if veTHE > 0:
                tokenids.append(veTHE)
            else:
                break

        # veTHE DF

        for tokenid in tokenids:
            # Balance veTHE
            bal = round(
                contract_instance1.functions.balanceOfNFT(tokenid).call() / 1000000000000000000,
                4,
            )

            # Locked veTHE
            locked = round(
                contract_instance1.functions.locked(tokenid).call()[0] / 1000000000000000000,
                4,
            )

            # Lock End Date
            lockend = time.strftime(
                "%Y-%m-%d",
                time.localtime(int(contract_instance1.functions.locked(tokenid).call()[1])),
            )

            # Voted Last Epoch
            voted = contract_instance1.functions.voted(tokenid).call()

            # Voted Current Epoch
            votedcurrentepoch = contract_instance2.functions.lastVoted(tokenid).call() > currentepoch

            # Total Supply
            totalSupply = contract_instance1.functions.totalSupply().call() / 1000000000000000000

            tokendata.append(
                {
                    "📛 name": name,
                    "🔢 Token ID": tokenid,
                    "🔒 Locked THE": locked,
                    "🧾 veTHE Balance": bal,
                    "🤑 Estimated BUSD Value": round(THE_price * locked, 4),
                    "⏲️ Lock End Date": lockend,
                    "🗳️ Vote Share %": round(bal / totalSupply * 100, 4),
                    "✔️ Vote Reset": ["No" if voted == True else "Yes"][0],
                    "⚡ Voted Current Epoch": ["No" if votedcurrentepoch == False else "Yes"][0],
                }
            )

    holder_vote_df = pd.DataFrame(tokendata)
    holder_vote_df.to_csv("data/top_holders/vote.csv", index=False)  # Save to CSV

    logger.info("Scrape Successful")
except Exception as e:
    logger.error("Error occurred while scraping Error: %s" % e)
