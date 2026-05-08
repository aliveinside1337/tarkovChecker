import os
import subprocess
import time

PROXIFIER_EXE = r"C:\Users\USER\Desktop\Proxifier PE\Proxifier.exe"
PROFILE_PATH = r"C:\Users\USER\Desktop\Proxifier PE\Profiles\Default.ppx"

#Код не актуален, когда его писал думал что будет смысл, но позже увидел что можно просто запустить проксифиллер сразу и оставить его

def generate_profile(ip: str, port: str, login: str, password: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<ProxifierProfile version="1.0" platform="Windows" product_id="0" product_version="3">
  <Options>
    <Resolve><ViaProxy>true</ViaProxy></Resolve>
  </Options>
  <ProxyList>
    <Proxy id="1" type="HTTPS">
      <Address>{ip}</Address>
      <Port>{port}</Port>
      <Authentication>
        <Username>{login}</Username>
        <Password>{password}</Password>
      </Authentication>
    </Proxy>
  </ProxyList>
  <RuleList>
    <Rule enabled="true">
      <Name>BsgLauncher</Name>
      <Applications>BsgLauncher.exe</Applications>
      <Action type="Proxy">1</Action>
    </Rule>
    <Rule enabled="true">
      <Name>Default</Name>
      <Action type="Direct"/>
    </Rule>
  </RuleList>
</ProxifierProfile>"""


def apply_proxy(proxy: dict):
    # ip = proxy["ip"]
    # port = proxy["port"]
    # login = proxy.get("login", "")
    # password = proxy.get("password", "")
    #
    # profile_xml = generate_profile(ip, port, login, password)
    #
    # os.system("taskkill /f /im Proxifier.exe >nul 2>&1")
    # time.sleep(1)
    #
    # os.makedirs(os.path.dirname(PROFILE_PATH), exist_ok=True)
    # with open(PROFILE_PATH, "w", encoding="utf-8") as f:
    #     f.write(profile_xml)
    # print(f"[PROXIFIER] Профиль записан: {ip}:{port} | {login}")
    #
    # subprocess.Popen([PROXIFIER_EXE, PROFILE_PATH])
    # time.sleep(3)
    print("[PROXIFIER] Запущен")




def stop():
    os.system("taskkill /f /im Proxifier.exe >nul 2>&1")
    print("[PROXIFIER] Остановлен")