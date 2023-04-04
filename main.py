import time
import os
import logging
import requests

from ipaddress import IPv4Network, AddressValueError
from requests.auth import HTTPBasicAuth


ROS_REST_URL = os.getenv("ROS_REST_URL", default="https://127.0.0.1")
ROS_USERNAME = os.getenv("ROS_USERNAME", default="admin")
ROS_PASSWORD = os.getenv("ROS_PASSWORD", default="")
PPPOE_INTERFACE = os.getenv("PPPOE_INTERFACE", default="pppoe-out1")
TARGET_NETWORK = IPv4Network(os.getenv("TARGET_NETWORK", default="58.32.0.0/16"))
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", default=5))
MAX_RETRY = int(os.getenv("MAX_RETRY", 20))
LOG_LEVEL = os.getenv("LOG_LEVEL", default="INFO")

logging.basicConfig(level=LOG_LEVEL)

requests.packages.urllib3.disable_warnings()


class RouterOSHelper:
    def __init__(self, base_url: str, username: str = "root", password: str = ""):
        self._base_url = base_url
        self._auth = HTTPBasicAuth(username, password)

    def get_address(self, interface: str) -> IPv4Network | None:
        resp = requests.get(
            f"{self._base_url}/rest/ip/address?actual-interface={interface}&.proplist=address",
            auth=self._auth,
            verify=False,
        )
        if resp.status_code != 200:
            raise Exception(resp.status_code, resp.text)
        records = resp.json()
        if len(records) == 0:
            return None
        try:
            addr = IPv4Network(records[0]["address"])
        except AddressValueError:
            addr = None
        return addr

    def get_pppoe_id(self, interface: str) -> str | None:
        resp = requests.get(
            f"{self._base_url}/rest/interface/pppoe-client?name={interface}&.proplist=.id",
            auth=self._auth,
            verify=False,
        )
        if resp.status_code != 200:
            raise Exception(resp.status_code, resp.text)
        records = resp.json()
        if len(records) == 0:
            return None
        return records[0][".id"]

    def reconnect_pppoe(self, pppoe_id: str) -> None:
        resp = requests.patch(
            f"{self._base_url}/rest/interface/pppoe-client/{pppoe_id}",
            json={},
            auth=self._auth,
            verify=False,
        )
        if resp.status_code != 200:
            raise Exception(resp.status_code, resp.text)


h = RouterOSHelper(ROS_REST_URL, username=ROS_USERNAME, password=ROS_PASSWORD)
current_address = h.get_address(PPPOE_INTERFACE)
if current_address is None:
    raise Exception(f"empty address on interface {PPPOE_INTERFACE}")
logging.info(f"Get address {current_address} on interface {PPPOE_INTERFACE}.")

pppoe_id = h.get_pppoe_id(PPPOE_INTERFACE)
if pppoe_id is None:
    raise Exception(f"interface {PPPOE_INTERFACE} not found")
logging.info(f"Get pppoe client {pppoe_id} on interface {PPPOE_INTERFACE}.")

retry = 0
while True:
    if retry >= MAX_RETRY:
        logging.error(f"Max retry exceed. Reboot or remove this program.")
        time.sleep(CHECK_INTERVAL)
        continue
    address = h.get_address(PPPOE_INTERFACE)
    if address is None:
        logging.error(f"Cannot get address. Retry after {CHECK_INTERVAL} seconds.")
        time.sleep(CHECK_INTERVAL)
        continue
    if address != current_address:
        current_address = address
        logging.warning(f"Get new address {address}.")
    if address.subnet_of(TARGET_NETWORK):
        retry = 0
        logging.debug(f"Current address {address} already in target network {TARGET_NETWORK}.")
        continue
    logging.warning(f"Reconnect and check again after {CHECK_INTERVAL} seconds.")
    h.reconnect_pppoe(pppoe_id)
    retry += 1
    time.sleep(CHECK_INTERVAL)
