import asyncio
import aiohttp
import json
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ.get("DISCORD_TOKEN", "")
CHANNEL_IDS = [c.strip() for c in os.environ.get("CHANNEL_IDS", "").split(",") if c.strip()]
KEYWORDS = ["battle", "!battle", "rumble"]
NTFY_TOPIC = "metawin-battle-pangoliar"
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"

GATEWAY = "wss://gateway.discord.gg/?v=10&encoding=json"

async def send_ntfy(title, message):
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(
                NTFY_URL,
                data=message.encode("utf-8"),
                headers={
                    "Title": title,
                    "Priority": "urgent",
                    "Tags": "crossed_swords,rotating_light"
                }
            )
            print(f"[NTFY] Bildirim gonderildi: {message}")
    except Exception as e:
        print(f"[NTFY] Hata: {e}")

async def heartbeat(ws, interval, seq_holder):
    while True:
        await asyncio.sleep(interval / 1000)
        try:
            await ws.send_str(json.dumps({"op": 1, "d": seq_holder[0]}))
        except Exception:
            break

async def connect():
    reconnect_delay = 5
    while True:
        try:
            print("[BOT] Discord'a baglaniliyor...")
            connector = aiohttp.TCPConnector(ssl=True)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.ws_connect(
                    GATEWAY,
                    heartbeat=None,
                    compress=0
                ) as ws:
                    heartbeat_task = None
                    seq_holder = [None]

                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            op = data.get("op")
                            if data.get("s"):
                                seq_holder[0] = data["s"]

                            if op == 10:
                                interval = data["d"]["heartbeat_interval"]
                                if heartbeat_task:
                                    heartbeat_task.cancel()
                                heartbeat_task = asyncio.create_task(
                                    heartbeat(ws, interval, seq_holder)
                                )
                                await ws.send_str(json.dumps({
                                    "op": 2,
                                    "d": {
                                        "token": TOKEN,
                                        "properties": {
                                            "os": "windows",
                                            "browser": "chrome",
                                            "device": ""
                                        },
                                        "intents": (1 << 9) | (1 << 15)
                                    }
                                }))
                            elif op == 0:
                                if data["t"] == "READY":
                                    print("[BOT] Baglanti basarili! Kanallar dinleniyor...")
                                    print(f"[BOT] Dinlenen kanallar: {CHANNEL_IDS}")
                                    reconnect_delay = 5
                                elif data["t"] == "MESSAGE_CREATE":
                                    msg_data = data["d"]
                                    channel_id = msg_data.get("channel_id", "")
                                    if channel_id not in CHANNEL_IDS:
                                        continue
                                    content = msg_data.get("content", "").lower()
                                    author = msg_data.get("author", {}).get("username", "?")
                                    original = msg_data.get("content", "")
                                    for kw in KEYWORDS:
                                        if kw in content:
                                            print(f"[BATTLE] {author}: {original}")
                                            await send_ntfy(
                                                "BATTLE BASLADI!",
                                                f"{author}: {original}"
                                            )
                                            break
                            elif op == 9:
                                print("[BOT] Token gecersiz! Bot durduruluyor.")
                                return
                            elif op == 7:
                                print("[BOT] Yeniden baglanma istendi.")
                                break

                        elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            print(f"[BOT] Baglanti kesildi: {msg.type}")
                            break

        except Exception as e:
            print(f"[BOT] Hata: {e}")

        print(f"[BOT] {reconnect_delay} saniye sonra yeniden baglaniliyor...")
        await asyncio.sleep(reconnect_delay)
        reconnect_delay = min(reconnect_delay * 2, 60)

async def main():
    print("[BOT] Baslatiliyor...")
    print(f"[BOT] Kanallar: {CHANNEL_IDS}")
    print(f"[BOT] NTFY: {NTFY_URL}")
    if not TOKEN:
        print("[BOT] HATA: DISCORD_TOKEN ayarlanmamis!")
        return
    if not CHANNEL_IDS:
        print("[BOT] HATA: CHANNEL_IDS ayarlanmamis!")
        return
    await connect()

if __name__ == "__main__":
    asyncio.run(main())
