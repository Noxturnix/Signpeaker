# Signpeaker
Set your Discord status as your currently playing Spotify song

# Before You Begin
You might want to consider running this script on your (private) server in a `tmux` session; not your local PC, since it needs to listen for HTTP(S) requests and we also want it to run 24/7.

If you found that this manual is confusing, I'm so sorry for my bad English :p I would really appreciate your contribution for this project, especially this README.md

Also, this script was recreated from my orignal script for personal use. I'm not responsible for anything that happens to your account.

# Getting Started
You need `git`, `python3` and `pip3` installed on your machine. The installation process may differ on different OSes. This usually works on Debian/Ubuntu
```
sudo apt update
sudo apt install git python3 python3-pip -y
```
Clone this repository and install requirements
```
git clone https://github.com/Noxturnix/Signpeaker.git
cd Signpeaker/
pip3 install -r requirements.txt
```

# Configure and Run
Copy `settings.example.json` to `settings.json`
```
cp settings.example.json settings.json
```
Open `settings.json` with your preferred editor. In this manual, we use `nano`
```
nano settings.json
```
See [Settings](#settings) for a guildline. After you've done that, press `Ctrl + X`, press `Y` and press `Enter` to save and quit.
Now, it's time to run the script! you can do this in a `tmux` session if you want
```
python3 signpeaker.py
```
If nothing is wrong, the script should give you a Spotify login URL. Open the link and login, and you're done!

Also note that if you save `settings.json` settings later, you don't have to restart the script. We use `livejson` for a reason ;)

# Settings
These settings are required to be set to a valid value
- `discord_token` (str) Your Discord token
- `client_id` (str) Your Spotify app ID. You can create an app on [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/)
- `client_secret` (str) Same as above but this is the client secret for the app
- `redirect_uri` (str) Same exact Redirect URI from your Spotify app settings. If you haven't added it to your app yet, it's your IP/Domain and port to your machine. For instance, "https://example.com:5768/"

You may want to change these settings as your preferred value
- `host` (str) Bind IP address
- `port` (int) Listen on a specific port
- `ssl` (bool) Use SSL or not
- `ssl_cert` (str) Path to a SSL certificate
- `ssl_key` (str) Path to the SSL key for `ssl_cert`
- `status_message` (str) Your Discord status message. It can also be formatted. See [Status Message Format](#status-message-format)
- `clear_status_after` (int) Discord should automatically clear your status after n second(s); `1800` for 30 minutes, `3600` for 1 hour etc.
- `max_artists` (int) Max amount of artist names that should be replaced to `[ARTISTS]`
- `emoji_id` (str) Emoji ID you want to use in your Discord status
- `emoji_name` (str) Emoji name. Discord appears to accept all names but you may want to set this to the name of `emoji_id` just in case
- `timezone` (str) Timezone string for log messages; `Asia/Bangkok`, `America/Los_Angeles`, `UTC` etc.
- `fetch_delay` (int) Delay in second for each Spotify API requests

These settings should never be touch. They're controlled by the script. Only edit if you know what are you doing
- `access_token` Spotify access token; used to get currently playing track
- `refresh_token` Spotify refresh token; used to re-issue `access_token`

# Status Message Format
- `[ARTISTS]` All artists that contribute the track; including feat./remix artists. It can be capped with the `max_artists` setting
- `[MAIN_ARTIST]` Same as `[ARTISTS]` with `max_artists` set to 1
- `[TRACK_TITLE]` Track/Song name

# License
[MIT License](LICENSE)
