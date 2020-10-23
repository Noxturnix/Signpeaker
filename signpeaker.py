from urllib.parse import urlencode
import threading
import traceback
import responder
import requests
import livejson
import datetime
import base64
import pytz
import time

SETTINGS = livejson.File("settings.json")
if "host" not in SETTINGS:
	SETTINGS["host"] = "0.0.0.0"
if "port" not in SETTINGS:
	SETTINGS["port"] = 5768
if "ssl" not in SETTINGS:
	SETTINGS["ssl"] = False
if "ssl_cert" not in SETTINGS:
	SETTINGS["ssl_cert"] = None
if "ssl_key" not in SETTINGS:
	SETTINGS["ssl_key"] = None
if "client_id" not in SETTINGS:
	SETTINGS["client_id"] = None
if "client_secret" not in SETTINGS:
	SETTINGS["client_secret"] = None
if "redirect_uri" not in SETTINGS:
	SETTINGS["redirect_uri"] = None
if "discord_token" not in SETTINGS:
	SETTINGS["discord_token"] = None
if "status_message" not in SETTINGS:
	SETTINGS["status_message"] = "[ARTISTS] - [TRACK_TITLE]"
if "max_artists" not in SETTINGS:
	SETTINGS["max_artists"] = 0
if "emoji_id" not in SETTINGS:
	SETTINGS["emoji_id"] = None
if "emoji_name" not in SETTINGS:
	SETTINGS["emoji_name"] = "Spotify"
if "fetch_delay" not in SETTINGS:
	SETTINGS["fetch_delay"] = 5
if "clear_status_after" not in SETTINGS:
	SETTINGS["clear_status_after"] = 0
if "timezone" not in SETTINGS:
	SETTINGS["timezone"] = "UTC"
if "access_token" not in SETTINGS:
	SETTINGS["access_token"] = None
if "refresh_token" not in SETTINGS:
	SETTINGS["refresh_token"] = None

api = responder.API()
allow_spotify_login = False


def _log_message(message):
	print("[{0}]{1}".format(str(datetime.datetime.now(pytz.timezone(SETTINGS["timezone"]))).split(".", 1)[0], message))


def logInfo(message):
	_log_message("[INFO] " + message)


def logWarning(message):
	_log_message("[WARNING] " + message)


def logError(message):
	_log_message("[ERROR] " + message)


def requestLogin():
	logInfo("Please log in on https://accounts.spotify.com/authorize?" + urlencode({
		"response_type": "code",
		"client_id": SETTINGS["client_id"],
		"scope": "user-read-currently-playing",
		"redirect_uri": SETTINGS["redirect_uri"]
	}))


def onRateLimited():
	logWarning("Spotify API rate limited. You may need to increase fetch_delay")


def updateDiscordSettings(jsonData):
	return requests.patch("https://discord.com/api/v8/users/@me/settings", headers={
		"Authorization": SETTINGS["discord_token"]
	}, json=jsonData)


def getTokens(token, grant_type="authorization_code"):
	grant_type = grant_type.lower()
	assert grant_type.lower() in ["authorization_code", "refresh_token"], "Invalid grant_type"
	data = {
		"grant_type": grant_type
	}
	if grant_type == "authorization_code":
		data["code"] = token
		data["redirect_uri"] = SETTINGS["redirect_uri"]
	else:
		data["refresh_token"] = token
	return requests.post("https://accounts.spotify.com/api/token", headers={
		"Authorization": "Basic " + base64.b64encode("{0}:{1}".format(SETTINGS["client_id"], SETTINGS["client_secret"]).encode()).decode()
	}, data=data)


@api.route("/")
def spotifyUserLogin(req, rresp):
	global SETTINGS
	global allow_spotify_login
	rresp.status_code = 200
	rresp.text = ""
	if allow_spotify_login:
		if "code" in req.params:
			rresp.status_code = 500
			rresp.text = "Internal server error, check console log"
			if SETTINGS["client_id"]:
				if SETTINGS["client_secret"]:
					if SETTINGS["redirect_uri"]:
						try:
							jsonResp = getTokens(req.params["code"]).json()
							if "error" not in jsonResp:
								if "user-read-currently-playing" in jsonResp["scope"]:
									allow_spotify_login = False

									SETTINGS["access_token"] = jsonResp["access_token"]
									SETTINGS["refresh_token"] = jsonResp["refresh_token"]

									jsonResp = requests.get("https://api.spotify.com/v1/me", headers={
										"Authorization": "Bearer " + SETTINGS["access_token"]
									}).json()

									if "error" not in jsonResp:
										logInfo("Spotify logged in as " + jsonResp["display_name"])
										rresp.status_code = 200
										rresp.text = "Log in success!"
									else:
										logError(jsonResp["error"]["message"])
								else:
									rresp.text = "Permission error, user-read-currently-playing is not in scope"
							else:
								logError(jsonResp["error_description"])
						except Exception as e:
							logError(str(e))
					else:
						logError("redirect_uri is not set")
				else:
					logError("client_secret is not set")
			else:
				logError("client_id is not set")
		elif "error" in req.params:
			rresp.status_code = 401
			rresp.text = "Failed to authenticate"
		else:
			rresp.status_code = 400
			rresp.text = "Invalid request"
	else:
		rresp.status_code = 403
		rresp.text = "Spotify login is currently disabled"


def statusUpdater():
	retry_delay = 10
	crash_retry_delay = 3
	while True:
		try:
			if SETTINGS["discord_token"]:
				resp = requests.get("https://discord.com/api/v8/users/@me", headers={
					"Authorization": SETTINGS["discord_token"]
				})
				if resp.status_code == 200:
					discordUsername = resp.json()["username"]
					logInfo("Discord logged in as " + discordUsername)

					last_status_message = ""
					while True:
						try:
							if SETTINGS["access_token"]:
								spotifyResp = requests.get("https://api.spotify.com/v1/me/player/currently-playing", headers={
									"Authorization": "Bearer " + SETTINGS["access_token"]
								})
								if spotifyResp.status_code in [200, 204]:
									if spotifyResp.status_code == 200:
										spotifyJsonResp = spotifyResp.json()
										if spotifyJsonResp["is_playing"]:

											artist_list = [artist["name"] for artist in spotifyJsonResp["item"]["artists"]]

											track_title = spotifyJsonResp["item"]["name"]
											main_artist = artist_list[0]
											artists = ", ".join(artist_list[:SETTINGS["max_artists"] if SETTINGS["max_artists"] > 0 else None])

											status_message = SETTINGS["status_message"].replace("[MAIN_ARTIST]", main_artist).replace("[ARTISTS]", artists).replace("[TRACK_TITLE]", track_title)

											if status_message != last_status_message:
												jsonData = {
													"custom_status": {
														"text": status_message
													}
												}
												if SETTINGS["clear_status_after"] > 0:
													jsonData["custom_status"]["expires_at"] = (datetime.datetime.utcnow() + datetime.timedelta(seconds=SETTINGS["clear_status_after"])).isoformat()[:-3] + "Z"
												if SETTINGS["emoji_id"]:
													jsonData["custom_status"]["emoji_id"] = SETTINGS["emoji_id"]
													jsonData["custom_status"]["emoji_name"] = SETTINGS["emoji_name"]

												logInfo("Updating Discord status to: " + status_message)
												discordResp = updateDiscordSettings(jsonData)
												if discordResp.status_code == 200:
													last_status_message = status_message
												else:
													break

											time.sleep(SETTINGS["fetch_delay"])
											continue
										else:
											if "" != last_status_message:
												logInfo("Removing Discord status...")
												discordResp = updateDiscordSettings({"custom_status": None})
												if discordResp.status_code == 200:
													last_status_message = ""
												else:
													break
											time.sleep(SETTINGS["fetch_delay"])
											continue
									else:
										if "" != last_status_message:
											logInfo("Removing Discord status...")
											discordResp = updateDiscordSettings({"custom_status": None})
											if discordResp.status_code == 200:
												last_status_message = ""
											else:
												break
										time.sleep(retry_delay)
										continue
								elif resp.status_code == 429:
									onRateLimited()
									time.sleep(int(resp.headers["Retry-After"]))
									continue
								else:
									try:
										logError(spotifyResp.join()["error"]["message"])
									except:
										pass
									time.sleep(retry_delay)
									continue
							else:
								time.sleep(retry_delay)
								continue
						except Exception as e:
							logError(str(e))
						time.sleep(crash_retry_delay)

					continue

				else:
					logError("Discord token is invalid")
					time.sleep(retry_delay)
					continue
			else:
				logError("discord_token is not set")
				time.sleep(retry_delay)
				continue
		except Exception as e:
			logError(str(e))
		time.sleep(crash_retry_delay)


def statusUpdaterDaemon():
	global SETTINGS
	global allow_spotify_login
	statusUpdaterStarted = False
	retry_delay = 10
	crash_retry_delay = 3
	while True:
		try:
			if SETTINGS["client_id"]:
				if SETTINGS["client_secret"]:
					if SETTINGS["redirect_uri"]:
						if SETTINGS["refresh_token"]:
							logInfo("Refreshing Spotify token...")
							resp = getTokens(SETTINGS["refresh_token"], grant_type="refresh_token")
							if resp.status_code == 200:
								jsonResp = resp.json()
								SETTINGS["access_token"] = jsonResp["access_token"]
								expires_in = jsonResp["expires_in"]
								if not statusUpdaterStarted:
									logInfo("Starting status updater...")
									statusUpdaterThread = threading.Thread(target=statusUpdater)
									statusUpdaterThread.daemon = True
									statusUpdaterThread.start()
									statusUpdaterStarted = True
								time.sleep(expires_in - 60)
								continue
							elif resp.status_code == 429:
								onRateLimited()
								time.sleep(int(resp.headers["Retry-After"]))
								continue
							else:
								SETTINGS["refresh_token"] = None
								SETTINGS["access_token"] = None
								allow_spotify_login = True
						else:
							allow_spotify_login = True
						if allow_spotify_login:
							requestLogin()
							time.sleep(retry_delay)
							continue
					else:
						logError("redirect_uri is not set")
						time.sleep(retry_delay)
						continue
				else:
					logError("client_secret is not set")
					time.sleep(retry_delay)
					continue
			else:
				logError("client_id is not set")
				time.sleep(retry_delay)
				continue
		except Exception as e:
			logError(str(e))
		time.sleep(crash_retry_delay)


statusUpdaterDaemonThread = threading.Thread(target=statusUpdaterDaemon)
statusUpdaterDaemonThread.daemon = True
statusUpdaterDaemonThread.start()

ssl_certfile = None
ssl_keyfile = None
if SETTINGS["ssl"]:
	ssl_certfile = SETTINGS["ssl_cert"]
	ssl_keyfile = SETTINGS["ssl_key"]

api.run(address=SETTINGS["host"], port=SETTINGS["port"], ssl_certfile=ssl_certfile, ssl_keyfile=ssl_keyfile)
